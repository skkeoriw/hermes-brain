#!/usr/bin/env python3
"""
NotebookLM Processor for Hermes Webhooks
优化点：
1) 所有 YouTube 链接写入同一个共享笔记本（默认名=GitHub 项目名）
2) 对每个“新加入”的 source 单独生成报告和脑图（source scoped）
3) 强制中文输出（默认 zh_Hans）
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class NotebookLMProcessor:
    def __init__(self, language: str = "zh_Hans"):
        self.notebooklm_bin = "notebooklm"
        self.temp_dir = Path("/tmp/notebooklm_processor")
        self.temp_dir.mkdir(exist_ok=True)
        self.language = language
        self.results = {
            "status": "pending",
            "language": language,
            "shared_notebook": None,
            "processed_urls": [],
            "generated_files": [],
            "errors": [],
            "summary": {},
        }
        self._set_language(language)

    def run_command(self, cmd: List[str], timeout: int = 300) -> Tuple[int, str, str]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return 1, "", str(e)

    def _json(self, text: str) -> Optional[dict]:
        try:
            return json.loads(text)
        except Exception:
            return None

    def _set_language(self, language: str) -> bool:
        rc, _, err = self.run_command([self.notebooklm_bin, "language", "set", language], timeout=60)
        if rc == 0:
            return True
        self.results["errors"].append(f"Failed to set language {language}: {err}")
        return False

    def verify_notebooklm_auth(self) -> bool:
        rc, out, _ = self.run_command([self.notebooklm_bin, "auth", "check", "--json"], timeout=30)
        if rc != 0:
            return False
        data = self._json(out) or {}
        return data.get("status") == "ok"

    def list_notebooks(self) -> List[dict]:
        rc, out, err = self.run_command([self.notebooklm_bin, "list", "--json"], timeout=60)
        if rc != 0:
            self.results["errors"].append(f"Failed to list notebooks: {err}")
            return []
        data = self._json(out)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for k in ("notebooks", "items", "data"):
                if isinstance(data.get(k), list):
                    return data[k]
        return []

    def create_notebook(self, title: str) -> Optional[str]:
        rc, out, err = self.run_command([self.notebooklm_bin, "create", title, "--json"], timeout=120)
        if rc != 0:
            self.results["errors"].append(f"Failed to create notebook '{title}': {err}")
            return None
        data = self._json(out) or {}
        nb = data.get("notebook") if isinstance(data.get("notebook"), dict) else data
        nid = nb.get("id") if isinstance(nb, dict) else None
        if not nid:
            self.results["errors"].append(f"Create notebook returned no id: {out[:300]}")
            return None
        return nid

    def get_or_create_shared_notebook(self, title: str) -> Optional[str]:
        notebooks = self.list_notebooks()
        for nb in notebooks:
            nb_title = nb.get("title") or nb.get("name")
            if nb_title == title:
                nid = nb.get("id")
                if nid:
                    return nid
        return self.create_notebook(title)

    def add_source(self, notebook_id: str, source_url: str) -> Optional[str]:
        rc, out, err = self.run_command([
            self.notebooklm_bin, "source", "add", source_url, "-n", notebook_id, "--json"
        ], timeout=300)
        if rc != 0:
            self.results["errors"].append(f"Failed to add source {source_url}: {err}")
            return None
        data = self._json(out) or {}
        src = data.get("source") if isinstance(data.get("source"), dict) else data
        sid = src.get("id") if isinstance(src, dict) else None
        if not sid:
            self.results["errors"].append(f"Add source returned no id for {source_url}: {out[:300]}")
            return None
        return sid

    def wait_source_processing(self, notebook_id: str, source_id: str, timeout: int = 900) -> bool:
        rc, _, err = self.run_command([
            self.notebooklm_bin, "source", "wait", source_id, "-n", notebook_id, "--timeout", str(timeout)
        ], timeout=timeout + 30)
        if rc == 0:
            return True
        self.results["errors"].append(f"Source wait failed ({source_id}): {err}")
        return False

    def generate_and_download(self, notebook_id: str, source_id: str, artifact_type: str, output_path: Path) -> bool:
        gen_cmd = [self.notebooklm_bin, "generate", artifact_type, "-n", notebook_id, "-s", source_id, "--language", self.language, "--json"]
        if artifact_type == "report":
            gen_cmd.extend(["--format", "briefing-doc"])  # 统一概览格式

        rc, out, err = self.run_command(gen_cmd, timeout=1800)
        if rc != 0:
            self.results["errors"].append(f"Generate {artifact_type} failed: {err}")
            return False

        data = self._json(out) or {}
        task_id = data.get("task_id")

        # report 通常异步，mind-map 有时同步
        if artifact_type == "report" and task_id:
            rc, _, wait_err = self.run_command([
                self.notebooklm_bin, "artifact", "wait", task_id, "-n", notebook_id, "--timeout", "900"
            ], timeout=1200)
            if rc != 0:
                self.results["errors"].append(f"Artifact wait failed ({task_id}): {wait_err}")
                return False

        if artifact_type == "report":
            dl_cmd = [self.notebooklm_bin, "download", "report", str(output_path), "-n", notebook_id]
        else:
            dl_cmd = [self.notebooklm_bin, "download", "mind-map", str(output_path), "-n", notebook_id]

        rc, _, err = self.run_command(dl_cmd, timeout=600)
        if rc != 0:
            self.results["errors"].append(f"Download {artifact_type} failed: {err}")
            return False

        self.results["generated_files"].append({
            "type": artifact_type,
            "path": str(output_path),
            "source_id": source_id,
            "language": self.language,
        })
        return True

    def extract_video_id(self, url: str) -> Optional[str]:
        m = re.search(r"(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]+)", url)
        return m.group(1) if m else None

    def process_one_url(self, notebook_id: str, url: str) -> Dict:
        row = {
            "url": url,
            "success": False,
            "notebook_id": notebook_id,
            "source_id": None,
            "report_path": None,
            "mindmap_path": None,
            "error": None,
        }

        vid = self.extract_video_id(url)
        if not vid:
            row["error"] = "invalid_youtube_url"
            self.results["errors"].append(f"Invalid YouTube URL: {url}")
            return row

        sid = self.add_source(notebook_id, url)
        if not sid:
            row["error"] = "add_source_failed"
            return row
        row["source_id"] = sid

        if not self.wait_source_processing(notebook_id, sid):
            row["error"] = "source_processing_timeout_or_failed"
            return row

        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        report_path = self.temp_dir / f"{vid}_{sid}_{ts}_report.md"
        mindmap_path = self.temp_dir / f"{vid}_{sid}_{ts}_mindmap.json"

        # 关键：仅基于新加入 source_id 生成（满足“继续研究只选中新加入”）
        ok_report = self.generate_and_download(notebook_id, sid, "report", report_path)
        ok_map = self.generate_and_download(notebook_id, sid, "mind-map", mindmap_path)

        if not ok_report:
            row["error"] = "generate_report_failed"
            return row
        if not ok_map:
            row["error"] = "generate_mindmap_failed"
            return row

        row["report_path"] = str(report_path)
        row["mindmap_path"] = str(mindmap_path)

        # 转换为 Obsidian Canvas 格式
        try:
            import uuid as _uuid
            with open(mindmap_path, 'r', encoding='utf-8') as f:
                mm = json.load(f)

            # 将 notebooklm mindmap JSON 转为 Obsidian Canvas
            canvas_nodes = []
            canvas_edges = []

            # NotebookLM mindmap 通常有 title 和 nodes/children 结构
            # 递归提取节点
            def extract_nodes(node, parent_id=None, x=0, y=0, depth=0):
                node_id = str(_uuid.uuid4())[:8]
                label = node.get('title') or node.get('label') or node.get('text') or str(node)
                canvas_nodes.append({
                    "id": node_id,
                    "type": "text",
                    "text": label,
                    "x": x,
                    "y": y,
                    "width": 200,
                    "height": 60
                })
                if parent_id:
                    canvas_edges.append({
                        "id": str(_uuid.uuid4())[:8],
                        "fromNode": parent_id,
                        "toNode": node_id
                    })
                children = node.get('children') or node.get('nodes') or []
                for i, child in enumerate(children):
                    extract_nodes(child, node_id, x + 250, y + i * 80, depth + 1)
                return node_id

            def clean_text(text):
                """Extract clean label from node text, handles Python dict strings."""
                if isinstance(text, dict):
                    return text.get('name') or text.get('label') or text.get('title') or str(text)
                if isinstance(text, str) and text.startswith("{"):
                    try:
                        import ast as _ast
                        d = _ast.literal_eval(text)
                        if isinstance(d, dict):
                            return d.get('name') or d.get('label') or d.get('title') or text
                    except Exception:
                        pass
                return text or "节点"

            # 从顶层开始提取
            if isinstance(mm, dict):
                if 'nodes' in mm and 'edges' in mm:
                    # 已经是图结构，清理 text 字段
                    canvas_nodes = [
                        {**n, "text": clean_text(n.get("text", ""))}
                        for n in mm['nodes']
                    ]
                    canvas_edges = mm.get('edges', [])
                else:
                    extract_nodes(mm, x=0, y=0)
            elif isinstance(mm, list):
                for i, item in enumerate(mm):
                    extract_nodes(item, x=0, y=i*100)

            canvas = {"nodes": canvas_nodes, "edges": canvas_edges}

            # 直接覆盖写入 .json 文件（Canvas 格式是合法 JSON，扩展名保持 .json）
            # Stage B 统一使用 .json 扩展名，Stage C 和 Obsidian 均可解析 Canvas JSON
            with open(mindmap_path, 'w', encoding='utf-8') as f:
                json.dump(canvas, f, ensure_ascii=False, indent=2)
            # mindmap_path 不变，仍为 .json

        except Exception as e:
            self.results["errors"].append(f"Canvas conversion failed for {vid}: {e}")
            # 保留原 json 文件

        row["success"] = True

        # 注入元数据 frontmatter — 让 report 文件自携带关联信息
        # Stage B copy 时原样保留，Stage C 读取时直接获取 video_url / mindmap_file
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.startswith("---"):
                # mindmap_path 可能已更新为 .canvas 路径
                fm = (
                    f"---\n"
                    f"video_id: {vid}\n"
                    f"video_url: {url}\n"
                    f"source_id: {sid}\n"
                    f"mindmap_file: {mindmap_path.name}\n"
                    f"processed_at: {ts}\n"
                    f"---\n\n"
                )
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(fm + content)
        except Exception as e:
            self.results["errors"].append(f"Frontmatter inject failed for {vid}: {e}")

        return row

    def process_youtube_links(self, youtube_links: List[str], notebook_title: str) -> Dict:
        if not self.verify_notebooklm_auth():
            self.results["status"] = "failed"
            self.results["errors"].append("NotebookLM authentication failed")
            return self.results

        nb_id = self.get_or_create_shared_notebook(notebook_title)
        if not nb_id:
            self.results["status"] = "failed"
            self.results["errors"].append(f"Failed to get/create shared notebook: {notebook_title}")
            return self.results

        self.results["shared_notebook"] = {"title": notebook_title, "id": nb_id}

        rows = [self.process_one_url(nb_id, u) for u in youtube_links]
        self.results["processed_urls"] = rows

        success_n = sum(1 for r in rows if r["success"])
        total_n = len(rows)
        fail_n = total_n - success_n
        self.results["summary"] = {"total": total_n, "successful": success_n, "failed": fail_n}

        if success_n == total_n:
            self.results["status"] = "success"
        elif success_n > 0:
            self.results["status"] = "partial_success"
        else:
            self.results["status"] = "failed"

        return self.results


def main():
    parser = argparse.ArgumentParser(description="NotebookLM Processor")
    parser.add_argument("urls", nargs="+", help="YouTube URLs to process")
    parser.add_argument("--language", default="zh_Hans", help="Output language (default: zh_Hans)")
    parser.add_argument("--notebook-title", default="youtube-video-research-wiki", help="Shared notebook title")
    args = parser.parse_args()

    p = NotebookLMProcessor(language=args.language)
    result = p.process_youtube_links(args.urls, notebook_title=args.notebook_title)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["status"] == "success":
        sys.exit(0)
    if result["status"] == "partial_success":
        sys.exit(1)
    sys.exit(2)


if __name__ == "__main__":
    main()

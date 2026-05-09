#!/usr/bin/env python3
"""
copy-and-rename-output.py — 将 NotebookLM Processor 的输出文件按中文标题重命名并复制到仓库

用法:
  python3 copy-and-rename-output.py <processor_json_file> <wiki_path>
  cat <processor_json> | python3 copy-and-rename-output.py - <wiki_path>

功能:
  1. 从 processor JSON 中读取 generated_files
  2. 为每个 report 提取中文标题（跳过 YAML frontmatter）
  3. 生成语义化 slug（保留 CJK/字母/数字，其余替换为 -，截取 40 字符）
  4. 复制报告到 raw/notebooklm-analysis/{slug}.md
  5. 复制脑图到 raw/notebooklm-mindmaps/{slug}.json（自动处理 .canvas 后缀问题）
  6. 验证脑图 JSON 合法性
  7. 更新报告 frontmatter 中的 mindmap_file 字段
  8. 输出 JSON 摘要到 stdout

返回码:
  0 — 全部成功
  1 — 部分失败（至少一个报告或脑图复制失败）
"""

import sys
import json
import re
import os
import shutil
import glob
from typing import Optional


def make_slug(title: str) -> str:
    """将中文标题转换为语义化 slug"""
    result = []
    for ch in title:
        if ('\u4e00' <= ch <= '\u9fff'
                or 'a' <= ch <= 'z'
                or 'A' <= ch <= 'Z'
                or '0' <= ch <= '9'):
            result.append(ch)
        else:
            result.append('-')
    slug = ''.join(result)
    slug = re.sub(r'-+', '-', slug)   # 合并连续 -
    slug = slug.strip('-')             # 去除首尾 -
    slug = slug[:40]                   # 截取前 40 字符
    slug = slug.strip('-')             # 再次去除可能的新首尾 -
    return slug


def extract_title(report_path: str) -> Optional[str]:
    """从 report 文件中提取 # 标题（跳过 YAML frontmatter）"""
    with open(report_path, 'r') as f:
        lines = f.readlines()

    in_frontmatter = False
    for i, line in enumerate(lines):
        if i == 0 and line.strip() == '---':
            in_frontmatter = True
            continue
        if in_frontmatter and line.strip() == '---':
            in_frontmatter = False
            continue
        if not in_frontmatter and line.startswith('# '):
            return line[2:].strip()
    return None


def find_actual_mindmap(video_id: str, expected_path: str) -> Optional[str]:
    """
    查找真实的脑图文件。
    processor 返回的 path 后缀可能是 .json 但磁盘上是 .canvas。
    """
    if os.path.exists(expected_path):
        return expected_path

    # 用 video_id 前缀搜索
    tmp_dir = os.path.dirname(expected_path)
    pattern = os.path.join(tmp_dir, f"{video_id}_*_mindmap.*")
    matches = glob.glob(pattern)
    if matches:
        return matches[0]
    return None


def validate_json(filepath: str) -> bool:
    """验证文件是否为合法 JSON"""
    try:
        with open(filepath, 'r') as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, OSError):
        return False


def process_processor_output(processor_json: dict, wiki_path: str) -> dict:
    """处理 processor 输出，生成并复制文件"""
    generated = processor_json.get("generated_files", [])
    if not generated:
        return {"status": "error", "message": "No generated_files in processor output"}

    reports = [f for f in generated if f["type"] == "report"]
    mindmaps = [f for f in generated if f["type"] == "mind-map"]

    results = []
    all_ok = True

    # 先处理所有 report，提取标题
    report_by_video = {}
    for rf in reports:
        src_path = rf["path"]
        basename = os.path.basename(src_path)
        video_id = basename.split('_')[0]

        title = extract_title(src_path)
        if not title:
            results.append({
                "video_id": video_id,
                "type": "report",
                "status": "failed",
                "error": "Could not extract title from report"
            })
            all_ok = False
            continue

        slug = make_slug(title)
        dest_path = os.path.join(wiki_path, "raw", "notebooklm-analysis", f"{slug}.md")
        shutil.copy2(src_path, dest_path)
        results.append({
            "video_id": video_id,
            "type": "report",
            "status": "ok",
            "title": title,
            "slug": slug,
            "src": src_path,
            "dest": dest_path,
            "size_bytes": os.path.getsize(dest_path)
        })
        report_by_video[video_id] = {"slug": slug, "dest": dest_path, "title": title}

    # 处理 mindmap
    for mf in mindmaps:
        src_path = mf["path"]
        basename = os.path.basename(src_path)
        video_id = basename.split('_')[0]

        actual_path = find_actual_mindmap(video_id, src_path)
        if not actual_path:
            results.append({
                "video_id": video_id,
                "type": "mindmap",
                "status": "failed",
                "error": "Mindmap file not found on disk"
            })
            all_ok = False
            continue

        slug = report_by_video.get(video_id, {}).get("slug")
        if not slug:
            results.append({
                "video_id": video_id,
                "type": "mindmap",
                "status": "failed",
                "error": "No report slug available for mindmap (report may have failed)"
            })
            all_ok = False
            continue

        dest_path = os.path.join(wiki_path, "raw", "notebooklm-mindmaps", f"{slug}.json")
        shutil.copy2(actual_path, dest_path)

        json_valid = validate_json(dest_path)
        results.append({
            "video_id": video_id,
            "type": "mindmap",
            "status": "ok" if json_valid else "invalid_json",
            "slug": slug,
            "src": actual_path,
            "dest": dest_path,
            "size_bytes": os.path.getsize(dest_path),
            "json_valid": json_valid
        })
        if not json_valid:
            all_ok = False

    # 更新 report frontmatter 中的 mindmap_file 字段
    for video_id, info in report_by_video.items():
        slug = info["slug"]
        dest = info["dest"]
        mindmap_exists = any(
            r["video_id"] == video_id
            and r["type"] == "mindmap"
            and r["status"] == "ok"
            for r in results
        )
        if not mindmap_exists:
            continue
        with open(dest, 'r') as f:
            content = f.read()
        content = re.sub(
            r'^mindmap_file:.*$',
            f'mindmap_file: {slug}.json',
            content,
            flags=re.MULTILINE
        )
        with open(dest, 'w') as f:
            f.write(content)

    return {
        "status": "ok" if all_ok else "partial",
        "total_reports": len(reports),
        "total_mindmaps": len(mindmaps),
        "results": results
    }


def main():
    if len(sys.argv) < 3:
        print("用法:", file=sys.stderr)
        print(f"  {sys.argv[0]} <processor_json_file> <wiki_path>", file=sys.stderr)
        print(f"  cat <json> | {sys.argv[0]} - <wiki_path>", file=sys.stderr)
        sys.exit(1)

    json_source = sys.argv[1]
    wiki_path = sys.argv[2]

    if json_source == '-':
        processor_json = json.load(sys.stdin)
    else:
        with open(json_source, 'r') as f:
            processor_json = json.load(f)

    result = process_processor_output(processor_json, wiki_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "ok" else 1)


if __name__ == "__main__":
    main()

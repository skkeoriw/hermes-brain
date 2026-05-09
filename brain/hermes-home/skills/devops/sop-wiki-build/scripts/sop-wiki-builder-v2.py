#!/usr/bin/env python3
"""
SOP Stage C v2: Process each analysis report sequentially with LLM API.
Fallback when the single-call script (sop_wiki_builder.py) truncates or times out
for 3+ reports.
"""
import argparse, json, os, re, subprocess, sys, urllib.request
from datetime import datetime
from pathlib import Path

def read_file(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except:
        return ""

def call_llm(prompt: str, timeout: int = 180) -> str:
    """Call LLM API, prefer DeepSeek since it has larger output capacity."""
    if os.environ.get("DEEPSEEK_API_KEY"):
        api_key = os.environ["DEEPSEEK_API_KEY"]
        base_url = "https://api.deepseek.com/v1"
        model = "deepseek-chat"
    elif os.environ.get("DASHSCOPE_API_KEY"):
        api_key = os.environ["DASHSCOPE_API_KEY"]
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        model = "qwen-plus"
    else:
        raise RuntimeError("No API key found")

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 12000,
        "temperature": 0.3
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]

def extract_json(text: str) -> dict:
    text = re.sub(r'^```json\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'^```\s*$', '', text.strip(), flags=re.MULTILINE)
    text = text.strip()
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        text = text[start:end+1]
    return json.loads(text)

def git_run(args, cwd):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki-path", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--before-sha", default="")
    parser.add_argument("--sha", default="HEAD")
    args = parser.parse_args()

    wiki_path = Path(args.wiki_path)
    run_id = args.run_id
    start_time = datetime.utcnow()
    print(f"[v2] Starting run {run_id}")

    schema = read_file(wiki_path / "TheSchema.md")
    existing_index = read_file(wiki_path / "index.md")

    # Gather all reports
    reports = []
    for report_file in sorted((wiki_path / "raw/notebooklm-analysis").glob("*.md")):
        content = read_file(report_file)
        mindmap_text = ""
        mindmap_file = wiki_path / "raw/notebooklm-mindmaps" / (report_file.stem + ".json")
        if mindmap_file.exists():
            try:
                mm = json.loads(mindmap_file.read_text())
                nodes = mm.get("nodes", [])[:20]
                mindmap_text = "\n".join(f"- {n.get('text','')}" for n in nodes)
            except:
                pass
        reports.append({
            "filename": report_file.name,
            "content": content,
            "mindmap": mindmap_text
        })

    if not reports:
        print("[v2] No reports found, skipping.")
        sys.exit(0)

    print(f"[v2] Found {len(reports)} reports. Processing each one separately...")

    all_pages = []
    all_index_entries = {
        "Sources": [], "Entities": [], "Concepts": [],
        "Comparisons": [], "Overview": []
    }
    total_stats = {"sources": 0, "entities": 0, "concepts": 0,
                   "comparisons": 0, "overviews": 0}

    for i, report in enumerate(reports):
        print(f"[v2] --- Report {i+1}/{len(reports)}: {report['filename']} ---")

        prompt = f"""你是一个知识图谱构建专家。以下是 TheSchema.md 规范和一份分析报告。

## TheSchema.md（核心规范）
{schema[:5000] if len(schema) > 5000 else schema}

## 任务
根据以下分析报告生成 wiki 页面。

报告文件名: {report['filename']}
报告内容:
{report['content'][:5000] if len(report['content']) > 5000 else report['content']}

脑图:
{report['mindmap'][:1500] if len(report['mindmap']) > 1500 else report['mindmap']}

## 输出格式（JSON）
{{
  "pages": [
    {{"path": "wiki/sources/文件名.md", "content": "完整 markdown"}}
  ],
  "index_entries": {{
    "Sources": ["- [[path|title]] — summary"],
    "Entities": [], "Concepts": [], "Comparisons": [], "Overview": []
  }},
  "stats": {{"sources": 1, "entities": 2, "concepts": 4, "comparisons": 0, "overviews": 0}}
}}

## 要求
- 创建 1 个 source 页 + 2-4 个 entity 页 + 4-6 个 concept 页
- 检查是否需要 comparison 页（两个实体直接对比时）
- 内容用中文，frontmatter 字段名用英文
- entity 文件名用小写 slug（hermes-agent.md），source/concept 用中文
- wikilink 用小写 slug 格式：[[hermes-agent]]
- 直接返回 JSON，不要额外文字"""

        try:
            print(f"[v2] Calling API for report {i+1}...")
            response_text = call_llm(prompt, timeout=180)
            print(f"[v2] Got response ({len(response_text)} chars)")

            plan = extract_json(response_text)
            pages = plan.get("pages", [])
            stats = plan.get("stats", {})
            entries = plan.get("index_entries", {})

            for page in pages:
                clean_path = page["path"].rstrip(".md") + ".md"
                file_path = wiki_path / clean_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(page["content"], encoding="utf-8")
                all_pages.append(page["path"])
                print(f"[v2]   Written: {page['path']}")

            for k in total_stats:
                total_stats[k] += stats.get(k, 0)
            for section in all_index_entries:
                all_index_entries[section].extend(entries.get(section, []))

        except Exception as e:
            print(f"[v2] ERROR on report {i+1}: {e}")
            continue

    print(f"[v2] Total pages created: {len(all_pages)}")

    # Write index.md
    end_time = datetime.utcnow()
    idx = "# Wiki Index\n\n> YouTube 视频研究知识图谱。\n"
    idx += f"> Last updated: {start_time.strftime('%Y-%m-%d')} | Total pages: {len(all_pages)}\n\n"
    for section, label in [("Sources","## Sources"), ("Entities","## Entities"),
                           ("Concepts","## Concepts"), ("Comparisons","## Comparisons"),
                           ("Overview","## Overview"), ("Queries","## Queries")]:
        idx += f"{label}\n"
        for entry in all_index_entries.get(section, []):
            idx += entry + "\n"
        idx += "\n"
    (wiki_path / "index.md").write_text(idx, encoding="utf-8")

    # Write pipeline-context.json
    duration = int((end_time - start_time).total_seconds())
    ctx_file = wiki_path / "raw/pipeline-context.json"
    ctx = {}
    if ctx_file.exists():
        try:
            ctx = json.loads(ctx_file.read_text())
        except:
            pass
    ctx["stage_c"] = {
        "run_id": run_id,
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_s": duration,
        "api_calls": len(reports),
        "pages_created": len(all_pages),
        "sources": total_stats["sources"],
        "entities": total_stats["entities"],
        "concepts": total_stats["concepts"],
        "comparisons": total_stats["comparisons"],
        "overviews": total_stats["overviews"]
    }
    ctx_file.write_text(json.dumps(ctx, ensure_ascii=False, indent=2))

    # Write run log
    log = f"""---
run_id: {run_id}
stage: stage_c
start_time: {start_time.strftime('%Y-%m-%dT%H:%M:%SZ')}
end_time: {end_time.strftime('%Y-%m-%dT%H:%M:%SZ')}
duration_s: {duration}
api_calls: {len(reports)}
pages_created: {len(all_pages)}
sources: {total_stats['sources']}
entities: {total_stats['entities']}
concepts: {total_stats['concepts']}
comparisons: {total_stats['comparisons']}
overviews: {total_stats['overviews']}
status: success
---

# Stage C Run Log

Pages written: {len(all_pages)}
Duration: {duration}s ({len(reports)} LLM API calls)

## Files Created
"""
    for p in all_pages:
        log += f"- {p}\n"

    log_file = wiki_path / f"logs/webhook-runs/{run_id}.md"
    log_file.write_text(log, encoding="utf-8")

    # Git commit + push
    git_run(["add", "wiki/", "index.md", "log.md", "logs/", "raw/pipeline-context.json"], wiki_path)
    result = git_run(["status", "--porcelain"], wiki_path)
    if result.stdout.strip():
        git_run(["commit", "-m", f"chore: update llm wiki graph [run:{run_id}]"], wiki_path)
        for i in range(3):
            r = git_run(["push", "origin", "main"], wiki_path)
            if r.returncode == 0:
                print(f"[v2] Push successful")
                break
            git_run(["pull", "--ff-only", "origin", "main"], wiki_path)

    print(f"[v2] Done: {len(all_pages)} pages in {duration}s ({len(reports)} API calls)")
    print(json.dumps({"status": "success", "pages": len(all_pages), "duration_s": duration}))

if __name__ == "__main__":
    main()

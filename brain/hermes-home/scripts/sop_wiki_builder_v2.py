#!/usr/bin/env python3
"""SOP Stage C v2: Process each analysis report sequentially with LLM API"""
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
    """Call LLM API, try DeepSeek first, fallback to DashScope"""
    if os.environ.get("DEEPSEEK_API_KEY"):
        api_key = os.environ["DEEPSEEK_API_KEY"]
        base_url = "https://api.deepseek.com/v1"
        model = "deepseek-chat"
    elif os.environ.get("DASHSCOPE_API_KEY"):
        api_key = os.environ["DASHSCOPE_API_KEY"]
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        model = "qwen-plus"
    else:
        raise RuntimeError("No API key found (DEEPSEEK_API_KEY or DASHSCOPE_API_KEY)")

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 16384,
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
    """Extract JSON from LLM response"""
    text = re.sub(r'^```json\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'^```\s*$', '', text.strip(), flags=re.MULTILINE)
    text = text.strip()
    # Find JSON boundaries
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

    # Read schema
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

    print(f"[v2] Processing {len(reports)} reports...")

    all_pages = []
    all_index_entries = {"Sources": [], "Entities": [], "Concepts": [], "Comparisons": [], "Overview": []}
    total_stats = {"sources": 0, "entities": 0, "concepts": 0, "comparisons": 0, "overviews": 0}

    for i, report in enumerate(reports):
        print(f"[v2] Processing report {i+1}/{len(reports)}: {report['filename']}")

        prompt = f"""你是一个知识图谱构建专家。以下是 TheSchema.md 规范和一份分析报告。

## TheSchema.md（核心规范）
{schema[:5000]}

## 任务
请根据以下分析报告，生成 wiki 页面内容。

报告文件名: {report['filename']}
报告内容:
{report['content'][:5000]}

脑图:
{report['mindmap'][:1500]}

请生成一个 JSON 对象，格式如下：
{{
  "pages": [
    {{
      "path": "wiki/sources/xxx.md",
      "content": "完整 markdown 内容，含 frontmatter"
    }}
  ],
  "index_entries": {{
    "Sources": ["- [[path|title]] — summary"],
    "Entities": [],
    "Concepts": [],
    "Comparisons": [],
    "Overview": []
  }},
  "stats": {{
    "sources": 1,
    "entities": N,
    "concepts": N,
    "comparisons": N,
    "overviews": N
  }}
}}

### 要求
- 必须创建 1 个 source 页，文件名用报告的中文标题
- 从报告中提取 2-4 个 entity 和 4-6 个 concept 页
- 所有内容用中文，frontmatter 字段名用英文
- 文件名用小写 slug（entity）或中文（source/concept）
- wikilink 使用小写 slug 格式：[[hermes-agent]]
- 直接返回 JSON，不要额外文字"""

        try:
            response_text = call_llm(prompt, timeout=180)
            print(f"[v2] Got response for report {i+1} ({len(response_text)} chars)")

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
                print(f"[v2] Written: {page['path']}")

            # Merge stats
            for k in total_stats:
                total_stats[k] += stats.get(k, 0)

            # Merge index entries
            for section in all_index_entries:
                all_index_entries[section].extend(entries.get(section, []))

        except Exception as e:
            print(f"[v2] Error processing report {i+1}: {e}")
            # Continue with next report

    print(f"[v2] Total pages created: {len(all_pages)}")

    # Update index.md
    end_time = datetime.utcnow()
    new_index = f"""# Wiki Index

> YouTube 视频研究知识图谱。所有 wiki 页面按类型分类索引。
> Last updated: {start_time.strftime('%Y-%m-%d')} | Total pages: {len(all_pages)}

## Sources
"""
    for entry in all_index_entries.get("Sources", []):
        new_index += entry + "\n"
    new_index += "\n## Entities\n"
    for entry in all_index_entries.get("Entities", []):
        new_index += entry + "\n"
    new_index += "\n## Concepts\n"
    for entry in all_index_entries.get("Concepts", []):
        new_index += entry + "\n"
    new_index += "\n## Comparisons\n"
    for entry in all_index_entries.get("Comparisons", []):
        new_index += entry + "\n"
    new_index += "\n## Overview\n"
    for entry in all_index_entries.get("Overview", []):
        new_index += entry + "\n"
    new_index += "\n## Queries\n"

    (wiki_path / "index.md").write_text(new_index, encoding="utf-8")

    # Update pipeline-context.json
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
        "sources": total_stats.get("sources", 0),
        "entities": total_stats.get("entities", 0),
        "concepts": total_stats.get("concepts", 0),
        "comparisons": total_stats.get("comparisons", 0),
        "overviews": total_stats.get("overviews", 0)
    }
    ctx_file.write_text(json.dumps(ctx, ensure_ascii=False, indent=2))

    # Write run-log
    log_content = f"""---
run_id: {run_id}
stage: stage_c
start_time: {start_time.strftime('%Y-%m-%dT%H:%M:%SZ')}
end_time: {end_time.strftime('%Y-%m-%dT%H:%M:%SZ')}
duration_s: {duration}
api_calls: {len(reports)}
pages_created: {len(all_pages)}
sources: {total_stats.get('sources', 0)}
entities: {total_stats.get('entities', 0)}
concepts: {total_stats.get('concepts', 0)}
comparisons: {total_stats.get('comparisons', 0)}
overviews: {total_stats.get('overviews', 0)}
status: success
---

# Stage C Run Log

Pages written: {len(all_pages)}
Duration: {duration}s ({len(reports)} LLM API calls)

## Files Created
"""
    for p in all_pages:
        log_content += f"- {p}\n"

    log_file = wiki_path / f"logs/webhook-runs/{run_id}.md"
    log_file.write_text(log_content, encoding="utf-8")

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

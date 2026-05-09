#!/usr/bin/env python3
"""
SOP Stage C: Wiki Builder v2
- 每份报告独立一次 API 调用（防输出截断）
- 通过 before-sha/sha 只处理本次 commit 新增的分析文件（防并发干扰）
"""
import argparse, json, os, re, subprocess, sys
from datetime import datetime
from pathlib import Path


def read_file(path):
    try:
        return open(path, encoding='utf-8').read()
    except:
        return ""


def call_llm(prompt: str) -> tuple:
    """调用 LLM API，优先级：DeepSeek > DashScope(qwen-plus) > OpenRouter(free)
    返回 (response_text, prompt_tokens, completion_tokens)
    """
    import urllib.request

    if os.environ.get("DEEPSEEK_API_KEY"):
        api_key = os.environ["DEEPSEEK_API_KEY"]
        base_url = "https://api.deepseek.com/v1"
        model_name = "deepseek-v4-flash"
        max_tokens = 16000
    elif os.environ.get("DASHSCOPE_API_KEY"):
        api_key = os.environ["DASHSCOPE_API_KEY"]
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        model_name = "qwen-plus"
        max_tokens = 16000
    else:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        base_url = "https://openrouter.ai/api/v1"
        model_name = "deepseek/deepseek-v4-flash:free"
        max_tokens = 16000

    payload = json.dumps({
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/chat/completions", data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())

    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


def build_report_prompt(schema: str, report: dict, index_content: str) -> str:
    mindmap_section = ""
    if report.get("mindmap"):
        mindmap_section = f"\n### 对应脑图（前20个节点）：\n{report['mindmap']}\n"

    return f"""你是知识图谱构建专家。根据以下单个视频分析报告，生成该报告对应的所有 wiki 页面。

## TheSchema.md（必须严格遵守）
{schema}

## 现有索引（避免重复创建已有页面）
{index_content}

## 分析报告：{report['filename']}
{report['content']}
{mindmap_section}

## 任务
为这一个报告生成以下页面：
1. **1个 Source 页**（对应本报告，唯一）
2. **所有 Entity 页**（本报告中出现的实体，如已在现有索引中则跳过）
3. **所有 Concept 页**（本报告概念，每视频至少4-5个，如已在现有索引中则跳过）
4. **Comparison 页**（有直接对比时创建）
5. **Overview 页**（仅在现有索引中已有 ≥2 个 source 时创建跨视频综述）

返回 JSON：
{{
  "pages": [
    {{"path": "wiki/sources/xxx.md", "content": "完整markdown含frontmatter"}},
    {{"path": "wiki/entities/xxx.md", "content": "..."}},
    {{"path": "wiki/concepts/xxx.md", "content": "..."}}
  ],
  "index_entries": {{
    "Sources": ["- [[slug|title]] — summary"],
    "Entities": ["..."],
    "Concepts": ["..."],
    "Comparisons": ["..."],
    "Overview": ["..."]
  }},
  "stats": {{"sources":0,"entities":0,"concepts":0,"comparisons":0,"overviews":0}}
}}

## 质量要求
**Source 页**：执行摘要3-5句 + 核心要点5-10条（具体细节）+ 关键引言（原话+背景）+ 脑图节点列举 + 关联wikilinks
**Entity 页**：≥5条核心特征/能力（具体技术细节）+ 2-3个应用场景 + 关系网络(≥2) + 关键事件/里程碑
**Concept 页**：精确定义+技术实现 + 本库具体例子（文件路径/工具名/具体数据）+ 边界区分 + 关联≥2概念+≥1实体 + ≥250字

所有内容用中文，frontmatter字段名用英文，wikilink用[[slug]]格式。直接返回JSON，不要额外说明。
"""


def parse_json(text: str) -> dict:
    text = re.sub(r'^```json\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'^```\s*$', '', text.strip(), flags=re.MULTILINE)
    return json.loads(text.strip())


def get_new_report_files(wiki_path: Path, before_sha: str, sha: str) -> list:
    """只取本次 commit 新增的分析文件，防止并发干扰"""
    if not before_sha or before_sha == sha:
        return sorted((wiki_path / "raw/notebooklm-analysis").glob("*.md"))

    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "diff", "--name-only",
         "--diff-filter=AM", before_sha, sha],
        cwd=wiki_path, capture_output=True, text=True
    )
    new_files = []
    for line in result.stdout.splitlines():
        if line.startswith("raw/notebooklm-analysis/") and line.endswith(".md"):
            p = wiki_path / line
            if p.exists():
                new_files.append(p)
    return sorted(new_files)


def git_run(args, cwd):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


def update_index(wiki_path, entries, total_pages, start_time):
    idx = f"""# Wiki Index

> YouTube 视频研究知识图谱。所有 wiki 页面按类型分类索引。
> Last updated: {start_time.strftime('%Y-%m-%d')} | Total pages: {total_pages}

## Sources
"""
    for e in entries.get("Sources", []):
        idx += e + "\n"
    idx += "\n## Entities\n"
    for e in entries.get("Entities", []):
        idx += e + "\n"
    idx += "\n## Concepts\n"
    for e in entries.get("Concepts", []):
        idx += e + "\n"
    idx += "\n## Comparisons\n"
    for e in entries.get("Comparisons", []):
        idx += e + "\n"
    idx += "\n## Overview\n"
    for e in entries.get("Overview", []):
        idx += e + "\n"
    idx += "\n## Queries\n"
    (wiki_path / "index.md").write_text(idx, encoding="utf-8")


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

    print(f"[wiki-builder] Starting run {run_id}")

    schema = read_file(wiki_path / "TheSchema.md")

    # 只取本次 commit 新增的分析文件
    report_files = get_new_report_files(wiki_path, args.before_sha, args.sha)

    if not report_files:
        print("[wiki-builder] No new analysis reports in this commit, skipping.")
        sys.exit(0)

    print(f"[wiki-builder] {len(report_files)} new report(s): {[f.name for f in report_files]}")

    for d in ["wiki/sources", "wiki/entities", "wiki/concepts",
              "wiki/comparisons", "wiki/overview", "wiki/queries", "logs/webhook-runs"]:
        (wiki_path / d).mkdir(parents=True, exist_ok=True)

    total_pt = total_ct = 0
    all_written = []
    all_index_entries = {"Sources": [], "Entities": [], "Concepts": [], "Comparisons": [], "Overview": []}
    total_stats = {"sources": 0, "entities": 0, "concepts": 0, "comparisons": 0, "overviews": 0}

    # 每份报告独立一次 API 调用，并行发出
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # 并行前统一读取一次 index（各 worker 只读不写）
    index_content = read_file(wiki_path / "index.md")

    def process_report(args):
        i, report_file = args
        content = read_file(report_file)
        mindmap_text = ""
        mf = wiki_path / "raw/notebooklm-mindmaps" / (report_file.stem + ".json")
        if mf.exists():
            try:
                mm = json.loads(mf.read_text())
                nodes = mm.get("nodes", [])[:20]
                mindmap_text = "\n".join(f"- {n.get('text', '')}" for n in nodes)
            except:
                pass

        prompt = build_report_prompt(schema, {
            "filename": report_file.name,
            "content": content,
            "mindmap": mindmap_text
        }, index_content)

        print(f"[wiki-builder] [{i}/{len(report_files)}] LLM call -> {report_file.name}")
        t0 = datetime.utcnow()
        response_text, pt, ct = call_llm(prompt)
        elapsed = int((datetime.utcnow() - t0).total_seconds())
        print(f"[wiki-builder] [{i}/{len(report_files)}] done {elapsed}s | {pt}+{ct} tokens")
        return i, report_file.name, response_text, pt, ct

    with ThreadPoolExecutor(max_workers=len(report_files)) as executor:
        futures = [executor.submit(process_report, (i, f))
                   for i, f in enumerate(report_files, 1)]
        results_raw = [f.result() for f in as_completed(futures)]

    # 汇总结果（并行完成后串行写文件）
    for i, fname, response_text, pt, ct in sorted(results_raw, key=lambda x: x[0]):
        total_pt += pt
        total_ct += ct
        try:
            result = parse_json(response_text)
        except Exception as e:
            print(f"[wiki-builder] [{i}] JSON parse failed: {e}, saving raw")
            (wiki_path / f"logs/webhook-runs/{run_id}-r{i}-raw.txt").write_text(response_text)
            continue

        for page in result.get("pages", []):
            clean_path = page["path"].rstrip(".md") + ".md"
            fp = wiki_path / clean_path
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(page["content"], encoding="utf-8")
            all_written.append(clean_path)
            print(f"[wiki-builder]   -> {clean_path}")

        for k in all_index_entries:
            all_index_entries[k].extend(result.get("index_entries", {}).get(k, []))
        for k in total_stats:
            total_stats[k] += result.get("stats", {}).get(k, 0)

    update_index(wiki_path, all_index_entries, len(all_written), start_time)

    # 更新 pipeline-context.json
    end_time = datetime.utcnow()
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
        "api_calls": len(report_files),
        "reports_processed": len(report_files),
        "pages_created": len(all_written),
        "prompt_tokens": total_pt,
        "completion_tokens": total_ct,
        **total_stats,
        "status": "success"
    }
    ctx_file.write_text(json.dumps(ctx, ensure_ascii=False, indent=2))

    # 写 run-log
    (wiki_path / f"logs/webhook-runs/{run_id}.md").write_text(f"""---
run_id: {run_id}
stage: stage_c
start_time: {start_time.strftime('%Y-%m-%dT%H:%M:%SZ')}
end_time: {end_time.strftime('%Y-%m-%dT%H:%M:%SZ')}
duration_s: {duration}
api_calls: {len(report_files)}
reports_processed: {len(report_files)}
pages_created: {len(all_written)}
prompt_tokens: {total_pt}
completion_tokens: {total_ct}
status: success
---
Reports: {len(report_files)} | Pages: {len(all_written)} | Time: {duration}s
""")

    # git commit + push
    git_run(["-c", "core.quotepath=false", "add",
             "wiki/", "index.md", "log.md", "logs/", "raw/pipeline-context.json"], wiki_path)
    if git_run(["status", "--porcelain"], wiki_path).stdout.strip():
        git_run(["commit", "-m", f"chore: update llm wiki graph [run:{run_id}]"], wiki_path)
        for _ in range(3):
            if git_run(["push", "origin", "main"], wiki_path).returncode == 0:
                break
            git_run(["pull", "--ff-only", "origin", "main"], wiki_path)

    print(f"\n[wiki-builder] Done: {len(all_written)} pages | {len(report_files)} API calls | {duration}s")
    print(json.dumps({"status": "success", "pages": len(all_written),
                      "api_calls": len(report_files), "duration_s": duration}))


if __name__ == "__main__":
    main()

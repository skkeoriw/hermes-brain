#!/usr/bin/env python3
"""
SOP Stage C: Wiki Builder - Single LLM call approach
替代 Hermes Agent 的多次调用，用一次 DeepSeek API 生成所有 wiki 页面
"""
import argparse, json, os, re, subprocess, sys
from datetime import datetime
from pathlib import Path

def read_file(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except:
        return ""

def call_deepseek(prompt: str, model: str = "deepseek-v4-flash") -> str:
    """调用 DeepSeek API，返回文本响应"""
    import urllib.request

    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    base_url = "https://api.deepseek.com/v1" if os.environ.get("DEEPSEEK_API_KEY") else "https://openrouter.ai/api/v1"
    model_name = "deepseek-v4-flash" if os.environ.get("DEEPSEEK_API_KEY") else "deepseek/deepseek-v4-flash"

    payload = json.dumps({
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 32000,
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
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]

def build_prompt(schema: str, reports: list, index_content: str) -> str:
    """构建一次性生成所有 wiki 页面的 prompt"""

    reports_text = ""
    for r in reports:
        reports_text += f"\n\n### 分析报告：{r['filename']}\n{r['content']}\n"
        if r.get('mindmap'):
            reports_text += f"\n### 对应脑图（前20个节点）：\n{r['mindmap']}\n"

    return f"""你是一个知识图谱构建专家。请根据以下输入，一次性生成所有需要的 wiki 页面内容。

## TheSchema.md（必须严格遵守）
{schema}

## 现有索引（避免重复创建已有页面）
{index_content}

## 分析报告
{reports_text}

## 任务要求

请生成一个 JSON 对象，包含所有需要创建的 wiki 页面。格式如下：

{{
  "pages": [
    {{
      "path": "wiki/sources/xxx.md",
      "content": "完整的 markdown 内容，包含 frontmatter"
    }},
    ...
  ],
  "index_entries": {{
    "Sources": ["- [[path|title]] — summary"],
    "Entities": [...],
    "Concepts": [...],
    "Comparisons": [...],
    "Overview": [...]
  }},
  "stats": {{
    "sources": 数量,
    "entities": 数量,
    "concepts": 数量,
    "comparisons": 数量,
    "overviews": 数量
  }}
}}

## 质量要求（必须满足）

**Source 页**（每个分析报告对应一个，唯一）：
- frontmatter：title/type/tags/summary/sources/created/updated/layer/confidence/video_url/mindmap
- 执行摘要（3-5句）
- 核心要点（5-10条，具体有细节）
- 关键引言（原话 + 背景分析）
- 脑图核心节点列举（从脑图数据提取）
- 关联实体 [[wikilink]]，关联概念 [[wikilink]]

**Entity 页**（每个实体一个，文件名小写 slug）：
- ≥5条核心特征/能力（每条有具体技术细节）
- 2-3个应用场景（具体场景）
- 关系网络（≥2条，注明关系类型）
- 关键事件/里程碑
- 出现的视频来源

**Concept 页**（每个视频至少4-5个概念）：
- 精确定义 + 技术实现细节
- 本库具体例子（必须有文件路径/工具名/具体数据）
- 与近似概念的边界区分
- 关联概念（≥2）+ 关联实体（≥1）
- 内容 ≥ 250 字

**Comparison 页**（有直接对比时必须创建）：
- 对比维度表格
- 核心差异分析
- 适用场景结论

**Overview 页**（同主题 source ≥2时必须创建）：
- 跨视频综合发现（L2 推断 + reasoning）
- 开放问题/L3

## 重要
- 所有内容用中文
- frontmatter 字段名用英文
- 文件名用中文语义名（不加 video_id 前缀）
- wikilink 使用小写 slug 格式：[[hermes-agent]]（不是 [[Hermes Agent]]）
- 直接返回 JSON，不要有额外说明文字
"""

def parse_json_response(text: str) -> dict:
    """从 LLM 响应中提取 JSON"""
    # 去掉 markdown 代码块
    text = re.sub(r'^```json\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'^```\s*$', '', text.strip(), flags=re.MULTILINE)
    text = text.strip()
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

    print(f"[sop_wiki_builder] Starting run {run_id}")

    # Phase 1: 收集输入
    schema = read_file(wiki_path / "TheSchema.md")
    index_content = read_file(wiki_path / "index.md")

    # 读取所有分析报告
    reports = []
    for report_file in sorted((wiki_path / "raw/notebooklm-analysis").glob("*.md")):
        content = read_file(report_file)
        # 提取对应脑图的前20个节点
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
        print("[sop_wiki_builder] No analysis reports found, skipping.")
        sys.exit(0)

    print(f"[sop_wiki_builder] Processing {len(reports)} reports...")

    # Phase 2: 一次 LLM 调用生成所有页面
    prompt = build_prompt(schema, reports, index_content)
    print(f"[sop_wiki_builder] Calling DeepSeek API (prompt size: {len(prompt)} chars)...")

    response_text = call_deepseek(prompt)
    print(f"[sop_wiki_builder] Got response ({len(response_text)} chars)")

    # Phase 3: 解析并写文件
    plan = parse_json_response(response_text)
    pages = plan.get("pages", [])
    stats = plan.get("stats", {})
    index_entries = plan.get("index_entries", {})

    # 确保目录存在
    for d in ["wiki/sources", "wiki/entities", "wiki/concepts", "wiki/comparisons", "wiki/overview", "wiki/queries", "logs/webhook-runs"]:
        (wiki_path / d).mkdir(parents=True, exist_ok=True)

    written = []
    for page in pages:
        # 防止 LLM 生成的路径已含 .md 扩展名导致重命名
        clean_path = page["path"].rstrip(".md") + ".md"
        file_path = wiki_path / clean_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(page["content"], encoding="utf-8")
        written.append(page["path"])
        print(f"[sop_wiki_builder] Written: {page['path']}")

    # Phase 4: 更新 index.md
    new_index = f"""# Wiki Index

> YouTube 视频研究知识图谱。所有 wiki 页面按类型分类索引。
> Last updated: {start_time.strftime('%Y-%m-%d')} | Total pages: {len(written)}

## Sources
"""
    for entry in index_entries.get("Sources", []):
        new_index += entry + "\n"
    new_index += "\n## Entities\n"
    for entry in index_entries.get("Entities", []):
        new_index += entry + "\n"
    new_index += "\n## Concepts\n"
    for entry in index_entries.get("Concepts", []):
        new_index += entry + "\n"
    new_index += "\n## Comparisons\n"
    for entry in index_entries.get("Comparisons", []):
        new_index += entry + "\n"
    new_index += "\n## Overview\n"
    for entry in index_entries.get("Overview", []):
        new_index += entry + "\n"
    new_index += "\n## Queries\n"

    (wiki_path / "index.md").write_text(new_index, encoding="utf-8")

    # Phase 5: 更新 pipeline-context.json
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
        "api_calls": 1,  # 只有一次！
        "pages_created": len(written),
        "sources": stats.get("sources", 0),
        "entities": stats.get("entities", 0),
        "concepts": stats.get("concepts", 0),
        "comparisons": stats.get("comparisons", 0),
        "overviews": stats.get("overviews", 0)
    }
    ctx_file.write_text(json.dumps(ctx, ensure_ascii=False, indent=2))

    # Phase 6: 写 run-log
    log_content = f"""---
run_id: {run_id}
stage: stage_c
start_time: {start_time.strftime('%Y-%m-%dT%H:%M:%SZ')}
end_time: {end_time.strftime('%Y-%m-%dT%H:%M:%SZ')}
duration_s: {duration}
api_calls: 1
pages_created: {len(written)}
sources: {stats.get('sources', 0)}
entities: {stats.get('entities', 0)}
concepts: {stats.get('concepts', 0)}
comparisons: {stats.get('comparisons', 0)}
overviews: {stats.get('overviews', 0)}
status: success
---

# Stage C Run Log

Pages written: {len(written)}
Duration: {duration}s (1 LLM API call)

## Files Created
"""
    for p in written:
        log_content += f"- {p}\n"

    log_file = wiki_path / f"logs/webhook-runs/{run_id}.md"
    log_file.write_text(log_content, encoding="utf-8")

    # Phase 7: git commit + push
    git_run(["add", "wiki/", "index.md", "log.md", "logs/", "raw/pipeline-context.json"], wiki_path)

    result = git_run(["status", "--porcelain"], wiki_path)
    if result.stdout.strip():
        git_run(["commit", "-m", f"chore: update llm wiki graph [run:{run_id}]"], wiki_path)

        for i in range(3):
            r = git_run(["push", "origin", "main"], wiki_path)
            if r.returncode == 0:
                print(f"[sop_wiki_builder] Push successful")
                break
            git_run(["pull", "--ff-only", "origin", "main"], wiki_path)

    print(f"[sop_wiki_builder] Done: {len(written)} pages in {duration}s (1 API call)")
    print(json.dumps({"status": "success", "pages": len(written), "duration_s": duration}))

if __name__ == "__main__":
    main()

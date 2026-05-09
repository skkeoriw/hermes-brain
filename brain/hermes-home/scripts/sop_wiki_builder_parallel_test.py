#!/usr/bin/env python3
"""
Stage C 并行方案测试脚本 — 不修改生产代码，不 git commit/push
测试 pre-planning call + 4 并行 generation calls 的耗时/质量/token 消耗

用法:
  source ~/.hermes/.env && unset DEEPSEEK_API_KEY && export OPENROUTER_API_KEY
  python3 ~/.hermes/scripts/sop_wiki_builder_parallel_test.py \
    --wiki-path ~/wiki/youtube-video-research-wiki \
    --output /tmp/parallel_test_output
"""
import argparse, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ── helpers ──────────────────────────────────────────────────────────────────

def read_file(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except:
        return ""

def call_deepseek(prompt: str, label: str = "") -> tuple[str, int, int]:
    """调用 API，返回 (response_text, prompt_tokens, completion_tokens)"""
    import urllib.request

    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("No API key found. Run: source ~/.hermes/.env && export OPENROUTER_API_KEY")

    use_deepseek = bool(os.environ.get("DEEPSEEK_API_KEY"))
    base_url = "https://api.deepseek.com/v1" if use_deepseek else "https://openrouter.ai/api/v1"
    model_name = "deepseek-v4-flash" if use_deepseek else "deepseek/deepseek-v4-flash"

    t0 = time.time()
    payload = json.dumps({
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 16000,
        "temperature": 0.3
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())

    elapsed = time.time() - t0
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    pt = usage.get("prompt_tokens", len(prompt) // 4)
    ct = usage.get("completion_tokens", len(text) // 4)
    print(f"  [{label}] done in {elapsed:.0f}s — prompt={pt}tok, completion={ct}tok")
    return text, pt, ct

# ── Phase 1: pre-planning prompt ─────────────────────────────────────────────

def build_planning_prompt(schema: str, reports: list) -> str:
    reports_summary = ""
    for r in reports:
        # 只用前 3000 字符摘要，节省 token
        reports_summary += f"\n### 报告：{r['filename']}\n{r['content'][:3000]}\n"

    return f"""你是知识图谱规划专家。根据分析报告，生成所有需要创建的 wiki 页面的结构化计划。

## TheSchema.md（质量要求）
{schema[:4000]}

## 分析报告摘要
{reports_summary}

## 任务
返回一个 JSON 对象，包含所有页面的计划：

{{
  "pages": [
    {{
      "path": "wiki/sources/GPT-5-5-Instant-深度分析简报-核心特性与实测表现.md",
      "type": "source",
      "title": "GPT-5.5 Instant 深度分析简报",
      "key_points": ["关键点1", "关键点2", "关键点3"],
      "related_entities": ["openai", "gpt-5-5-instant"],
      "related_concepts": ["幻觉率下降", "长期记忆"]
    }},
    ...
  ],
  "all_slugs": ["openai", "gpt-5-5-instant", "幻觉率下降", ...]
}}

要求：
- 列出全部页面（sources/entities/concepts/comparisons/overview）
- key_points 每页 3-5 条，足够具体
- all_slugs 包含所有实体和概念的 slug，供 worker 参考保证 wikilink 一致性
- 直接返回 JSON，不要有额外说明
"""

# ── Phase 2: worker generation prompts ───────────────────────────────────────

def build_worker_prompt(schema: str, reports: list, page_plan: dict, page_types: list, worker_name: str) -> str:
    assigned = [p for p in page_plan.get("pages", []) if p["type"] in page_types]
    all_slugs = page_plan.get("all_slugs", [])

    reports_text = ""
    for r in reports:
        reports_text += f"\n### 分析报告：{r['filename']}\n{r['content']}\n"
        if r.get('mindmap'):
            reports_text += f"\n### 对应脑图节点：\n{r['mindmap']}\n"

    assigned_json = json.dumps(assigned, ensure_ascii=False, indent=2)
    slugs_str = ", ".join(all_slugs[:50])

    return f"""你是知识图谱构建专家。请生成以下 wiki 页面的完整内容。

## TheSchema.md（必须严格遵守）
{schema}

## 分析报告（全文）
{reports_text}

## 本次需要生成的页面（{worker_name}，共 {len(assigned)} 页）
{assigned_json}

## 所有已知 slug 列表（用于 wikilink，确保一致性）
{slugs_str}

## 输出格式

返回 JSON：
{{
  "pages": [
    {{
      "path": "wiki/xxx/yyy.md",
      "content": "完整 markdown（含 frontmatter）"
    }},
    ...
  ]
}}

## 质量要求

**Source 页**：执行摘要3-5句 + 核心要点5-10条 + 关键引言 + 脑图节点列举 + 关联 wikilinks

**Entity 页**：≥5条核心特征/能力（具体技术细节）+ 2-3个应用场景 + 关系网络(≥2) + 关键事件/里程碑

**Concept 页**：精确定义+技术实现 + 本库具体例子（文件路径/工具名/具体数据）+ 边界区分 + 关联≥2概念+≥1实体 + ≥250字

**Comparison 页**：对比维度表格 + 核心差异分析 + 适用场景结论

**Overview 页**：跨视频综合发现 + L2推断 + 开放问题/L3

所有内容用中文，frontmatter 字段名用英文，wikilink 用 [[slug]] 格式。
直接返回 JSON，不要额外说明。
"""

# ── JSON parsing ──────────────────────────────────────────────────────────────

def parse_json(text: str) -> dict:
    text = re.sub(r'^```json\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'^```\s*$', '', text.strip(), flags=re.MULTILINE)
    return json.loads(text.strip())

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki-path", required=True)
    parser.add_argument("--output", default="/tmp/parallel_test_output", help="输出目录（测试用，不写入 wiki 仓库）")
    args = parser.parse_args()

    wiki_path = Path(args.wiki_path).expanduser()
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    total_start = time.time()
    metrics = {"calls": [], "total_prompt_tokens": 0, "total_completion_tokens": 0}

    print(f"[parallel-test] Wiki path: {wiki_path}")
    print(f"[parallel-test] Output: {output_path}")

    # 读取输入
    schema = read_file(wiki_path / "TheSchema.md")
    index_content = read_file(wiki_path / "index.md")

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
        reports.append({"filename": report_file.name, "content": content, "mindmap": mindmap_text})

    if not reports:
        print("[parallel-test] No analysis reports found.")
        sys.exit(1)

    print(f"[parallel-test] Found {len(reports)} reports")

    # ── CALL 0: pre-planning ─────────────────────────────────────────────────
    print("\n=== CALL 0: pre-planning ===")
    t0 = time.time()
    planning_prompt = build_planning_prompt(schema, reports)
    plan_text, pt0, ct0 = call_deepseek(planning_prompt, "pre-planning")
    call0_time = time.time() - t0
    metrics["calls"].append({"label": "pre-planning", "time_s": call0_time, "prompt_tokens": pt0, "completion_tokens": ct0})
    metrics["total_prompt_tokens"] += pt0
    metrics["total_completion_tokens"] += ct0

    try:
        page_plan = parse_json(plan_text)
        plan_pages = page_plan.get("pages", [])
        print(f"  Plan: {len(plan_pages)} pages planned")
        (output_path / "plan.json").write_text(json.dumps(page_plan, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"  [ERROR] Failed to parse planning response: {e}")
        (output_path / "plan_raw.txt").write_text(plan_text)
        sys.exit(1)

    # ── CALL 1-4: parallel workers ───────────────────────────────────────────
    worker_configs = [
        ("sources",          ["source"],                        "Worker-1-Sources"),
        ("entities",         ["entity"],                        "Worker-2-Entities"),
        ("concepts",         ["concept"],                       "Worker-3-Concepts"),
        ("comp_overview",    ["comparison", "overview"],        "Worker-4-Comp+Overview"),
    ]

    print("\n=== CALLS 1-4: parallel generation ===")
    parallel_start = time.time()

    def run_worker(config):
        group_name, page_types, label = config
        prompt = build_worker_prompt(schema, reports, page_plan, page_types, label)
        text, pt, ct = call_deepseek(prompt, label)
        return group_name, label, text, pt, ct

    all_pages = []
    worker_metrics = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_config = {executor.submit(run_worker, cfg): cfg for cfg in worker_configs}
        for future in as_completed(future_to_config):
            group_name, label, text, pt, ct = future.result()
            worker_metrics.append({"label": label, "prompt_tokens": pt, "completion_tokens": ct})
            metrics["total_prompt_tokens"] += pt
            metrics["total_completion_tokens"] += ct
            try:
                result = parse_json(text)
                pages = result.get("pages", [])
                all_pages.extend(pages)
                (output_path / f"worker_{group_name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"  [ERROR] {label} JSON parse failed: {e}")
                (output_path / f"worker_{group_name}_raw.txt").write_text(text)

    parallel_elapsed = time.time() - parallel_start
    metrics["calls"].extend(worker_metrics)

    # ── Write output files ───────────────────────────────────────────────────
    print(f"\n=== Writing {len(all_pages)} pages to {output_path} ===")
    for page in all_pages:
        p = page.get("path", "")
        if not p:
            continue
        clean_path = p.rstrip(".md") + ".md"
        file_path = output_path / clean_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(page.get("content", ""), encoding="utf-8")

    # ── Final report ─────────────────────────────────────────────────────────
    total_elapsed = time.time() - total_start
    total_tokens = metrics["total_prompt_tokens"] + metrics["total_completion_tokens"]

    # 简单质量检查
    quality_checks = {
        "total_pages": len(all_pages),
        "has_sources": sum(1 for p in all_pages if "/sources/" in p.get("path","")),
        "has_entities": sum(1 for p in all_pages if "/entities/" in p.get("path","")),
        "has_concepts": sum(1 for p in all_pages if "/concepts/" in p.get("path","")),
        "has_comparisons": sum(1 for p in all_pages if "/comparisons/" in p.get("path","")),
        "has_overview": sum(1 for p in all_pages if "/overview/" in p.get("path","")),
        "avg_content_length": int(sum(len(p.get("content","")) for p in all_pages) / max(len(all_pages),1)),
        "pages_under_500chars": sum(1 for p in all_pages if len(p.get("content","")) < 500),
    }

    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "timing": {
            "pre_planning_s": round(call0_time, 1),
            "parallel_workers_s": round(parallel_elapsed, 1),
            "total_s": round(total_elapsed, 1),
            "baseline_single_call_s": 347,
            "speedup_s": round(347 - total_elapsed, 1),
        },
        "tokens": {
            "prompt": metrics["total_prompt_tokens"],
            "completion": metrics["total_completion_tokens"],
            "total": total_tokens,
            "baseline_single_call": 55000,
            "overhead_tokens": total_tokens - 55000,
        },
        "quality": quality_checks,
        "per_call": metrics["calls"],
    }

    report_path = output_path / "test_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    print("\n" + "="*60)
    print("PARALLEL TEST RESULTS")
    print("="*60)
    print(f"  Total time:        {total_elapsed:.0f}s  (baseline: 347s, saved: {347-total_elapsed:.0f}s)")
    print(f"  Pre-planning call: {call0_time:.0f}s")
    print(f"  Parallel workers:  {parallel_elapsed:.0f}s  (wall clock)")
    print(f"  Pages generated:   {len(all_pages)}  (baseline: 37)")
    print(f"  Token consumption: {total_tokens:,}  (baseline: ~55K)")
    print(f"    prompt:          {metrics['total_prompt_tokens']:,}")
    print(f"    completion:      {metrics['total_completion_tokens']:,}")
    print(f"  Quality checks:")
    for k, v in quality_checks.items():
        print(f"    {k}: {v}")
    print(f"\n  Full report: {report_path}")
    print(f"  Pages output: {output_path}/wiki/")
    print("="*60)

    verdict = "PASS" if total_elapsed < 150 and len(all_pages) >= 35 else "NEEDS_REVIEW"
    print(f"\n  Verdict: {verdict}")
    if total_elapsed < 150:
        print("  ✓ Time target met (< 150s)")
    else:
        print(f"  ✗ Time target missed ({total_elapsed:.0f}s > 150s)")
    if len(all_pages) >= 35:
        print(f"  ✓ Page count target met ({len(all_pages)} >= 35)")
    else:
        print(f"  ✗ Page count target missed ({len(all_pages)} < 35)")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Stage C 按报告并行测试脚本
- 每个报告独立一个 worker（source + entities + concepts）
- 第4个 worker 处理跨报告内容（comparisons + overview）
- 无 pre-planning call
用法:
  source ~/.hermes/.env && export DEEPSEEK_API_KEY
  python3 ~/.hermes/scripts/sop_wiki_builder_by_report_test.py \
    --wiki-path ~/wiki/youtube-video-research-wiki \
    --output /tmp/by_report_test_output
"""
import argparse, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path


def read_file(path):
    try:
        return open(path, encoding='utf-8').read()
    except:
        return ""


def call_deepseek(prompt: str, label: str = "") -> tuple:
    import urllib.request
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    use_deepseek = bool(os.environ.get("DEEPSEEK_API_KEY"))
    base_url = "https://api.deepseek.com/v1" if use_deepseek else "https://openrouter.ai/api/v1"
    model_name = "deepseek-v4-flash" if use_deepseek else "deepseek/deepseek-v4-flash"
    provider = "DeepSeek直连" if use_deepseek else "OpenRouter"

    payload = json.dumps({
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 16000,
        "temperature": 0.3
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/chat/completions", data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
    elapsed = time.time() - t0
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    pt = usage.get("prompt_tokens", len(prompt) // 4)
    ct = usage.get("completion_tokens", len(text) // 4)
    print(f"  [{label}] {elapsed:.0f}s | prompt={pt} completion={ct} | {ct/elapsed:.1f} tok/s ({provider})")
    return text, pt, ct, elapsed


def parse_json(text: str) -> dict:
    text = re.sub(r'^```json\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'^```\s*$', '', text.strip(), flags=re.MULTILINE)
    return json.loads(text.strip())


def build_report_worker_prompt(schema: str, report: dict, all_slugs_hint: str) -> str:
    mindmap_section = ""
    if report.get('mindmap'):
        mindmap_section = f"\n### 脑图节点（前20个）：\n{report['mindmap']}\n"

    return f"""你是知识图谱构建专家。根据以下单个视频分析报告，生成该报告对应的所有 wiki 页面。

## TheSchema.md（必须严格遵守）
{schema}

## 分析报告：{report['filename']}
{report['content']}
{mindmap_section}

## 已知 slug 提示（用于 wikilink 一致性）
{all_slugs_hint}

## 任务
为这一个报告生成以下页面：
1. **1个 Source 页**（对应本报告）
2. **所有 Entity 页**（本报告中出现的实体）
3. **所有 Concept 页**（本报告中出现的概念，每视频至少4-5个）

返回 JSON：
{{
  "pages": [
    {{"path": "wiki/sources/xxx.md", "content": "完整markdown含frontmatter"}},
    {{"path": "wiki/entities/xxx.md", "content": "..."}},
    {{"path": "wiki/concepts/xxx.md", "content": "..."}}
  ]
}}

## 质量要求

**Source 页**：执行摘要3-5句 + 核心要点5-10条（具体细节）+ 关键引言（原话+背景）+ 脑图节点列举 + 关联 wikilinks

**Entity 页**：≥5条核心特征/能力（具体技术细节）+ 2-3个应用场景 + 关系网络(≥2条) + 关键事件/里程碑

**Concept 页**：精确定义+技术实现 + 本库具体例子（文件路径/工具名/具体数据）+ 边界区分 + 关联≥2概念+≥1实体 + ≥250字

所有内容用中文，frontmatter 字段名用英文，wikilink 用 [[slug]] 格式。直接返回 JSON。
"""


def build_cross_report_prompt(schema: str, reports: list) -> str:
    summaries = ""
    for r in reports:
        summaries += f"\n### {r['filename']}\n{r['content'][:2000]}...\n"

    return f"""你是知识图谱构建专家。根据以下多个视频报告的摘要，生成跨报告的对比和综述页面。

## TheSchema.md（必须严格遵守）
{schema[:3000]}

## 各报告摘要
{summaries}

## 任务
生成：
1. **Comparison 页**（有直接对比关系的实体/概念之间的对比，如有则生成，否则跳过）
2. **Overview 页**（跨视频综合发现，同主题≥2个视频时必须生成）

返回 JSON：
{{
  "pages": [
    {{"path": "wiki/comparisons/xxx.md", "content": "..."}},
    {{"path": "wiki/overview/xxx.md", "content": "..."}}
  ]
}}

Comparison 页：对比维度表格 + 核心差异分析 + 适用场景结论
Overview 页：跨视频综合发现（L2推断+reasoning）+ 开放问题/L3

所有内容用中文，frontmatter 字段名用英文。直接返回 JSON。
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki-path", required=True)
    parser.add_argument("--output", default="/tmp/by_report_test_output")
    args = parser.parse_args()

    wiki_path = Path(args.wiki_path).expanduser()
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    use_deepseek = bool(os.environ.get("DEEPSEEK_API_KEY"))
    print(f"[by-report-test] Provider: {'DeepSeek直连' if use_deepseek else 'OpenRouter'}")
    print(f"[by-report-test] Wiki: {wiki_path}")

    total_start = time.time()

    # 读取输入
    schema = read_file(wiki_path / "TheSchema.md")
    reports = []
    for rf in sorted((wiki_path / "raw/notebooklm-analysis").glob("*.md")):
        content = read_file(rf)
        mindmap_text = ""
        mf = wiki_path / "raw/notebooklm-mindmaps" / (rf.stem + ".json")
        if mf.exists():
            try:
                mm = json.loads(mf.read_text())
                nodes = mm.get("nodes", [])[:20]
                mindmap_text = "\n".join(f"- {n.get('text','')}" for n in nodes)
            except:
                pass
        reports.append({"filename": rf.name, "content": content, "mindmap": mindmap_text})

    print(f"[by-report-test] {len(reports)} 个报告 → {len(reports)+1} 个并行 workers\n")

    # 预先收集所有可能的 slug（简单提取报告中的实体名）
    all_slugs_hint = "（各 worker 各自推断实体/概念 slug，使用小写连字符格式）"

    # 构建所有 worker 的 prompts
    report_workers = [
        (f"Worker-R{i+1}({r['filename'][:20]})", build_report_worker_prompt(schema, r, all_slugs_hint))
        for i, r in enumerate(reports)
    ]
    cross_worker = ("Worker-Cross(comparisons+overview)", build_cross_report_prompt(schema, reports))

    all_workers = report_workers + [cross_worker]

    print(f"=== 并行执行 {len(all_workers)} 个 workers ===")
    parallel_start = time.time()

    total_pt = 0
    total_ct = 0
    all_pages = []
    worker_results = []

    def run_worker(label_prompt):
        label, prompt = label_prompt
        text, pt, ct, elapsed = call_deepseek(prompt, label)
        return label, text, pt, ct, elapsed

    with ThreadPoolExecutor(max_workers=len(all_workers)) as executor:
        futures = {executor.submit(run_worker, w): w[0] for w in all_workers}
        for future in as_completed(futures):
            label, text, pt, ct, elapsed = future.result()
            total_pt += pt
            total_ct += ct
            worker_results.append({"label": label, "time_s": elapsed, "prompt": pt, "completion": ct})
            try:
                result = parse_json(text)
                pages = result.get("pages", [])
                all_pages.extend(pages)
                (output_path / f"worker_{label[:30].replace('/','_')}.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2))
                print(f"  [{label[:30]}] → {len(pages)} pages parsed OK")
            except Exception as e:
                print(f"  [{label[:30]}] → JSON parse FAILED: {e}")
                (output_path / f"worker_{label[:30].replace('/','_')}_raw.txt").write_text(text)

    parallel_elapsed = time.time() - parallel_start
    total_elapsed = time.time() - total_start

    # 写出文件
    for page in all_pages:
        p = page.get("path", "")
        if not p:
            continue
        fp = output_path / (p.rstrip(".md") + ".md")
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(page.get("content", ""), encoding="utf-8")

    # 质量检查
    qc = {
        "total_pages": len(all_pages),
        "sources": sum(1 for p in all_pages if "/sources/" in p.get("path","")),
        "entities": sum(1 for p in all_pages if "/entities/" in p.get("path","")),
        "concepts": sum(1 for p in all_pages if "/concepts/" in p.get("path","")),
        "comparisons": sum(1 for p in all_pages if "/comparisons/" in p.get("path","")),
        "overview": sum(1 for p in all_pages if "/overview/" in p.get("path","")),
        "avg_content_len": int(sum(len(p.get("content","")) for p in all_pages) / max(len(all_pages),1)),
        "pages_under_500chars": sum(1 for p in all_pages if len(p.get("content","")) < 500),
    }

    report_data = {
        "provider": "DeepSeek直连" if use_deepseek else "OpenRouter",
        "approach": "by-report-parallel",
        "timing": {
            "parallel_wall_clock_s": round(parallel_elapsed, 1),
            "total_s": round(total_elapsed, 1),
        },
        "tokens": {"prompt": total_pt, "completion": total_ct, "total": total_pt + total_ct},
        "quality": qc,
        "per_worker": sorted(worker_results, key=lambda x: -x["time_s"]),
    }
    (output_path / "test_report.json").write_text(json.dumps(report_data, ensure_ascii=False, indent=2))

    print("\n" + "="*60)
    print("BY-REPORT PARALLEL RESULTS")
    print("="*60)
    print(f"  Provider:      {'DeepSeek直连' if use_deepseek else 'OpenRouter'}")
    print(f"  Wall clock:    {parallel_elapsed:.0f}s")
    print(f"  Total:         {total_elapsed:.0f}s")
    print(f"  Pages:         {len(all_pages)}")
    print(f"  Tokens:        prompt={total_pt:,}  completion={total_ct:,}  total={total_pt+total_ct:,}")
    print(f"  Quality: {qc}")
    print(f"\n  Per-worker breakdown:")
    for w in sorted(worker_results, key=lambda x: -x["time_s"]):
        rate = w["completion"] / w["time_s"] if w["time_s"] > 0 else 0
        print(f"    {w['label'][:40]:40s}: {w['time_s']:.0f}s | {w['completion']} tokens | {rate:.1f} tok/s")
    print("="*60)


if __name__ == "__main__":
    main()

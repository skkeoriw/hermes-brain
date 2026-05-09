#!/usr/bin/env python3
"""
SOP Stage D: TG Notify - Pure Python, no LLM needed
读取 pipeline-context.json，组装消息，发送 Telegram
"""
import json, os, sys, subprocess, shutil
from datetime import datetime
from pathlib import Path

def send_telegram(token: str, chat_id: str, text: str) -> bool:
    result = subprocess.run([
        "curl", "-s", "-X", "POST",
        f"https://api.telegram.org/bot{token}/sendMessage",
        "-d", f"chat_id={chat_id}",
        "-d", "disable_web_page_preview=true",
        "--data-urlencode", f"text={text}",
        "-w", "\nHTTP_STATUS:%{http_code}"
    ], capture_output=True, text=True)
    return "HTTP_STATUS:200" in result.stdout

def git_run(args, cwd):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki-path", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--tg-token-env", default="YOUTUBE_WIKI_TG_TOKEN")
    parser.add_argument("--tg-chat-id", required=True)
    parser.add_argument("--repo-url", default="")
    args = parser.parse_args()

    wiki_path = Path(args.wiki_path)
    token = os.environ.get(args.tg_token_env, "")

    if not token:
        print(f"[sop_tg_notify] No token found in env var {args.tg_token_env}")
        sys.exit(1)

    # 读取 pipeline-context.json
    ctx_file = wiki_path / "raw/pipeline-context.json"
    if not ctx_file.exists():
        # 尝试从 logs 里找最新的
        logs = sorted((wiki_path / "logs/pipeline-runs").glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        if logs:
            ctx_file = logs[0]
        else:
            print("[sop_tg_notify] No pipeline-context.json found")
            sys.exit(1)

    ctx = json.loads(ctx_file.read_text())
    stage_b = ctx.get("stage_b", {})
    stage_c = ctx.get("stage_c", {})

    # 读取 source 页的标题和 video_url
    sources = []
    for src_file in sorted((wiki_path / "wiki/sources").glob("*.md")):
        content = src_file.read_text(encoding="utf-8")
        title = ""
        video_url = ""
        for line in content.split("\n"):
            if line.startswith("title:"):
                title = line.split(":", 1)[1].strip().strip('"')
            if line.startswith("video_url:"):
                video_url = line.split(":", 1)[1].strip()
        if title:
            sources.append({"title": title, "url": video_url, "file": src_file.stem})

    # 组装消息
    total_dur = stage_b.get("duration_s", 0) + stage_c.get("duration_s", 0)
    total_pages = stage_c.get("pages_created", 0)

    video_lines = "\n".join(f"  {i+1}. {s['title']}" for i, s in enumerate(sources))

    nav_lines = ""
    if args.repo_url:
        for s in sources:
            encoded = s['file'].replace(" ", "%20")
            nav_lines += f"  · {s['title'][:25]}...\n    {args.repo_url}/blob/main/wiki/sources/{encoded}.md\n"

    msg = f"""[YOUTUBE-WIKI-RUN] 🎬

📹 本次处理 {len(sources)} 条视频：
{video_lines}

⏱️ 各阶段耗时：
  Stage B (NotebookLM): {stage_b.get('duration_s', '?')}s
  Stage C (知识图谱):   {stage_c.get('duration_s', '?')}s
  全程合计:             {total_dur}s

🔢 LLM 调用：
  Stage B: {stage_b.get('api_calls', '?')} 次
  Stage C: {stage_c.get('api_calls', '1')} 次 ← 方案A一次生成

📊 知识图谱产出：
  Source: {stage_c.get('sources', 0)}  Entity: {stage_c.get('entities', 0)}
  Concept: {stage_c.get('concepts', 0)}  Comparison: {stage_c.get('comparisons', 0)}  Overview: {stage_c.get('overviews', 0)}
  总页数: {total_pages}

🔗 快捷导航：
{nav_lines if nav_lines else '  (未配置仓库 URL)'}
run: {args.run_id}"""

    # 发送 Telegram
    success = send_telegram(token, args.tg_chat_id, msg)
    print(f"[sop_tg_notify] TG sent: {success}")

    # 归档 pipeline-context.json
    archive_dir = wiki_path / "logs/pipeline-runs"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_file = archive_dir / f"pipe-{args.run_id}.json"
    shutil.copy(ctx_file, archive_file)
    if ctx_file.name == "pipeline-context.json":
        ctx_file.unlink()

    # 写 run-log
    log_file = wiki_path / f"logs/webhook-runs/{args.run_id}.md"
    log_file.write_text(f"""---
run_id: {args.run_id}
stage: stage_d
status: {"success" if success else "tg_failed"}
tg_sent: {success}
archived: logs/pipeline-runs/pipe-{args.run_id}.json
---
""", encoding="utf-8")

    # git commit + push
    git_run(["add", "logs/"], wiki_path)
    result = git_run(["status", "--porcelain"], wiki_path)
    if result.stdout.strip():
        git_run(["commit", "-m", f"chore: tg notify done [run:{args.run_id}]"], wiki_path)
        for i in range(3):
            r = git_run(["push", "origin", "main"], wiki_path)
            if r.returncode == 0:
                break
            git_run(["pull", "--ff-only", "origin", "main"], wiki_path)

    print(f"[sop_tg_notify] Done")

if __name__ == "__main__":
    main()

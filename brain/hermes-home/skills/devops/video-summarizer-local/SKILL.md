---
name: video-summarizer-local
description: Use when you want Hermes to run a fully local, isolated video transcript/summarization workflow (YouTube and other URLs) without depending on any external project checkout path.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [video, youtube, transcript, summary, docker, deepseek]
    related_skills: [hermes-agent, youtube-content]
---

# Video Summarizer (Isolated Local Skill)

## Overview
This skill runs a vendored copy of the `summarize` project from a private local path under Hermes skills, so runtime does not depend on `/home/zhouhuijuan1987/summarize`.

Vendored runtime root:
`~/.hermes/skills/devops/video-summarizer-local/vendor/summarize`

## When to Use
- You want transcript + summary features as a standalone Hermes capability.
- You do not want coupling to your existing working repo checkout.
- You want a predictable docker-compose based runtime.

## Capabilities
- Full transcript extraction (captions or audio transcription fallback)
- Summary generation with provider/model selection
- `--no-save` stdout mode or file output mode
- Multi-source support (YouTube + supported video URLs + local files)

## Runtime Commands
1) Start services:
`cd ~/.hermes/skills/devops/video-summarizer-local/vendor/summarize && docker compose up -d`

2) Health check:
`cd ~/.hermes/skills/devops/video-summarizer-local/vendor/summarize && docker compose ps`

3) Run summary:
`cd ~/.hermes/skills/devops/video-summarizer-local/vendor/summarize && docker compose exec -T summarizer python -m summarizer --source "https://www.youtube.com/watch?v=VIDEO_ID" --provider deepseek --prompt-type "Distill Wisdom" --no-save`

4) Export full transcript (inside container):
`cd ~/.hermes/skills/devops/video-summarizer-local/vendor/summarize && docker compose exec -T summarizer python - <<'PY'
from summarizer.transcription import get_transcript
cfg={
  'type_of_source':'YouTube Video',
  'source_url_or_path':'https://www.youtube.com/watch?v=VIDEO_ID',
  'use_youtube_captions':True,
  'force_download':False,
  'verbose':False,
  'language':'auto',
  'use_proxy':False,
  'cache_transcript':False,
  'audio_speed':1.0,
  'transcription_method':'Cloud Whisper',
  'whisper_model':'tiny'
}
print(get_transcript(cfg))
PY`

## Required Files
- `vendor/summarize/.env` must include keys for selected providers.
- `vendor/summarize/summarizer.yaml` should include provider profiles.

## Common Pitfalls
1) Container is up but no API keys configured in `.env`.
2) Using host python instead of container command path.
3) Assuming `--provider deepseek` controls transcription backend; summarization and transcription backend can differ.

## Verification Checklist
- [ ] `docker compose ps` shows `summarizer` and `cobalt` running
- [ ] `python -m summarizer ... --no-save` returns summary text
- [ ] transcript extraction command returns non-empty text

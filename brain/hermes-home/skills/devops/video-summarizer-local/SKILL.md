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

## Provider and Model Configuration

The summarization provider and model are configured in two places:

1. `vendor/summarize/.env` – contains API keys for each provider (e.g., `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`).

2. `vendor/summarize/summarizer.yaml` – defines provider profiles and default model.

Example `.env` snippet:
```
# Provider API keys
DEEPSEEK_API_KEY=sk-...
OPENAI_API_KEY=sk-...
```

Example `summarizer.yaml` snippet:
```
providers:
  deepseek:
    api_key: ${DEEPSEEK_API_KEY}
    base_url: https://api.deepseek.com/v1
    model: deepseek-chat
  openai:
    api_key: ${OPENAI_API_KEY}
    base_url: https://api.openai.com/v1
    model: gpt-4o-mini
default_provider: deepseek
```

When invoking the summarizer via the skill, you can override the provider with `--provider <name>` (e.g., `--provider openai`).

**Note:** The transcription step (extracting captions/audio-to-text) is independent of the summarization provider and uses its own configuration (see `transcription_method` in the transcript extraction example).

## Quick Reference

| Task | Command |
|------|---------|
| Start services | `cd ~/.hermes/skills/devops/video-summarizer-local/vendor/summarize && docker compose up -d` |
| Health check | `cd ~/.hermes/skills/devops/video-summarizer-local/vendor/summarize && docker compose ps` |
| Run summary (stdout) | `cd ~/.hermes/skills/devops/video-summarizer-local/vendor/summarize && docker compose exec -T summarizer python -m summarizer --source "https://www.youtube.com/watch?v=VIDEO_ID" --provider deepseek --prompt-type "Distill Wisdom" --no-save` |
| Run summary (save to file) | `cd ~/.hermes/skills/devops/video-summarizer-local/vendor/summarize && docker compose exec -T summarizer python -m summarizer --source "https://www.youtube.com/watch?v=VIDEO_ID" --provider deepseek --prompt-type "Distill Wisdom" --output ./summary.txt` |
| Extract full transcript (stdout) | `cd ~/.hermes/skills/devops/video-summarizer-local/vendor/summarize && docker compose exec -T summarizer python - <<'PY'\nfrom summarizer.transcription import get_transcript\ncfg={\n  'type_of_source':'YouTube Video',\n  'source_url_or_path':'https://www.youtube.com/watch?v=VIDEO_ID',\n  'use_youtube_captions':True,\n  'force_download':False,\n  'verbose':False,\n  'language':'auto',\n  'use_proxy':False,\n  'cache_transcript':False,\n  'audio_speed':1.0,\n  'transcription_method':'Cloud Whisper',\n  'whisper_model':'tiny'\n}\nprint(get_transcript(cfg))\nPY` |
| Extract transcript and save to file | `cd ~/.hermes/skills/devops/video-summarizer-local/vendor/summarize && docker compose exec -T summarizer python - <<'PY'\nfrom summarizer.transcription import get_transcript\ncfg={\n  'type_of_source':'YouTube Video',\n  'source_url_or_path':'https://www.youtube.com/watch?v=VIDEO_ID',\n  'use_youtube_captions':True,\n  'force_download':False,\n  'verbose':False,\n  'language':'auto',\n  'use_proxy':False,\n  'cache_transcript':False,\n  'audio_speed':1.0,\n  'transcription_method':'Cloud Whisper',\n  'whisper_model':'tiny'\n}\nwith open('transcript.txt', 'w', encoding='utf-8') as f:\n    f.write(get_transcript(cfg))\nPY` |

## CLI Reference (absorbed from summarize skill)

The `summarize` vendor tool's full CLI reference has been absorbed into this umbrella skill. See:

- `references/summarize-cli-reference.md` — Complete CLI flag reference, summary styles table (11 styles), examples for all provider combinations, multi-step workflow guidance, and warnings (Windows, social media Cobalt dependency, transcription fallback).

Key notes absorbed:

- **Summarization is independent of transcription** — you can use Cloud Whisper (Groq) for transcription and a different provider (DeepSeek, Gemini, OpenAI) for summarization.
- **Prompt types** control output format: use `Summarization` for overviews, `Distill Wisdom` for insights, `Fact Checker` for claim verification, `Mermaid Diagram` for visual maps.
- **No direct URL fetching** — always go through the CLI; the tool handles all downloading and transcription internally.
- **Batch processing** supported: pass multiple `--source` values.

## Provider Configuration Examples

See `references/provider-examples.md` for detailed examples of `.env` and `summarizer.yaml` configurations for various providers (DeepSeek, OpenAI, Anthropic, etc.).

## Verification Checklist
- [ ] `docker compose ps` shows `summarizer` and `cobalt` running
- [ ] `python -m summarizer ... --no-save` returns summary text
- [ ] transcript extraction command returns non-empty text

# Summarize CLI Reference

> Absorbed from the `summarize` skill (vendored upstream project). This is the engine that `video-summarizer-local` wraps in Docker.

## Overview

The `python -m summarizer` CLI transcribes videos and summarizes them using a configurable LLM. Supports 11 summary styles and multiple providers.

**Never fetch, scrape, or download video URLs directly (e.g. with WebFetch or curl). The CLI handles all downloading, transcription, and summarization internally.**

## Quick Start (inside Docker)

```bash
cd ~/.hermes/skills/devops/video-summarizer-local/vendor/summarize && \
docker compose exec -T summarizer python -m summarizer --source "VIDEO_URL"
```

## File Locations (inside the vendor directory)

| File | Location (relative to vendor/summarize/) |
|------|-----------------------------------------|
| Config | `./summarizer.yaml` |
| API keys | `./.env` |
| Prompt templates | `./summarizer/prompts.json` |
| Output summaries | `./summaries/<filename>.md` |

## CLI Flag Reference

```
python -m summarizer [OPTIONS]
```

### Required

| Flag | Description |
|------|-------------|
| `--source` | One or more video URLs or file paths |

### Provider Options

| Flag | Description | Default |
|------|-------------|---------|
| `--provider` | Named provider from `summarizer.yaml` | `default_provider` from YAML |
| `--base-url` | API endpoint URL (overrides provider) | From YAML |
| `--model` | Model identifier (overrides provider) | From YAML |
| `--api-key` | API key (overrides `.env` auto-matching) | Auto from `.env` |

### Source Options

| Flag | Description | Default |
|------|-------------|---------|
| `--type` | `YouTube Video`, `Video URL`, `Local File`, `Google Drive Video Link`, `Dropbox Video Link` | `YouTube Video` |
| `--force-download` | Skip YouTube captions, download audio instead | `False` |
| `--transcription` | `Cloud Whisper` (Groq API) or `Local Whisper` | `Cloud Whisper` |
| `--whisper-model` | `tiny`, `base`, `small`, `medium`, `large` | `tiny` |
| `--language` | Language code or `auto` (uses first available caption track, lets Whisper detect language) | `auto` |

### Processing Options

| Flag | Description | Default |
|------|-------------|---------|
| `--prompt-type` | Summary style (see Styles below) | From YAML defaults |
| `--chunk-size` | Characters per text chunk | From YAML defaults |
| `--parallel-calls` | Concurrent API requests | `30` |
| `--max-tokens` | Max output tokens per chunk | `4096` |

### Output Options

| Flag | Description | Default |
|------|-------------|---------|
| `--output-dir` | Directory to save summaries | `summaries` |
| `--output-format` | `markdown`, `json`, or `html` | `markdown` |
| `--no-save` | Print to stdout only, don't save file | `False` |
| `--verbose`, `-v` | Detailed progress output | `False` |

### Config Options

| Flag | Description |
|------|-------------|
| `--config` | Path to config file (default: auto-detect) |
| `--no-config` | Ignore config file, use CLI args only |
| `--init-config` | Generate example `summarizer.yaml` and exit |

## Summary Styles

Use with `--prompt-type`. Defined in `summarizer/prompts.json`.

| Style | Purpose |
|-------|---------|
| `Questions and answers` | Q&A extraction from content |
| `Summarization` | Standard summary with title |
| `Distill Wisdom` | Ideas, quotes, and references extraction |
| `DNA Extractor` | Core truth distilled to 200 words max |
| `Fact Checker` | Claim verification with TRUE/FALSE/MISLEADING labels |
| `Tutorial` | Step-by-step instructions from content |
| `Research` | Deep analysis with broader context |
| `Reflections` | Philosophical extensions beyond what is said |
| `Mermaid Diagram` | Visual concept map in Mermaid.js syntax |
| `Essay Writing in Paul Graham Style` | 250-word essay in Paul Graham's style |
| `Only grammar correction with highlights` | Grammar cleanup with bold highlights |

## Examples

```bash
# Basic YouTube summary
python -m summarizer --source "https://youtube.com/watch?v=VIDEO_ID"

# Specific provider
python -m summarizer --source "URL" --provider gemini

# Extract key insights
python -m summarizer --source "URL" --prompt-type "Distill Wisdom"

# Fact-check with Perplexity
python -m summarizer \
  --source "URL" \
  --base-url "https://api.perplexity.ai" \
  --model "sonar-pro" \
  --prompt-type "Fact Checker"

# Mermaid diagram from a lecture
python -m summarizer --source "URL" --provider gemini --prompt-type "Mermaid Diagram"

# Local file
python -m summarizer --type "Local File" --source "./lecture.mp4" --provider groq

# Batch process
python -m summarizer --source "URL1" "URL2" "URL3" --provider gemini

# No config file (all explicit)
python -m summarizer \
  --source "URL" \
  --base-url "https://openrouter.ai/api/v1" \
  --model "google/gemini-2.0-flash-exp:free" \
  --api-key "sk-or-v1-YOUR_KEY" \
  --prompt-type "Tutorial" \
  --no-config
```

## Multi-Step Workflow

For comprehensive analysis, chain multiple styles on the same video:

1. `Summarization` — quick overview
2. `Distill Wisdom` — extract key insights
3. `Fact Checker` (with Perplexity) — verify claims
4. `Mermaid Diagram` — visual reference

## Warnings

- **Windows + `--no-save`**: Do NOT use `--no-save` on Windows — Unicode output crashes stdout. Always let the tool save to file, then read it.
- **Social media**: TikTok, Instagram, Twitter/X, and Reddit require a running Cobalt service.
- **Transcription fallback**: If YouTube captions are unavailable, the tool automatically falls back to audio download + Whisper transcription.
- **Cloud Whisper**: Requires a Groq API key (free tier available).
- Use `--verbose` for detailed progress and debugging.

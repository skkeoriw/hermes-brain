---
name: youtube-content
description: "YouTube video full pipeline: transcript extraction → Whisper fallback → 12 processing modes (summary, Mermaid diagram, fact check, Q&A, etc.)"
---

# YouTube Content Tool

## When to use

Use when the user shares a YouTube URL or video link and wants any of the following:
- Extract transcript / subtitles
- Summarize the video
- Generate a concept diagram (Mermaid or ASCII)
- Fact-check claims in the video
- Turn the video into a blog post, tutorial, Q&A, or Twitter thread
- Deep research based on video content

Supports any YouTube URL format: standard, short (youtu.be), Shorts, embed, live, or raw 11-character video ID.

---

## Step 1 — Extract transcript (auto-fallback)

### Primary: subtitle extraction (seconds)

```bash
SKILL_DIR=~/.hermes/hermes-agent/skills/media/youtube-content

# JSON output with metadata
python3 $SKILL_DIR/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID"

# Plain text
python3 $SKILL_DIR/scripts/fetch_transcript.py "URL" --text-only

# With timestamps
python3 $SKILL_DIR/scripts/fetch_transcript.py "URL" --timestamps

# Specific language (comma-separated fallback chain)
python3 $SKILL_DIR/scripts/fetch_transcript.py "URL" --language zh,zh-Hans,zh-Hant,en
```

### Fallback: Whisper transcription (when no subtitles exist)

Use the `summarize` project at `~/summarize/` with `--force-download`:

```bash
cd ~/summarize
source venv/bin/activate

# Cloud Whisper (fast, needs Groq/OpenAI/OpenRouter API key in .env)
python3 -m summarizer --source "URL" --transcription "Cloud Whisper"

# Local Whisper (no API key needed, slower, needs GPU for large models)
python3 -m summarizer --source "URL" --transcription "Local Whisper" --whisper-model base
# whisper-model options: tiny | base | small | medium | large
```

Cloud Whisper provider priority: Groq → OpenAI → OpenRouter (auto-detected from .env).

**Decision rule:**
1. Try subtitle extraction first — if successful, use it (seconds).
2. If subtitle extraction fails → use Cloud Whisper if API key available.
3. No API key → use Local Whisper.
4. Still fails → tell the user the video has no accessible audio/subtitle source.

---

## Step 2 — Process content (12 modes)

All modes use `~/summarize/` with the configured provider (see `~/summarize/summarizer.yaml`).

```bash
cd ~/summarize && source venv/bin/activate

python3 -m summarizer --source "URL" --prompt-type "MODE" --no-save
```

| Mode | Output | Best for |
|------|--------|----------|
| `Summarization` | Concise paragraph summary | Quick overview |
| `Distill Wisdom` | Insights + quotes + references | Learning/retention |
| `DNA Extractor` | ≤200-word core truth | Ultra-condensed takeaway |
| `Questions and answers` | Auto-generated Q&A pairs | Study / review |
| `Research` | Deep analysis + background context | Academic / investigative |
| `Fact Checker` | Each claim labeled TRUE / FALSE / UNVERIFIABLE | Verifying accuracy |
| `Tutorial` | Numbered step-by-step guide | How-to videos |
| `Reflections` | Extended thinking beyond the video | Philosophical / creative |
| `Essay Writing in Paul Graham Style` | Clean, conversational essay | Writing inspiration |
| `Only grammar correction with highlights` | Grammar-fixed text + bold highlights | Transcript cleanup |
| `Mermaid Diagram` | Mermaid.js concept map code | Architecture / relationships |
| `ASCII Diagram` | Spatial ASCII relationship map | Quick visual overview |

Default mode (if user doesn't specify): `Distill Wisdom`.

### Typical processing times (video already cached)

| Step | Time |
|------|------|
| Subtitle extraction | ~1 second |
| Cloud Whisper transcription | 1–3 minutes |
| Local Whisper (tiny/base) | 2–5 minutes |
| Any processing mode (single chunk) | 10–20 seconds |
| Long video multi-chunk processing | proportional to chunk count |

---

## Step 3 — Output options

```bash
# Save as markdown (default)
python3 -m summarizer --source "URL" --prompt-type "Mermaid Diagram" --output-format markdown

# JSON
python3 -m summarizer --source "URL" --prompt-type "Mermaid Diagram" --output-format json

# HTML
python3 -m summarizer --source "URL" --prompt-type "Mermaid Diagram" --output-format html

# Don't save to file, print to stdout only
python3 -m summarizer --source "URL" --prompt-type "Mermaid Diagram" --no-save
```

Output files are saved to `~/summarize/summaries/` by default.

---

## Transcript caching

The `summarize` project caches transcripts in memory per session. Running multiple `--prompt-type` modes on the same URL within one session reuses the cached transcript — no repeated downloads.

---

## Language support

- Subtitle extraction: 99+ languages via `--language` flag
- Whisper transcription: 99 languages, auto-detected or specify with `--language`
- Processing modes: outputs in the language of the transcript by default; ask the model explicitly for translation if needed

---

## Error handling

| Error | Action |
|-------|--------|
| No subtitles found | Auto-fallback to Whisper; if Whisper also unavailable, tell user |
| Private / unavailable video | Relay the error, ask user to verify URL |
| No matching language | Retry without `--language` to get any available transcript |
| API key missing for Cloud Whisper | Fall back to Local Whisper or notify user |
| `youtube-transcript-api` not installed | Run `pip install youtube-transcript-api --break-system-packages` |
| `summarize` venv missing | Run `cd ~/summarize && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt` |

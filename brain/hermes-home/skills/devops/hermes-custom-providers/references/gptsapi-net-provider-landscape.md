# gptsapi.net: Complete Model & Provider Landscape

## What is gptsapi.net?

A multi-format proxy gateway that accepts OpenAI, Claude, and Gemini API payloads under **one base_url** and **one API key**. It routes based on endpoint path and payload format, not by separate provider credentials.

**Key difference from direct APIs:** Single bearer token (`sk-...`) works for all three formats.

## Supported Models by Format (as of 2026-05-06)

### OpenAI Format
- **Base URL:** `https://api.gptsapi.net/v1`
- **Endpoint:** `/chat/completions`
- **Auth:** `Authorization: Bearer sk-...`

**Models tested & confirmed:**
- gpt-5.5 ✅
- gpt-5.4 ✅
- gpt-5.2 ✅
- gpt-5.1 ✅
- gpt-5-nano ✅
- gpt-5-mini ✅
- gpt-5.3-codex ✅
- gpt-5.2-codex ✅
- gpt-5.1-codex ✅
- gpt-5.1-codex-max ✅
- gpt-5.1-codex-mini ✅

**NOT tested (but in config):** `gpt-5` (timeouts observed), `gpt-4-turbo` (HTTP 503 "no available channel")

### Claude Format (via Anthropic-compatible endpoint)
- **Base URL:** `https://api.gptsapi.net/v1`
- **Endpoint:** `/messages`
- **Auth:** `Authorization: Bearer sk-...` (proxy forwards with different header semantics internally)

**Models tested & confirmed:**
- claude-haiku-4-5-20251001 ✅
- claude-sonnet-4-6 ✅
- claude-sonnet-4-6-thinking ✅

### Gemini Format (via Google-compatible endpoint)
- **Base URL:** `https://api.gptsapi.net/v1beta/models`
- **Endpoint:** `/{model}:generateContent`
- **Auth:** `x-goog-api-key: sk-...` (proxy accepts Bearer in Authorization header too)

**Models tested & confirmed:**
- gemini-3-flash-preview ✅
- gemini-2.5-flash ✅
- gemini-2.5-flash-lite ✅
- gemini-2.5-flash-nothinking ✅
- gemini-3.1-pro-preview ✅

## Hermes Config Template

```yaml
custom_providers:
# OpenAI family
- name: Gptsapi-OpenAI
  base_url: https://api.gptsapi.net/v1
  api_key: sk-Cbec6ad9324a0ae51b564b5bfd17a8405d083173fefmDd0t
  model: gpt-5.5

- name: Gptsapi-GPT-5-Mini
  base_url: https://api.gptsapi.net/v1
  api_key: sk-Cbec6ad9324a0ae51b564b5bfd17a8405d083173fefmDd0t
  model: gpt-5-mini

- name: Gptsapi-GPT-5-Nano
  base_url: https://api.gptsapi.net/v1
  api_key: sk-Cbec6ad9324a0ae51b564b5bfd17a8405d083173fefmDd0t
  model: gpt-5-nano

# Claude family
- name: Gptsapi-Claude-Sonnet-4-6
  base_url: https://api.gptsapi.net/v1
  api_key: sk-Cbec6ad9324a0ae51b564b5bfd17a8405d083173fefmDd0t
  model: claude-sonnet-4-6

- name: Gptsapi-Claude-Sonnet-4-6-Thinking
  base_url: https://api.gptsapi.net/v1
  api_key: sk-Cbec6ad9324a0ae51b564b5bfd17a8405d083173fefmDd0t
  model: claude-sonnet-4-6-thinking

# Gemini family
- name: Gptsapi-Gemini-2.5-Flash
  base_url: https://api.gptsapi.net/v1beta/models
  api_key: sk-Cbec6ad9324a0ae51b564b5bfd17a8405d083173fefmDd0t
  model: gemini-2.5-flash

- name: Gptsapi-Gemini-3.1-Pro
  base_url: https://api.gptsapi.net/v1beta/models
  api_key: sk-Cbec6ad9324a0ae51b564b5bfd17a8405d083173fefmDd0t
  model: gemini-3.1-pro-preview
```

## When to Use Each Model

**gpt-5-mini / gpt-5-nano**
- Low cost, fast iteration, webhook/cron automation
- Ideal for repetitive tasks (llm-wiki incremental updates, brain sync reporting)
- Use case: `wiki-ops` webhook, `hermes-brain-sync-tg` cron job

**gpt-5.5 / gpt-5.4**
- Balanced quality + speed for CLI queries
- Use when user interaction time matters

**claude-sonnet-4-6 / claude-sonnet-4-6-thinking**
- Extended reasoning, complex multi-step logic
- Higher latency; use for knowledge synthesis, not real-time tasks

**gemini-2.5-flash**
- Google's fast model; good for time-sensitive logic
- Fallback when OpenAI/Claude limits hit

## Real-World Usage Pattern

**Scenario:** User's OpenAI account hits HTTP 429 (quota exhausted).

**Old approach:** Wait for quota reset or upgrade plan.

**New approach:**
1. Switch webhook from default OpenAI to `Gptsapi-GPT-5-Mini` (gptsapi.net proxy).
2. Switch cron job from default to `Gptsapi-GPT-5-Nano`.
3. Both now run on stable, shared-quota proxy account.
4. Original OpenAI credentials untouched for other high-priority tasks.

This is what happened in the 2026-05-06 session: wiki-ops webhook and hermes-brain-sync-tg cron were both hitting 429; both migrated to gptsapi providers and confirmed working.

## Troubleshooting

### "model not found" HTTP 400
- Check exact model name against this reference.
- Proxy may not support that model version.
- Fallback: try a known-good model like `gpt-5.5` or `gemini-2.5-flash`.

### "No available channel for model X" HTTP 503
- Proxy has temporarily exhausted capacity for that model.
- Retry after a delay or switch to a different model.
- Example: `gpt-4-turbo` hit this; `gpt-5.5` works fine.

### HTTP 405 on the path
- **Almost always:** wrong subdomain.
- Check: is it `https://api.gptsapi.net/v1` or `https://gptsapi.net/v1`?
- Answer: MUST include `api.` subdomain.

### Bearer token accepted for Claude endpoints?
- **Yes.** Proxy internally translates to Anthropic's `x-api-key` format.
- Simplifies Hermes config — no special header logic needed.
- But do NOT use Anthropic's official API key; this proxy key is separate.

## Related Session Notes

- **2026-05-06:** Diagnosed HTTP 405 subdomain error, added 19 providers, switched webhook + cron to stable proxy models.
- **Key lesson:** Exact model names matter even when proxy claims format compatibility.

# Multi-Format Proxy Testing: gptsapi.net Case Study

## Problem
OpenAI API quota exhausted (HTTP 429). Need to switch to a multi-format proxy (gptsapi.net) that claims to support OpenAI, Claude, and Gemini APIs under a single API key.

Initial attempts to configure failed with HTTP 405 (Method Not Allowed). How to debug?

## Root Cause
The proxy exposes **different base URLs for different formats**:
- OpenAI format: `https://api.gptsapi.net/v1` (note: `api.` subdomain is **mandatory**)
- Claude format: `https://api.gptsapi.net/v1` (same, but endpoint is `/messages` not `/chat/completions`)
- Gemini format: `https://api.gptsapi.net/v1beta/models` (different versioned path)

Typo or missing subdomain → HTTP 405. Exact model name mismatch → HTTP 400.

## Debugging Walkthrough

### Step 1: Gather the curl command from proxy docs
The proxy documentation provided three example commands:
```bash
# OpenAI format
curl https://api.gptsapi.net/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.5","messages":[...]}'

# Claude format
curl https://api.gptsapi.net/v1/messages \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-haiku-4-5-20251001","messages":[...]}'

# Gemini format
curl https://api.gptsapi.net/v1beta/models/gemini-3-flash-preview:generateContent \
  -H "x-goog-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[...]}'
```

### Step 2: Test each format before committing config
Use Python to systematically test all three:

```python
import requests

api_key = "sk-..."

# Test 1: OpenAI format
resp = requests.post(
    "https://api.gptsapi.net/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json={"model": "gpt-5.5", "messages": [{"role": "user", "content": "test"}], "max_tokens": 10}
)
print(f"OpenAI: HTTP {resp.status_code}")

# Test 2: Claude format
resp = requests.post(
    "https://api.gptsapi.net/v1/messages",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json={"model": "claude-haiku-4-5-20251001", "messages": [{"role": "user", "content": "test"}], "max_tokens": 100}
)
print(f"Claude: HTTP {resp.status_code}")

# Test 3: Gemini format
resp = requests.post(
    "https://api.gptsapi.net/v1beta/models/gemini-3-flash-preview:generateContent",
    headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
    json={"contents": [{"role": "user", "parts": [{"text": "test"}]}]}
)
print(f"Gemini: HTTP {resp.status_code}")
```

**Output:**
```
OpenAI: HTTP 200 ✅
Claude: HTTP 200 ✅
Gemini: HTTP 200 ✅
```

### Step 3: Identify the "gotchas"

1. **Wrong subdomain was silently failing:**
   - ❌ `https://gptsapi.net/v1` → HTTP 405 (Nginx routing error)
   - ✅ `https://api.gptsapi.net/v1` → HTTP 200

2. **Model names are exact and version-specific:**
   - ❌ `claude-opus` → HTTP 400 "model not found"
   - ✅ `claude-haiku-4-5-20251001` → HTTP 200

3. **Claude can use Bearer token when proxied:**
   - Normally Anthropic uses `x-api-key` header
   - This proxy accepts `Authorization: Bearer` for Claude endpoints too
   - Makes config simpler (no special auth header logic needed)

4. **Gemini endpoint includes the model and action in the path:**
   - Endpoint: `/v1beta/models/{model}:generateContent`
   - Not just `/v1/models` like OpenAI patterns
   - This affects how Hermes constructs the full URL

### Step 4: Commit to config.yaml

Once all three are confirmed working, add them as separate providers:

```yaml
custom_providers:
- name: Gptsapi-OpenAI
  base_url: https://api.gptsapi.net/v1
  api_key: sk-...
  model: gpt-5.5

- name: Gptsapi-Claude
  base_url: https://api.gptsapi.net/v1
  api_key: sk-...
  model: claude-haiku-4-5-20251001

- name: Gptsapi-Gemini
  base_url: https://api.gptsapi.net/v1beta/models
  api_key: sk-...
  model: gemini-3-flash-preview
```

### Step 5: Use in webhooks and cron jobs

**Webhook:**
```json
{
  "my-webhook": {
    "provider": "Gptsapi-Claude",
    "model": "claude-haiku-4-5-20251001",
    ...
  }
}
```

**Cron:**
```bash
hermes cronjob update JOB_ID \
  --provider Gptsapi-OpenAI \
  --model gpt-5.5
```

## Key Learnings

1. **Test in isolation first.** Use curl/Python before relying on Hermes to load the config and report errors via logs.
2. **Subdomain and path matter.** A single character wrong (missing `api.`, wrong versioning) silently breaks routing.
3. **Model names are exact.** Check the proxy's latest supported models — version numbers matter.
4. **Different formats may coexist on the same proxy.** Separate providers for each model family for clarity, even if the base_url is similar.
5. **Proxy auth may differ from official APIs.** A proxy might accept Bearer tokens for Claude endpoints, even though Anthropic's official API uses `x-api-key`. Check the proxy's docs.

## Logs to Monitor

When things fail:
- Check `~/.hermes/logs/agent.log` for the exact HTTP status and response body
- Search for "model not found", "HTTP 405", "HTTP 401" — these are the top three red flags
- If the response is HTML (nginx error page), the URL or subdomain is wrong

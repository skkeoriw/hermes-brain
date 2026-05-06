---
name: hermes-custom-providers
description: Configure custom LLM providers in Hermes — OpenAI-compatible, Claude-compatible, Gemini-compatible, and multi-format proxies. Troubleshoot authentication and endpoint issues.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes-config, llm-providers, authentication, api-proxy, custom-providers]
    category: devops
    related_skills: [hermes-agent]
---

# Configuring Custom Hermes LLM Providers

Use this skill to configure non-standard (custom) LLM provider endpoints in `config.yaml` — allowing Hermes to use OpenAI-compatible proxies, Claude-compatible APIs, Gemini endpoints, or multi-format gateways.

## Trigger

- Need to add a provider beyond Hermes' built-in list (openai, anthropic, openrouter, etc.)
- Troubleshooting API authentication failures (HTTP 405, 401, invalid auth header)
- Setting up a proxy/gateway that supports multiple model families (e.g., gptsapi.net)
- Want to specify a custom base_url for an existing model family
- Webhook or cron job requires a specific provider or model not in the default config

## Configuration Shape

In `~/.hermes/config.yaml`:

```yaml
custom_providers:
- name: ProviderName
  base_url: https://api.example.com/v1
  api_key: your_api_key_here
  model: model-name-exact
```

## Multi-Format Proxy Pattern

Many proxy services (e.g., gptsapi.net) support **multiple API formats under a single endpoint**. Each format has different:
- **Base URL** (path)
- **Authentication header** (how to send the API key)
- **Endpoint** (the path fragment)
- **Model names** (exact string required)

### Format 1: OpenAI-Compatible

```yaml
- name: CustomOpenAI
  base_url: https://api.proxy.com/v1
  api_key: sk-...
  model: gpt-4-turbo
```

**Request:**
```
POST /v1/chat/completions
Authorization: Bearer sk-...
Content-Type: application/json

{
  "model": "gpt-4-turbo",
  "messages": [...],
  "max_tokens": 100
}
```

### Format 2: Claude-Compatible (Anthropic)

```yaml
- name: CustomClaude
  base_url: https://api.proxy.com/v1
  api_key: sk-...
  model: claude-3-sonnet-20240229
```

**Request:**
```
POST /v1/messages
Authorization: Bearer sk-...
anthropic-version: 2023-06-01
Content-Type: application/json

{
  "model": "claude-3-sonnet-20240229",
  "messages": [...],
  "max_tokens": 1000
}
```

### Format 3: Google Gemini-Compatible

```yaml
- name: CustomGemini
  base_url: https://api.proxy.com/v1beta/models
  api_key: sk-...
  model: gemini-2.5-flash
```

**Request:**
```
POST /v1beta/models/gemini-2.5-flash:generateContent
x-goog-api-key: sk-...
Content-Type: application/json

{
  "contents": [
    {
      "role": "user",
      "parts": [{"text": "..."}]
    }
  ]
}
```

## Applying to Webhooks & Cron Jobs

### Webhook
Edit `~/.hermes/webhook_subscriptions.json`:
```json
{
  "my-webhook": {
    "provider": "CustomOpenAI",
    "model": "gpt-4-turbo",
    ...
  }
}
```

### Cron Job
```bash
hermes cronjob update JOB_ID \
  --model gpt-4-turbo \
  --provider CustomOpenAI
```

## Pitfalls

### Pitfall 1: Wrong Subdomain or Path
❌ `https://gptsapi.net/v1` (HTTP 405)  
✅ `https://api.gptsapi.net/v1` (HTTP 200)

**Detection:** Test with curl before committing to config.yaml.
```bash
curl -X POST https://api.gptsapi.net/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.5","messages":[{"role":"user","content":"test"}],"max_tokens":10}'
```

### Pitfall 2: Wrong Model Name
❌ `claude-opus` (model not found)  
✅ `claude-haiku-4-5-20251001` (exact version required)

**Solution:** Query the proxy's docs or test models systematically (same format, different models).

### Pitfall 3: Mixed Auth Headers
Different formats require **different auth mechanisms**:
- **OpenAI & Claude (via proxy):** `Authorization: Bearer sk-...` (same header)
- **Gemini (via proxy):** `x-goog-api-key: sk-...` (different header + optional `anthropic-version`)

Hermes is smart enough to detect the format and apply the right header **if** base_url matches the documented format. If you mix (e.g., Claude model name with OpenAI endpoint), it will fail.

### Pitfall 4: Rate Limits & Usage Quotas
If Hermes reports HTTP 429 or "usage limit reached", don't assume a config error — check:
1. Provider's quota dashboard (did you hit a monthly limit?)
2. Whether the API key is still valid
3. Whether the account tier supports the model

Switch to a different provider temporarily to confirm the config is sound.

## Verification Steps

1. **Test auth privately first:**
   ```bash
   curl -X POST https://api.proxy.com/v1/chat/completions \
     -H "Authorization: Bearer YOUR_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"exact-model-name","messages":[{"role":"user","content":"hi"}],"max_tokens":5}' \
     | jq .
   ```
   Response should be `HTTP 200` with `choices[0].message.content` present.

2. **Check config.yaml syntax:**
   ```bash
   hermes config list  # or similar validation command
   ```

3. **Check Hermes sees the provider:**
   ```bash
   grep -A2 "name: ProviderName" ~/.hermes/config.yaml
   ```

4. **Test in Hermes directly** (ask a simple question, check logs):
   ```
   hermes config set model.provider CustomOpenAI
   hermes config set model.default gpt-4-turbo
   # then run an agent query and monitor ~/.hermes/logs/agent.log
   ```

---

## References

See `references/multi-format-proxy-testing.md` for a real-world example (gptsapi.net) and step-by-step debugging approach.

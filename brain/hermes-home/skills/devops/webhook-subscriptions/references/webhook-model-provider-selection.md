# Webhook Model & Provider Selection

## Key Discovery

**Webhooks are NOT bound to the machine's authenticated models or current gateway provider.** You can supply any API endpoint + key combo — it does not have to be a model the machine has previously used or authenticated with.

## Use Cases

1. **Escape rate limits**: When the default model hits quota (HTTP 429), route that webhook to a different provider without changing global config.
2. **Cost optimization**: Use cheaper/faster models for specific webhook routes (e.g., llm-wiki incremental builds → Qwen; PR reviews → GPT-4).
3. **Provider diversity**: Mix OpenAI, Anthropic, Qwen, xAI, local ollama, or custom endpoints in a single Hermes instance.
4. **Fallback strategy**: Pre-configure backup providers so if primary fails, webhook automatically tries secondary without manual intervention.

## How to Configure

### Option 1: Per-Webhook Route (Recommended)

Edit `~/.hermes/webhook_subscriptions.json` or use `hermes webhook subscribe`:

```bash
hermes webhook subscribe wiki-ops-qwen \
  --prompt "Your llm-wiki prompt..." \
  --events "push" \
  --skills "llm-wiki" \
  --model "qwen-turbo" \
  --provider "qwen" \
  --api-key "sk-your-qwen-key" \
  --base-url "https://dashscope.aliyuncs.com/compatible-mode/v1" \
  --deliver telegram \
  --deliver-chat-id "123456789"
```

This creates a route that ignores the machine's global model and always uses Qwen.

### Option 2: In JSON (Direct Edit)

Edit `~/.hermes/webhook_subscriptions.json`:

```json
{
  "wiki-ops-qwen": {
    "description": "LLM Wiki with Qwen model",
    "prompt": "你是...",
    "events": [],
    "secret": "123456",
    "skills": ["llm-wiki"],
    "model": "qwen-turbo",
    "provider": "qwen",
    "api_key": "sk-your-qwen-key",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "deliver": ["telegram"],
    "deliver_params": {"chat_id": "123456789"}
  }
}
```

After editing, the gateway hot-reloads on the next webhook request (mtime-gated).

### Option 3: Custom Provider in config.yaml (for Multiple Routes)

If you have several routes that need the same provider, define it once in `~/.hermes/config.yaml` and reference it:

```yaml
custom_providers:
  - name: qwen-provider
    base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    api_key: sk-your-qwen-key
    model: qwen-turbo
```

Then in `webhook_subscriptions.json`:
```json
{
  "wiki-ops": {
    "provider": "qwen-provider",
    "model": "qwen-turbo"
  }
}
```

## Common Providers & Endpoints

### Qwen (阿里通义千问)

```yaml
provider: qwen
base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
api_key: sk-... (from Alibaba DashScope console)
model: qwen-turbo | qwen-plus | qwen-long
```

**Cost:** ~0.008 CNY/1K tokens (turbo) — significantly cheaper than GPT-4o.

### OpenRouter

```yaml
provider: openrouter
base_url: https://openrouter.ai/api/v1
api_key: sk-or-... (from openrouter.ai)
model: anthropic/claude-haiku-4.5 | openai/gpt-4 | meta-llama/llama-3.1-405b-instruct
```

**Cost:** Variable by model; Claude Haiku ~0.8¢/1M tokens input.

### Local Ollama

```yaml
provider: ollama
base_url: http://localhost:11434/v1
api_key: "" (not needed for local)
model: llama3.1 | mistral | phi | neural-chat
```

**Cost:** Zero (runs locally).

### Anthropic Direct

```yaml
provider: anthropic
base_url: https://api.anthropic.com/v1
api_key: sk-ant-... (from console.anthropic.com)
model: claude-3-5-sonnet-20241022 | claude-3-opus-20250219
```

## Troubleshooting

### Webhook gets HTTP 429 (rate limited)

**Old behavior (before this discovery):** Stuck on that provider until quota resets or global config changes + gateway restart.

**New behavior:** Create a new route with a different provider:
```bash
hermes webhook subscribe wiki-ops-fallback \
  --prompt "..." \
  --model qwen-turbo \
  --provider qwen \
  --api-key "sk-..." \
  --base-url "https://dashscope.aliyuncs.com/compatible-mode/v1" \
  --deliver telegram
```

Then update your upstream service (GitHub webhook, CI/CD, etc.) to POST to the fallback URL instead.

### API key rejected or 401 errors

- Verify the key is correct and not expired (check console for the provider).
- Confirm the base URL matches what the provider expects (e.g., OpenAI vs OpenRouter use different endpoints).
- Test locally:
  ```bash
  curl -X POST "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer sk-..." \
    -d '{"model": "qwen-turbo", "messages": [{"role": "user", "content": "test"}], "max_tokens": 10}'
  ```

### Model name not found

Verify the model name is correct for that provider. Examples:
- OpenAI: `gpt-4-turbo`, `gpt-4o`, `gpt-4o-mini`
- Anthropic: `claude-3-5-sonnet-20241022`
- Qwen: `qwen-turbo`, `qwen-plus`, `qwen-long`
- Meta (via OpenRouter): `meta-llama/llama-3.1-405b-instruct`

## Cost Comparison (as of May 2026)

| Provider | Model | Input | Output | Use Case |
|----------|-------|-------|--------|----------|
| OpenAI | gpt-4o | $5/1M | $15/1M | High accuracy, general purpose |
| OpenAI | gpt-4o-mini | $0.15/1M | $0.60/1M | Fast, cheap, good for simple tasks |
| Anthropic | Claude 3.5 Sonnet | $3/1M | $15/1M | Good reasoning + code |
| Qwen | qwen-turbo | 0.008 CNY/1K (~$1.1/1M) | 0.02 CNY/1K (~$2.7/1M) | Cheap, Chinese-friendly |
| OpenRouter | Claude Haiku | $0.8/1M | $4/1M | Cheap + unified interface |
| Ollama | llama3.1 | Free (local) | Free (local) | Privacy, zero cost |

## Session Context

This reference was created after discovering a webhook delivery failed with HTTP 429 (OpenAI quota exhausted). The session revealed that webhooks do NOT require pre-authenticated models — any provider + key combo can be used on a per-route basis. This enables instant fallback without restarting the gateway or changing global config.

### Key Learnings for Future Sessions

1. **Webhooks are provider-agnostic.** Supply model + provider + api_key + base_url on a per-route basis.
2. **Hot reload works for dynamic routes.** Changing `webhook_subscriptions.json` takes effect on the next POST; no gateway restart needed.
3. **Cost-optimize by route.** Use fast/cheap models (Haiku, Qwen, local ollama) for high-frequency routes; reserve expensive models (GPT-4o, Claude Opus) for complex tasks.
4. **Immediate rate-limit fallback.** When a route hits 429, add a parallel route with a different provider instead of waiting for quota reset or manual reconfiguration.

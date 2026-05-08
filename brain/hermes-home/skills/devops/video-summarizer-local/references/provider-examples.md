# Provider Configuration Examples

## DeepSeek

**.env**
```
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
```

**summarizer.yaml**
```yaml
providers:
  deepseek:
    api_key: ${DEEPSEEK_API_KEY}
    base_url: https://api.deepseek.com/v1
    model: deepseek-chat
```

## OpenAI

**.env**
```
OPENAI_API_KEY=sk-your-openai-key-here
```

**summarizer.yaml**
```yaml
providers:
  openai:
    api_key: ${OPENAI_API_KEY}
    base_url: https://api.openai.com/v1
    model: gpt-4o-mini
```

## Anthropic (Claude)

**.env**
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**summarizer.yaml**
```yaml
providers:
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    base_url: https://api.anthropic.com/v1
    model: claude-3-haiku-20240307
```

## Ollama (local)

**.env**
```
# No API key needed for Ollama
```

**summarizer.yaml**
```yaml
providers:
  ollama:
    base_url: http://localhost:11434/v1
    model: llama3
```

## Azure OpenAI

**.env**
```
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment
```

**summarizer.yaml**
```yaml
providers:
  azure_openai:
    api_key: ${AZURE_OPENAI_API_KEY}
    base_url: ${AZURE_OPENAI_ENDPOINT}
    model: ${AZURE_OPENAI_DEPLOYMENT_NAME}
    api_version: 2024-02-01
```

## Default Provider

Set the default provider in summarizer.yaml:
```yaml
default_provider: deepseek  # or whichever you prefer
```

## Usage Notes

- Use `--provider <name>` to override the provider for a specific run.
- If using Ollama, ensure the service is running locally.
- For Azure OpenAI, you must provide `api_version` in the provider config.
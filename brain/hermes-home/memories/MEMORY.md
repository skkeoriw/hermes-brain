Git authentication on this machine is configured for GitHub user ChangfengHU using git credential store; the llm-wiki repository lives at /home/zhouhuijuan1987/wiki/llm-wiki-obsidian-blink with origin https://github.com/ChangfengHU/llm-wiki-obsidian-blink.git.
§
Brain sync: Hermes cron job runs hourly using gpt-5-nano (Gptsapi) to execute ~/hermes-brain/scripts/auto_sync.sh, syncing ~/.hermes→brain repo→GitHub and sending Telegram report. Systemd timer replaced with cron (2026-05-06).
§
gptsapi.net: 19 custom providers configured (key: sk-Cbec6ad9324a0ae51b564b5bfd17a8405d083173fefmDd0t). Critical: https://api.gptsapi.net/v1 (subdomain mandatory). OpenAI format (7 GPT + 3 Codex), Claude format (3 models), Gemini format at /v1beta/models (5 variants). Wiki-ops webhook → gpt-5-mini; brain-sync cron → gpt-5-nano (avoids OpenAI quota).
§
prompt-qa-unified-wiki: https://github.com/divanoo65/prompt-qa-unified-wiki, local /home/zhouhuijuan1987/wiki/prompt-qa-unified-wiki, PAT: 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 (divanoo65). Wiki uses TheSchema.md layout (raw/ + wiki/sources|entities|concepts|comparisons|overview|queries). llm-wiki webhook run IDs use gh-<run_id>-<attempt> prefix format.
§
User's knowledge graph philosophy: Strict "facts from raw only" initially seemed appealing to user, but after discussion agreed that L2 (inference) + L3 (question) layers with explicit confidence/reasoning labels are better than locked-down facts-only approach. This enables deeper insights while maintaining traceability. User now convinced that "releasing discovery with guardrails" > "constraining to raw-only".
§
User's quality diagnostic method: wiki/KG quality issues stem from (1) prompt/pipeline/schema design (main), (2) raw input quality (secondary), (3) model capability (tertiary). Prefers A/B testing to isolate root cause before fixing; prioritizes "define real problem first" over model change.
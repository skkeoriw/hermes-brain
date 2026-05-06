Git authentication on this machine is configured for GitHub user ChangfengHU using git credential store; the llm-wiki repository lives at /home/zhouhuijuan1987/wiki/llm-wiki-obsidian-blink with origin https://github.com/ChangfengHU/llm-wiki-obsidian-blink.git.
§
The private GitHub repository ChangfengHU/hermes-brain exists and is cloned at /home/zhouhuijuan1987/hermes-brain; it syncs selected Hermes persistent data from ~/.hermes into brain/hermes-home via scripts/hermes_brain_sync.py and shell wrappers.
§
gptsapi.net: 19 custom providers configured (key: sk-Cbec6ad9324a0ae51b564b5bfd17a8405d083173fefmDd0t). Critical: https://api.gptsapi.net/v1 (subdomain mandatory). OpenAI format (7 GPT + 3 Codex), Claude format (3 models), Gemini format at /v1beta/models (5 variants). Wiki-ops webhook → gpt-5-mini; brain-sync cron → gpt-5-nano (avoids OpenAI quota).
§
For llm-wiki webhook automation, user wants run IDs/delivery IDs to use a GitHub Actions-based prefix format (e.g., gh-<github_run_id>-<run_attempt>) so GitHub runs, webhook deliveries, Hermes sessions, and wiki logs can be correlated end-to-end.
§
User's knowledge graph philosophy: Strict "facts from raw only" initially seemed appealing to user, but after discussion agreed that L2 (inference) + L3 (question) layers with explicit confidence/reasoning labels are better than locked-down facts-only approach. This enables deeper insights while maintaining traceability. User now convinced that "releasing discovery with guardrails" > "constraining to raw-only".
§
User's quality diagnostic method: Quality problems in wiki/KG are caused by "three layers" (in priority order): 1) prompt/pipeline/schema design (main), 2) raw input quality (secondary), 3) model capability (tertiary). User wants A/B testing approach to pinpoint root cause before fixing. For this user, "define the real problem first" > "change model".
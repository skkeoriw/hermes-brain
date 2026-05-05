# Full Data Map

Repo path `brain/hermes-home/` maps directly to local `~/.hermes/`.

## Synchronized by default

- `config.yaml`
- `.env`
- `auth.json`
- `memories/`
- `skills/`
- `sessions/`
- `state.db`
- `webhook_subscriptions.json`
- `gateway_state.json`
- `channel_directory.json`
- `pairing/`
- `profiles/`
- `cron`/gateway/API/webhook persistent JSON/YAML files
- custom prompts and scripts stored directly under `~/.hermes`

## Excluded by default

- `hermes-agent/` because Hermes should be installed per machine
- `logs/` because logs are runtime noise
- `cache/`, `audio_cache/`
- `__pycache__/`, `*.pyc`
- `*.lock`
- `*.pid`
- `*.log`
- `*-wal`, `*-shm`
- `.update_check`

## Notes

This project intentionally supports plaintext test credential sync. Do not use the repository as public documentation.

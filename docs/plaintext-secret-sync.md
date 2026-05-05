# Plaintext Secret Sync

This repository intentionally supports plaintext secret sync for testing.

Files that may contain secrets:

- `brain/hermes-home/.env`
- `brain/hermes-home/auth.json`
- `brain/hermes-home/config.yaml`
- `brain/hermes-home/webhook_subscriptions.json`
- `brain/hermes-home/pairing/`
- `brain/hermes-home/gateway_state.json`
- `brain/hermes-home/channel_directory.json`

Rules:

- Keep the GitHub repository private.
- Do not add collaborators unless they may see all credentials.
- Do not make the repo public.
- If public exposure happens, rotate every token/key.

To switch to encrypted mode later, add `scripts/encrypt_secrets.sh` and move sensitive files out of plaintext Git history after rotating credentials.

# Security notes

This repo is intentionally configured for plaintext private-repo brain sync during testing.

It may contain:

- API keys and provider credentials
- OAuth tokens and auth pools
- webhook secrets
- GitHub tokens
- gateway pairing/channel state
- personal memories/session transcripts

Rules:

1. Keep the GitHub repo private.
2. Do not add untrusted collaborators.
3. Do not fork public.
4. If exposed, rotate/revoke all credentials.
5. Remember that Git history preserves deleted secrets.
6. For production, migrate to encrypted secret sync or keep `.env`/`auth.json` machine-local.

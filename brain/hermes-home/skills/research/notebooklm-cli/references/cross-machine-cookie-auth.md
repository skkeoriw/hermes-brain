# Cross-machine cookie auth troubleshooting (Mac -> Linux)

Observed workflow that worked:
- `shared-storage.json` validated structurally (cookies present, SID present) but failed token fetch.
- Copying session file into active profile path and re-authenticating eventually produced `Token fetch: pass`.

Commands used:
- Validate auth: `notebooklm auth check --test`
- Set profile storage explicitly:
  - `mkdir -p ~/.notebooklm/profiles/default`
  - `cp /path/to/shared-storage.json ~/.notebooklm/profiles/default/storage_state.json`
  - `chmod 600 ~/.notebooklm/profiles/default/storage_state.json`

Failure signatures:
- `Storage file not found: ~/.notebooklm/profiles/default/storage_state.json`
- `Token fetch failed: Authentication expired or invalid. Redirected to accounts.google.com...`
- `login --browser-cookies <browser>` => `can't find cookies file` (rookiepy path detection miss)

Interpretation:
- Static cookie presence checks are necessary but not sufficient.
- Final gate is token fetch.
- VNC/browser environments often use non-standard profile locations, so browser-cookie auto-read may fail.

Security note:
- Treat Netscape cookie dumps and storage_state files as secrets (session bearer-equivalent). Rotate sessions if exposed.
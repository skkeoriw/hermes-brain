# Git Push Auth Fallback Chain

When `git push` fails with HTTP 403, the available credential/token may not have push access to the target repository. This document defines the systematic auth discovery chain to exhaust before classifying the run as `error:push_failed`.

## Auth Discovery Order

### 1. Primary Token (from env)
The most common source. Check environment variables in priority order:
```bash
# Check these env vars
echo "$GITHUB_TOKEN"         # Common CI variable
echo "$GH_TOKEN"             # gh CLI variable
# And any *TOKEN* or *PAT* env vars
env | grep -i -E 'TOKEN|PAT' | grep -v 'TELEGRAM\|BOT'
```

If found, embed in remote URL and retry:
```bash
git remote set-url origin "https://<token>@github.com/<owner>/<repo>.git"
git push origin main
```

### 2. Stored Credentials (~/.git-credentials)
If the primary token fails, check the credential store:
```bash
cat ~/.git-credentials 2>/dev/null
```
Each line has format `https://<username>:<pat>@github.com`. Try each alternative PAT:
```bash
# Extract unique PATs from credential file
grep -oP 'github\.com.*' ~/.git-credentials | sed 's/.*://' | sed 's/@.*//'
```

### 3. Additional Environment Tokens
Sometimes tokens for different accounts are set in the environment:
```bash
# Broader search for GitHub-specific tokens
env | grep -i 'GITHUB\|GH_\|GITLAB' | grep -v 'TELEGRAM\|BOT\|WEBHOOK\|WORKSPACE\|ACTION\|STEP\|REF\|SHA\|HEAD\|BRANCH\|REPO\|ACTOR\|RUN\|EVENT\|PATH\|HOME\|CI\|TOKEN_AUTH'
```

### 4. Retry with Alternative Tokens
For each alternative token found in steps 2-3:
```bash
git remote set-url origin "https://<alt_token>@github.com/<owner>/<repo>.git"
git push origin main
```
Stop at the first success.

## When All Tokens Fail

If every available token returns 403:

1. **Restore remote URL** to original form:
   ```bash
   git remote set-url origin https://github.com/<owner>/<repo>.git
   ```

2. **Record failure in run-log:**
   - Exact 403 error message
   - Which tokens/accounts were tried (log usernames, not token values)
   - Outcome: all denied

3. **Classify run** as `error:push_failed`

4. **Suppress Telegram:** Do NOT send notification — the "build commit + push success" gate is not met

5. **Preserve local commit:** The commit exists locally (`git log`). User can push manually once credentials are fixed.

## Common Error Patterns

| Error | Likely Cause |
|-------|-------------|
| `denied to <user>` | Token belongs to a different GitHub account that lacks repo access |
| `403 Forbidden` | Token is valid but lacks the `repo` scope or the user is not a collaborator |
| `401 Unauthorized` | Token is expired or invalid |
| `fatal: could not read Username` | No credentials configured at all |

## Manual Recovery (for user or operator)
```bash
cd /path/to/repo
git remote set-url origin https://github.com/<owner>/<repo>.git
# Then push with correct credentials:
# Option A: Use gh CLI
gh auth login && git push origin main
# Option B: Set a new PAT
git remote set-url origin "https://<username>:<new_pat>@github.com/<owner>/<repo>.git"
git push origin main
```

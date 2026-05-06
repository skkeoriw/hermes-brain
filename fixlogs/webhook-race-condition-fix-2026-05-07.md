# Webhook Race Condition Fix - 2026-05-07

## Problem
Git stash pop failures in concurrent webhook execution:
```
error: could not restore untracked files from stash
logs/webhook-runs/gh-25447048029-1.md already exists, no checkout
```

Root cause: Multiple webhooks create untracked log files between `git stash push` and `git stash pop`.

## Solution - Dual-Layer Protection

### Layer 1: Root Cause (Persistent)
- **Change**: Add `logs/webhook-runs/*.md` to `.gitignore`
- **Effect**: Log files never included in git stash
- **File**: `/home/zhouhuijuan1987/wiki/llm-wiki-obsidian-blink/.gitignore`
- **Commit**: 1474dc2

### Layer 2: Safety Mechanism (Temporal)
- **Change**: Add GitHub Actions concurrency control to workflow
- **Effect**: Multiple webhooks run sequentially, not concurrently
- **File**: `.github/workflows/hermes-webhook-on-push.yml`
- **Key addition**:
  ```yaml
  concurrency:
    group: hermes-webhook-${{ github.repository }}
    cancel-in-progress: false
  ```

## Implementation Details

### Workflow Enhancements
1. **Concurrency lock** (lines 23-25): Sequential execution
2. **Standardized run_id** (line 45): `gh-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}`
3. **Complete payload** (lines 47-62): Better tracing and correlation
4. **Error handling** (lines 67-96): Config validation + HTTP status checks

## Robustness Improvements
| Scenario | Before | After |
|----------|--------|-------|
| Single webhook | ✓ | ✓ |
| 2+ concurrent | ✗ | ✓ |
| Rapid sequential | ✗ | ✓ |
| Log growth | ✗ | ✓ |

## Deployment Status
✅ Complete and verified
✅ Zero downtime
✅ Fully backward compatible
✅ Ready for production

## Reference
- Skill: webhook-subscriptions
- Reference doc: webhook-subscriptions/references/git-stash-race-conditions-in-concurrent-webhooks.md

---
name: llm-wiki-multiwiki-e2e-gate
description: "Bootstrap and validate multi-wiki factory flow: push->GitHub Action->Hermes webhook->incremental compile->push-back->next run skip when raw unchanged."
version: 1.0.0
author: Hermes Agent
---

# Trigger
Use when creating a new wiki repo that must run fully automated webhook compilation with loop prevention.

# Steps
1) Create isolated wiki
- Separate repo, local path, webhook route, and token.
- Keep rule priority: webhook prompt > TheSchema.md > SCHEMA.md > llm-wiki defaults.

2) Workflow baseline
- Trigger on push(main) + optional workflow_dispatch.
- Build payload including run_id/delivery_id: gh-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}.
- POST to Hermes webhook URL with X-Gitlab-Token.
- Copy the validated workflow skeleton from `templates/hermes-webhook-on-push.yml` and only edit identifiers (repo/wiki_id/route/token var names).

3) Raw-change gate (loop prevention)
- Do NOT gate in an ad-hoc tmp git repo. Use checkout + full history in the job itself:
  - actions/checkout@v4 with fetch-depth: 0
  - BEFORE='${{ github.event.before }}', AFTER='${{ github.sha }}'
  - if workflow_dispatch => should_run=true
  - if BEFORE is empty/zero sha => should_run=true (fail-open)
  - if BEFORE commit missing locally => should_run=true with reason=before_not_found_fail_open
  - else compute `git diff --name-only "$BEFORE" "$AFTER" -- 'raw/**/*.md'`
- Use changed_count integer instead of grep-only checks; set reason=raw_changed or reason=no_raw_change.
- Ensure webhook step runs only when should_run=true; otherwise stop step prints `Skip webhook: no_raw_change` and exits 0.

4) Variables/secrets fallback
- Prefer vars for initial bootstrap when secrets API unavailable:
  - HERMES_WEBHOOK_URL
  - HERMES_WEBHOOK_TOKEN
- Env expression pattern:
  - vars.X != '' && vars.X || secrets.X

4.1) Telegram isolation + unified template (recommended)
- For multi-wiki deployments, avoid shared default delivery channels; isolate each wiki's Telegram sender.
- Preferred: direct Telegram Bot API send with wiki-specific bot token (env var), not shared implicit route delivery.
- Enforce a single notification template for all runs:
  [QA-WIKI-RUN]
  action=<action>
  run_id=<run_id>
  raw_changed_count=<n>
  raw_changed_files=<comma_list>
  wiki_updates=<yes|no>
  created_files=<comma_list>
  updated_files=<comma_list>
  commit=<hash|none>
  push=<success|failed|none>
  run_log=<absolute_path>
  errors=<none|summary>
- Gate remains strict: no_raw_change => no Telegram message.

5) End-to-end validation
- Evidence must include:
  a) push with raw change triggers action and webhook accepted (2xx)
  b) Hermes run compiles and pushes derived artifacts
  c) next push (no raw change) skips webhook with reason=no_raw_change
  d) for notification-enabled runs, verify Telegram delivery with explicit proof (`chat_id`, `message_id`) instead of inferring from webhook success.
  e) if a run unexpectedly skips as `no_raw_change`, patch route prompt/gate rules immediately and re-run with a tiny raw change to re-validate.

6) Content quality standard (MANDATORY)
- Use article-style raw corpus under `raw/articles/` (avoid short QA stubs as primary corpus).
- Baseline for production wiki quality:
  - At least 10 domain articles for initial bootstrap.
  - Each article must be >=500 Chinese characters (or equivalent depth in other languages).
  - Each article must include: problem framing, methodology/architecture, failure modes or counterexample, and practical checklist.
  - Each article must contribute at least 2 reusable concepts or entities to wiki graph pages.
- Reject low-information content:
  - No "few-sentence" placeholder pages.
  - No repetitive template paraphrases across files.
  - No claim without traceable source/provenance marker.

7) Schema quality enforcement
- In canonical schema (prefer `TheSchema.md` if repo defines it), require:
  - Frontmatter completeness and consistent taxonomy.
  - Confidence labels for inferential claims.
  - Explicit edge typing for KG relations.
- Pre-commit/compile gate should fail when article depth or schema constraints are not met.

8) Graph quality acceptance
- Incremental build must produce meaningful graph deltas (not empty churn):
  - entity/concept/comparison pages should increase or be substantively updated when new raw articles are added.
  - report quantitative deltas (counts + representative names/edges).
- If raw changed but graph remains near-empty, classify run as quality-failed and require remediation before "success" reporting.

# Diagnostics matrix
- 403 on dispatch: token lacks permission for that repo/action.
- 422 on dispatch: GitHub says workflow has no workflow_dispatch trigger (file recognition/parsing mismatch).
- run completed failure in <1s and no jobs: likely workflow parse/config issue or platform-side workflow ingestion problem.
- Raw changed but run says `skipped:no_raw_changes`: treat as gate regression. Verify diff command in run-log; it must use payload `before`/`sha` against `raw/**/*.md` and not shortcut to "pull up-to-date => no changes".
- TG not received while build/push succeeded: distinguish transport vs policy.
  - Transport check: send a direct `send_message` probe to target chat_id and confirm message_id success.
  - Policy check: inspect run-log gate outcome; if skipped/no-op, no Telegram is expected by contract.

# Pitfalls
- YAML heredoc closing marker in workflow `run: |` blocks must keep indentation aligned (e.g., `JSON` terminator); misalignment causes `Invalid workflow file ... yaml syntax`.
- Don’t rely only on manual dispatch; push trigger is primary production path.
- `workflow_dispatch` errors are diagnostic:
  - 422: workflow trigger recognition issue (not token auth failure)
  - 403: token lacks permission for that repo/action
- Don’t notify Telegram on no-op runs.
- Don’t share webhook route/token across multiple wikis.
- Don’t share a single Telegram delivery channel/bot across multiple wikis; enforce per-wiki bot/token isolation to prevent cross-wiki confusion.
- For push-trigger incremental runs, never infer `no_raw_change` from `pull up-to-date`. Raw-change must be decided from `before..sha` diff (fallback only when before missing/invalid).
- Avoid non-quantitative Telegram summaries (“updated successfully”). Always include counts + names + representative edges, or mark metrics as `unknown` with reason.

# Verification checklist
- webhook_subscriptions route exists and points to correct local wiki path
- gateway restarted after webhook config change
- repository has HERMES_WEBHOOK_URL/TOKEN configured (vars or secrets)
- action logs show gate_reason and skip behavior as expected
- control-plane consistency check passes across three layers:
  1) GitHub workflow gate (push/manual trigger + before..sha raw diff)
  2) Hermes webhook route prompt (stage routing + commit/push/notify policy)
  3) Repo schema contract (TheSchema.md/SCHEMA.md run rules)

# Control-plane anti-drift (important)
- Treat the automation as layered control, not a single controller.
- Primary gate should live in GitHub workflow; webhook prompt should validate/consume gate outcome and only do fail-open fallback when context is missing.
- Avoid duplicated but different raw-change logic in workflow and webhook prompt; that causes split-brain outcomes (workflow says run, prompt says skip, or vice versa).
- Prefer script-backed stage execution (scripts/) over long imperative prompt blocks for Stage1/Stage2; keep prompt orchestration thin and deterministic.
- Normalize run-log schema for all routes: action, gate_reason, raw_changed_count, raw_changed_files, wiki_updates, created_files, updated_files, commit, push, errors.

# Packaged assets
- Template workflow: `templates/hermes-webhook-on-push.yml` (known-good gate + webhook payload + vars/secrets fallback).
- Validation notes: `references/e2e-validation-notes.md` (failure signatures, fixes, and proof checklist).
- Telegram isolation/template: `references/telegram-qa-wiki-template.md` (per-wiki bot isolation, send gate, quantitative message schema).
- Incident playbook: `references/no-raw-change-false-skip-and-tg-proof.md` (raw-changed-but-skipped diagnosis + Telegram proof checklist).
- Control-plane notes: `references/control-plane-layering-and-anti-drift.md` (workflow gate vs webhook prompt vs schema layering, anti-drift policy).
- Article quality rubric: `references/ai-agent-article-quality-rubric.md` (>=500中文、结构完整、反模板化、图谱联动验收)。

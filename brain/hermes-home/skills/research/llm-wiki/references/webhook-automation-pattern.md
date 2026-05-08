# Webhook Automation Pattern for llm-wiki

This document outlines the specific pattern for handling GitHub webhook automation for the llm-wiki skill, based on the requirements and pitfalls encountered in production use.

## Precedence Order (Critical)
When conflicts exist between different sources of guidance, apply this strict order:
1. **Webhook prompt** (highest priority - the specific instructions in the webhook payload)
2. **Repository canonical schema** (TheSchema.md - the source of truth in the repo)
3. **Bridge SCHEMA.md** (compatibility document for generic tooling)
4. **Generic llm-wiki skill defaults** (lowest priority)

Never let generic skill defaults override repository-specific contracts.

## Standard Workflow for All Webhook Runs

### 1. Protective Stash & Sync Sequence
Before any processing, ALWAYS execute:
```bash
git stash push -u -m "webhook-auto-stash-<run_id>"
git fetch origin main && git checkout main && git pull --ff-only origin main
git stash pop  # Handle conflicts appropriately
```

**Conflict Handling:**
- If `stash pop` produces merge/content conflicts: Log details and abort immediately
- If `stash pop` only conflicts on the current run-log file ("already exists, no checkout"): Treat as non-blocking warning, log, and continue
- If `git pull --ff-only` fails with divergence: Classify as `aborted:sync_ff_only_failed`, log, and abort

### 2. Run-Log Creation Timing
**Critical:** Complete the stash/fetch/pull/pop sequence BEFORE creating or appending the run-log file to avoid restore conflicts.

### 3. Incremental Build Specifics
#### Change Detection
- Prefer payload-provided `before..sha` for `git diff --name-only`
- Fallback to `HEAD~1..HEAD` if `before` is missing or malformed
- **Hard-filter** to `raw/**/*.md` only
- If zero changes: Record `skipped:no_raw_changes`, stop without wiki writes/commit/push, and do NOT send Telegram

#### Processing Scope
When raw changes exist:
- Only update affected wiki pages (sources, entities, concepts, etc.)
- Update `index.md` and `log.md`
- Rebuild relationship overviews as needed

### 4. Git Operations Discipline
#### Commit Strategy
- Default message: `git commit -m "chore: update llm wiki graph"`
- **If repo contains unrelated untracked files:** Stage ONLY files touched by this run to avoid bundling stale artifacts
- **Verification guard:** Immediately after commit, run `git show --name-only --oneline -n 1 HEAD` and confirm expected files are present

#### Push Requirements
- **Push discipline (critical):** After ANY local write operation, you MUST git add + commit + push in the SAME TURN
- Never leave changes local - users find it extremely frustrating
- Sequence must be atomic: write → git add -A → git commit → git push

### 5. Run-Log Requirements
Every execution MUST create/append a detailed run log at:
`logs/webhook-runs/gh-<run_id>-<attempt>.md` (or use provided run_id/delivery_id/UTC timestamp)

**Required content:**
- Start time (ISO 8601 UTC)
- Complete payload
- Git sync commands and results (stash, fetch, checkout, pull, stash pop)
- List of scanned/read key files (SCHEMA.md, TheSchema.md, index.md, log.md, changed raw files)
- Created/updated/deleted files lists
- Git status after changes
- Commit hash and push result
- Errors or failure stack traces
- End time (ISO 8601 UTC)

For `full_build`, additionally record:
- Number of Markdown files scanned
- Structure initialization/repair details
- Index and graph page generation/update details

## Telegram Notification Rules
- **Only send** when: `incremental_build` AND raw/**/*.md changed AND actual graph/wiki updates occurred (commit + push success)
- **Never send** when: `skipped:no_raw_changes`, aborted, or error states
- **Delivery method:** Telegram Bot API direct-send (not via Hermes webhook route)
- **Required summary metrics:**
  - New entity count + names
  - New/changed raw source count + file list
  - Relation changes grouped by type (with ≥3 sample edges)
  - Affected concept-page list
  - Commit hash
  - Run-log file path

## Session-Specific Learnings (May 8, 2026)
- **Source page creation:** When creating a new source page from raw content, include comprehensive metadata (stars, language, update time) and structured sections (项目信息, 核心功能, 适用场景, 价值评估, 与同类项目对比)
- **Entity page mirroring:** Entity pages should mirror source page content but focus on the entity's role in the knowledge graph, using the same core information but potentially different emphasis
## Session-Specific Learnings (May 8, 2026)
- **Source page creation:** When creating a new source page from raw content, include comprehensive metadata (stars, language, update time) and structured sections (项目信息, 核心功能, 适用场景, 价值评估, 与同类项目对比)
- **Entity page mirroring:** Entity pages should mirror source page content but focus on the entity's role in the knowledge graph, using the same core information but potentially different emphasis
- **Relationship mapping:** For new entity additions, create explicit relationships: \n  - Source file → Source page (documentation)\n  - Source page → Entity page (description)\n  - Entity page → Related concepts (based on content analysis)
- **Index updates:** When adding new source and entity entries, maintain alphabetical ordering within sections and update counters accurately
- **Log consistency:** Both wiki/log.md and webhook run logs should be updated - the former for wiki operations history, the latter for detailed automation audit
- **Overview updates:** Relationship overview pages (like wiki/overview/知识图谱关系.md) should be updated to reflect new entity-concept connections
- **Raw file frontmatter:** When processing raw file changes, always add/update frontmatter with source_url, ingested date, and SHA256 hash for drift detection on future ingests
- **Entity page updates:** When updating existing entity pages, preserve the original creation date, update the modified date, and incrementally improve content based on new source information (e.g., correcting star counts, updating feature descriptions)
- **Cross-linking discipline:** Every new or updated wiki page must link to at least 2 other wiki pages via [[wikilinks]] and verify reciprocal links exist
- **Filename encoding handling:** When processing git diff output for raw file changes, properly handle escaped unicode sequences in filenames. The output may appear as quoted strings with escaped unicode (e.g., \\\"raw/Self-RAG-\\\\\\\\350\\\\\\\\207\\\\\\\\252...md\\\") that requires decoding to get the actual filename.
- **Change detection robustness:** When payload-provided `before` SHA is missing, invalid, or malformed, immediately fallback to `git diff --name-only HEAD~1 HEAD -- 'raw/**/*.md'` rather than assuming no changes based on \"up-to-date\" status.
- **Git operations verification:** After commit, always run verification guard: `git show --name-only --oneline -n 1 HEAD` to confirm expected files are actually in the commit before considering the operation successful.
- **Telegram notification discipline:** Use the independent Bot Token from environment variable `QA_WIKI_TELEGRAM_BOT_TOKEN` for direct Telegram Bot API sends (not via Hermes webhook route), targeting fixed chat_id `6938920500`.
- **Working directory state management:** At the start of webhook runs, expect modified files from previous runs (especially logs and entity pages that may have been edited manually). Execute the protective stash sequence BEFORE assessing raw changes to avoid false positives. After stash/pop, reassess the clean state for accurate change detection.
- **Untracked file accumulation:** Webhook runs will accumulate untracked log files over time. These should be left alone unless they interfere with operations (like run-log filename conflicts). The stash/pop process handles them safely.
- **Relationship maintenance:** When adding new entities that relate to existing concepts (like Agent, LLM, RAG, etc.), verify those concept pages exist and create bidirectional links. In this run, hello-agents was linked to existing concept pages for Agent, LLM, RAG, MCP, Agentic-RL, and GRPO.
- **Source/entity pairing:** For each new raw source processed, create both a source summary page (in wiki/sources/) and an entity page (in wiki/entities/) to capture both the source metadata and the entity's role in the knowledge graph.
- **Working directory state management:** At the start of webhook runs, expect modified files from previous runs (especially logs and entity pages that may have been edited manually). Execute the protective stash sequence BEFORE assessing raw changes to avoid false positives. After stash/pop, reassess the clean state for accurate change detection.
- **Untracked file accumulation:** Webhook runs will accumulate untracked log files over time. These should be left alone unless they interfere with operations (like run-log filename conflicts). The stash/pop process handles them safely.
- **Relationship maintenance:** When adding new entities that relate to existing concepts (like Agent, LLM, RAG, etc.), verify those concept pages exist and create bidirectional links. In this run, hello-agents was linked to existing concept pages for Agent, LLM, RAG, MCP, Agentic-RL, and GRPO.
- **Source/entity pairing:** For each new raw source processed, create both a source summary page (in wiki/sources/) and an entity page (in wiki/entities/) to capture both the source metadata and the entity's role in the knowledge graph.
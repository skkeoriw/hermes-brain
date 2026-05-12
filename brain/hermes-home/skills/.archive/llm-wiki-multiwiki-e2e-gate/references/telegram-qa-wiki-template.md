# Telegram isolation + quantitative template (qa-wiki)

Use this when running multi-wiki automation where each wiki must send notifications independently.

## Isolation rules
- One wiki = one Telegram bot token (env var per wiki).
- Do not rely on shared/default delivery channel for multi-wiki production.
- Preferred send path: direct Telegram Bot API `sendMessage` with the wiki-specific token.

## Required notification gate
Send Telegram only when all are true:
1) `action=incremental_build`
2) `raw/**/*.md` changed (`changed_raw_count > 0`)
3) wiki/KG artifacts actually changed
4) commit + push succeeded

If `no_raw_change`, set `telegram=skipped:no_raw_change` in run-log and do not send.

## Standard message template
```text
[QA-WIKI-RUN]
action=<action>
run_id=<run_id>
raw_changed_count=<n>
raw_changed_files=<comma_list>
wiki_updates=<yes|no>
kg_delta_entities=<n|unknown>
kg_delta_concepts=<n|unknown>
kg_delta_relations=<n|unknown>
relation_types_delta=<type1:+n,type2:+m|unknown>
relation_samples=<A--rel-->B;...>
created_files=<comma_list>
updated_files=<comma_list>
commit=<hash|none>
push=<success|failed|none>
run_log=<absolute_path>
errors=<none|summary>
```

## Verification checklist
- Confirm `before` and `sha` in payload and use them for diff first.
- Verify run-log records exact raw changed files and counts.
- Verify notification content is quantitative (not generic prose).
- Verify message goes through the wiki-specific bot (not shared channel).

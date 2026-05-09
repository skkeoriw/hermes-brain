prompt-qa-unified-wiki: https://github.com/divanoo65/prompt-qa-unified-wiki, local /home/zhouhuijuan1987/wiki/prompt-qa-unified-wiki, PAT: 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 (divanoo65). Wiki uses TheSchema.md layout (raw/ + wiki/sources|entities|concepts|comparisons|overview|queries). llm-wiki webhook run IDs use gh-<run_id>-<attempt> prefix format.
§
User's knowledge graph philosophy: Strict "facts from raw only" initially seemed appealing to user, but after discussion agreed that L2 (inference) + L3 (question) layers with explicit confidence/reasoning labels are better than locked-down facts-only approach. This enables deeper insights while maintaining traceability. User now convinced that "releasing discovery with guardrails" > "constraining to raw-only".
§
User's quality diagnostic method: wiki/KG quality issues stem from (1) prompt/pipeline/schema design (main), (2) raw input quality (secondary), (3) model capability (tertiary). Prefers A/B testing to isolate root cause before fixing; prioritizes "define real problem first" over model change.
§
Updated sop-notebooklm-research skill to handle stash pop conflicts by resetting to origin/main and dropping stash changes when conflicts occur during protected sync step.
§
Updated sop-notebooklm-research skill to reflect actual notebooklm_processor.py output structure: JSON includes generated_files list with type and path; copy files preserving original filenames.
§
Updated sop-notebooklm-research skill to include timing logs, duration calculation, and required log fields (start_time, end_time, duration_seconds, videos_processed). Also clarified the renaming rule for generated files based on report title slug.
§
Successfully executed SOP Stage B for youtube-video-research-wiki: processed 3 YouTube links, generated reports and mindmaps, committed and pushed changes. Updated the skill to include timing logs and enhanced log requirements.
§
Reviewed and updated sop-notebooklm-research skill based on execution experience: enhanced timing/logging requirements, clarified file renaming rules based on report title slug, and improved overall procedure clarity.
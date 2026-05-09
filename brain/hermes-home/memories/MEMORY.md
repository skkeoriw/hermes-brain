【重要约束】禁止使用 OpenRouter 付费模型。若必须用 OpenRouter，只能选免费模型（模型名带 :free 后缀）。
§
SOP Stage C 经验 2026-05-09: 单次 API 调用处理多份报告易截断。改用 v2 分批处理（每报告一次 API 调用）。API 优先级：export DEEPSEEK_API_KEY 且 unset DASHSCOPE_API_KEY 避免误用 qwen-turbo（max_tokens 仅 8192）。即使1份报告也可能截断JSON，需从response.txt恢复。LLM 输出文件名有时截断（缺末尾字符），push 后必须做死链检查。
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
2026-05-09: 修复 sop-notebooklm-research skill 的 Pitfall #2。原版错误引用 `rm -f` 清理旧文件，与 Step 7"不要删除"矛盾。修正为：遗留旧文件被捎带提交是预期行为（装饰性 bloat），Stage C 通过 diff 过滤；不删除以避免并发竞态。
§
Reviewed and updated sop-notebooklm-research skill based on execution experience: enhanced timing/logging requirements, clarified file renaming rules based on report title slug, and improved overall procedure clarity.
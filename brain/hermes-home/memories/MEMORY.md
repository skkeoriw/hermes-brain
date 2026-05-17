【重要约束】禁止使用 OpenRouter 付费模型。若必须用 OpenRouter，只能选免费模型（模型名带 :free 后缀）。
§
SOP wiki-build 超时/守卫竞态: 脚本超600s缺git收尾 或 守卫杀前reset清commit。杀守卫再push。commit含"stage-c done"触发Stage D。Phase 3.A.1 fallback陷阱：先export WIKI_LLM_PROVIDER=deepseek再跑Phase 1会失效——Phase 1第一条source env覆盖回gemini。必须先source env再export override。
§
User's knowledge graph philosophy: Strict "facts from raw only" initially seemed appealing to user, but after discussion agreed that L2 (inference) + L3 (question) layers with explicit confidence/reasoning labels are better than locked-down facts-only approach. This enables deeper insights while maintaining traceability. User now convinced that "releasing discovery with guardrails" > "constraining to raw-only".
§
User's quality diagnostic method: wiki/KG quality issues stem from (1) prompt/pipeline/schema design (main), (2) raw input quality (secondary), (3) model capability (tertiary). Prefers A/B testing to isolate root cause before fixing; prioritizes "define real problem first" over model change.
§
Updated sop-notebooklm-research skill to include timing logs, duration calculation, and required log fields (start_time, end_time, duration_seconds, videos_processed). Also clarified the renaming rule for generated files based on report title slug.
§
2026-05-09: 修复 sop-notebooklm-research skill 的 Pitfall #2。原版错误引用 `rm -f` 清理旧文件，与 Step 7"不要删除"矛盾。修正为：遗留旧文件被捎带提交是预期行为（装饰性 bloat），Stage C 通过 diff 过滤；不删除以避免并发竞态。
§
Reviewed and updated sop-notebooklm-research skill based on execution experience: enhanced timing/logging requirements, clarified file renaming rules based on report title slug, and improved overall procedure clarity.
§
webhook session 中 `api_calls` 值：`hermes insights` 仅返回当天汇总，无法精确到当前 session。写 `"api_calls": "unknown"`（不用 0 或空字符串）。交互式 session 中若知道 session ID 可用 `hermes insights --session-id {id}` 获取精确值。
§
sop-notebooklm-research Pitfall #16 2026-05-13: pipeline-context.json 可能为空 `{}`（processor 自动写入静默失败或前序占位）。处理方式：视作新 pipeline，直接覆写完整版。不要在此空对象上做合并。
§
2026-05-17: terminal heredoc (python3 << 'PYEOF') 可静默失败——文件写入返回 success 但内容未持久化。python3 -c "..." 内联方式可靠。已更新 sop-notebooklm-research Pitfall #12。写 pipeline 关键文件后必须 cat 验证。
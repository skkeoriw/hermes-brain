# Slug 生成规范

## Source 页
格式：`{中文标题}.md`
- 直接使用分析文件的语义化中文标题，不加 video_id 前缀。
- 示例：`Hermes + Qwen 3.6 本地最强 AI Agent 组合部署与应用简报.md`

## Entity 页 → ⚠️ 关键：文件名必须与 wikilink 名称完全一致
格式：`{实体名}.md`

**硬性规则**：entity 文件名必须严格匹配你在 source/concept 等页面中使用的 `[[wikilink]]` 名称。

- 如果你在 source 页中写 `[[Hermes Agent]]`，则 entity 文件必须命名为 `Hermes Agent.md`（含空格、大小写敏感）
- 如果你在 source 页中写 `[[OpenAI]]`，则 entity 文件必须命名为 `OpenAI.md`
- **不要**使用小写 slug 格式（`hermes-agent.md`、`openai.md`），因为 wikilink 走的是 readable 名称匹配
- **例外**：如果某个 entity 有约定俗成的 slug 别名（如 `GPT-5.5 Instant`），可直接使用该别名作为文件名，但务必在所有页面中使用一致的 `[[别名]]`

**检查方法**：创建完所有页面后，执行 grep -rho '\[\[[^]]*\]\]' wiki/ --include='*.md' 提取所有 wikilink，验证每个 wikilink 的目标文件都存在。

## Concept 页
格式：`{概念名}.md`
- 概念：中文概念名称，直接使用中文命名。
- 示例：`执行循环驱动架构.md`、`Token自由.md`

## 注意
- slug 必须唯一，避免冲突。
- 建议先检查对应目录下是否已存在同名文件。
- 所有 wiki 文件使用 write_file 工具写入，禁止 shell heredoc/eval。

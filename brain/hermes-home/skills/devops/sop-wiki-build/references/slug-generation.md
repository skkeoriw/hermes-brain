# Slug 生成规范

## Source 页
格式：`{中文标题}.md`
- 直接使用分析文件的语义化中文标题，不加 video_id 前缀。
- 示例：`Hermes + Qwen 3.6 本地最强 AI Agent 组合部署与应用简报.md`

## Entity 页 → ⚠️ 遵循 TheSchema.md 的小写 slug 规范
格式：`{小写-slug}.md`

**硬性规则**：entity 文件名使用**小写 slug 格式**，与 `[[wikilink]]` 中使用的名称完全一致（大小写敏感）。

- TheSchema.md §2 定义 entity 命名规范为 `{实体名}.md（小写 slug）`
- 如果你在 source 页中写 `[[hermes-agent]]`，entity 文件必须命名为 `hermes-agent.md`
- 如果你在 source 页中写 `[[openai]]`，entity 文件必须命名为 `openai.md`
- **不要**使用带空格的 readable 名称（`Hermes Agent.md`、`OpenAI.md`），因为 TheSchema.md 要求小写 slug
- 对于中文实体名（如 `chatgpt`、`evomap`），直接使用英文 slug 或全小写拼音

**一致性规则**：在所有页面中使用 `[[slug]]` 引用实体时，必须与 entity 文件名完全一致（Linux 文件系统大小写敏感）。

**检查方法**：创建完所有页面后执行：
```bash
cd {wiki_local_path}/wiki
grep -rho '\[\[[^]]*\]\]' sources/ entities/ concepts/ comparisons/ overview/ --include='*.md' | sort -u
```
然后遍历每个 wikilink 确认目标文件存在于对应的 entities/, concepts/ 等目录中。

## Concept 页
格式：`{概念名}.md`
- 概念：中文概念名称，直接使用中文命名。
- 示例：`执行循环驱动架构.md`、`Token自由.md`

## 注意
- slug 必须唯一，避免冲突。
- 建议先检查对应目录下是否已存在同名文件。
- 所有 wiki 文件使用 write_file 工具写入，禁止 shell heredoc/eval。

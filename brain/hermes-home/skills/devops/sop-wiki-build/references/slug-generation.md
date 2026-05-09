# Slug 生成规范

## Source 页
格式：`{video-id}-{短标题-slug}.md`
- `video-id`：YouTube 视频 ID（如 `NbldZVdusKo`）
- `短标题-slug`：视频标题的简短英文摘录，转换为小写，空格替换为连字符，移除特殊字符。
  示例：标题 "Hermes Agent 与 OpenClaw 技术深度对比简报" -> slug `hermes-agent-openclaw-comparison`
  （可参考现有文件：`NbldZVdusKo-hermes-agent-openclaw-comparison.md`）

## Entity 页
格式：`{实体名-slug}.md`
- 实体名：英文实体名称，转换为小写，空格替换为连字符。
  示例：`Nous Research` -> `nous-research`
- 若实体名已有约定俗成的缩写或变体，优先使用常见形式。
  示例：`Hermes Agent` -> `hermes-agent`

## Concept 页
格式：`{概念-slug}.md`
- 概念：英文概念名称，转换为小写，空格替换为连字符。
  示例：`执行循环驱动架构` -> 先翻译为英文 "execution-loop-driven architecture" -> slug `execution-loop-driven-architecture`
  （但为保持中文可读性，亦可使用拼音或混合命名，需保持唯一性；本项目中文概念页使用中文名称拼音 slug，例如 `执行循环驱动架构` -> `zhi-xing-xun-huan-qu-dong-jia-gou`，实际中文命名请参现有文件。）
  注：本项目中文概念页实际使用中文名称（如 `执行循环驱动架构.md`），slug 即为文件名（不含 .md），因此中文命名直接使用。

## 注意
- slug 必须唯一，避免冲突。
- 建议先检查对应目录下是否已存在同名文件。
- 所有 slug 使用小写连字符形式。
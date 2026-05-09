# Dead Link Categories in Wiki Builds

LLM 生成的 wikilink 与磁盘文件名之间存在多种不一致模式。本文件记录了所有已知的 dead link 类型及其修复方法。

## 分类表

| # | 类型 | 示例（wikilink） | 期望目标 | 根因 | 检测工具 |
|---|------|-----------------|---------|------|---------|
| 1 | **大小写不匹配** | `[[Computer Use]]` | `computer-use.md` | LLM 使用自然语言（大写+空格）而非 slug 格式 | Python 脚本（`.lower()`） |
| 2 | **空格 vs 连字符** | `[[Codex Chrome 插件]]` | `Codex-Chrome-插件.md` | LLM 随机用空格代替 slug 连字符 | Python 脚本 |
| 3 | **缩写 vs 全名** | `[[CDP]]` | `chrome-devtools-protocol.md` | LLM 用通用缩写而非指定文件名 | Python 脚本 + 人工审核 |
| 4 | **中文 vs English slug** | `[[Chrome调试协议]]` | `chrome-devtools-protocol.md` | LLM 用中文翻译名而文件名用英文 | Python 脚本 |
| 5 | **命名规范混用** | `[[Deep Research]]` | 不存在（概念页未创建） | LLM 引用了不在索引中的概念 | Python 脚本 |
| 6 | **路径前缀差异** | `[[sources/xxx]]` | `sources/xxx.md` | 部分 wikilink 含路径前缀 | `find -path` 检查 |

## 修复建议

- **类型 1-2**：用 `sed` 批量替换（全文件）
- **类型 3-4**：改为正确的文件名 slug
- **类型 5**：若概念不核心，改为纯文本；若重要则创建新概念页
- **类型 6**：确保检查方法支持路径前缀（`find -path` 而非 `find -name`）

## 推荐的死链检查流程

```bash
# 1. 运行 verify-quality.sh（基础检查）
bash /home/zhouhuijuan1987/.hermes/skills/devops/sop-wiki-build/scripts/verify-quality.sh {wiki_path}

# 2. 运行 Python 精确扫描（捕获类型 1-5）
python3 -c "import re,glob; e={f.replace('wiki/','').rsplit('.md',1)[0].lower() for f in glob.glob('wiki/**/*.md',recursive=True)}; d=0; [print(f'DEAD: {f}: [[{l.strip()}]]') or (d:=d+1) for f in glob.glob('wiki/**/*.md',recursive=True) for l in re.findall(r'\[\[([^\]]+?)(?:\|[^\]]+)?\]\]',open(f).read()) if not any(l.strip().lower()==s or l.strip().lower()==s.split('/')[-1] for s in e)]; print('OK' if d==0 else f'{d} DEAD')"

# 3. 检查 index.md 和 log.md（盲区）
grep -n '\[\[.*\]\]' index.md log.md 2>/dev/null | sed 's/\[\[/,/' | while IFS=, read -r line slug; do
  slug=$(echo "$slug" | sed 's/\[\[//;s/\]\]//;s/|.*//')
  found=$(find wiki/ -path "*/${slug}.md" 2>/dev/null | head -1)
  [ -z "$found" ] && [ -n "$slug" ] && echo "INDEX DEAD: $line → [[${slug}]]"
done
```

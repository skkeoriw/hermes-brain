# TheSchema.md Layout Reference

Used by repos like `llm-wiki-obsidian-blink` and `prompt-qa-unified-wiki`.
Source of truth: https://github.com/ChangfengHU/llm-wiki-obsidian-blink/blob/main/TheSchema.md

## Directory Structure

```
raw/                        # source files, read-only after ingestion
wiki/
  sources/                  # one page per raw source (summary)
  entities/                 # people, projects, tools, orgs
  concepts/                 # methods, theories, models
  comparisons/              # side-by-side analyses
  overview/                 # synthesis / survey pages
  queries/                  # Q&A worth keeping
  index.md                  # wiki-level index
  log.md                    # wiki-level log
TheSchema.md                # canonical schema (not SCHEMA.md)
index.md                    # root index
log.md                      # root log
```

## Three-Layer Model (strictly enforced)

| Layer | Name | Rule |
|-------|------|------|
| L1 | Fact | Must be directly supported by raw/**/*.md. No speculation. |
| L2 | Inference | Inferred from 2+ L1 facts. MUST have confidence + reasoning. |
| L3 | Question | Open questions, gaps, hypotheses. Not facts. |

## Frontmatter (all wiki pages)

```yaml
---
type: source|entity|concept|comparison|overview|query
tags: [tag1, tag2]
summary: 一句话说明核心内容
sources: [raw/xxx.md]
created: 2026-05-07
updated: 2026-05-07
layer: L1           # L1 | L2 | L3
confidence: high    # required for L2/L3; optional for L1
reasoning: ...      # required for L2/L3
---
```

Required fields: `type`, `tags`, `summary`, `sources`, `updated`, `layer`
L2/L3 additionally require: `confidence`, `reasoning`

## Raw File Format (translated arxiv sources)

When ingesting arxiv papers with Chinese translation:

```yaml
---
title: "中文标题"
title_en: "English Title"
source_url: https://arxiv.org/abs/XXXX.XXXXX
arxiv_id: "XXXX.XXXXX"
ingested: 2026-05-07
tags: [agent, rag, llm, research]
---

# 中文标题

**原文标题：** English Title
**来源：** https://arxiv.org/abs/XXXX.XXXXX
**采集日期：** 2026-05-07

## 摘要

（完整中文翻译，无英文对照）
```

## Arxiv Scrape + Google Translate Pattern

```python
import urllib.request, urllib.parse, json, re

def fetch_arxiv(arxiv_id):
    url = f"http://export.arxiv.org/abs/{arxiv_id}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', 'ignore')
    title_m = re.search(r'<h1 class="title mathjax"><span class="descriptor">Title:</span>\s*(.+?)</h1>', html, re.S)
    title = re.sub(r'\s+', ' ', title_m.group(1).strip()) if title_m else ''
    abs_m = re.search(r'<blockquote class="abstract mathjax">\s*<span class="descriptor">Abstract:</span>\s*(.+?)</blockquote>', html, re.S)
    abstract = re.sub(r'\s+', ' ', abs_m.group(1).strip()) if abs_m else ''
    return title, abstract

def translate(text):
    url = 'https://translate.googleapis.com/translate_a/single?' + urllib.parse.urlencode({
        'client': 'gtx', 'sl': 'en', 'tl': 'zh-CN', 'dt': 't', 'q': text
    })
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    data = json.loads(urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'ignore'))
    return ''.join([x[0] for x in data[0] if x and x[0]])
```

Pitfalls:
- HTML may contain `<a href=...>` tags inside abstract text — strip or leave as-is (renders fine in Obsidian)
- Sleep 0.5-1s between requests to avoid rate limiting on both arxiv and gtx
- `idx = int(f.name.split('-')[2])` fails if filename format differs — always inspect filenames before parsing

## Git Auth with PAT

```bash
git remote set-url origin https://<PAT>@github.com/<owner>/<repo>.git
git push origin main
```

No other setup needed. Works for any repo the PAT has write access to.

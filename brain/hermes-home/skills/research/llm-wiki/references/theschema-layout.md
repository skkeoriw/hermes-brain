# TheSchema.md Layout Variant

Some repositories (like llm-wiki-obsidian-blink) use `TheSchema.md` instead of `SCHEMA.md` as the schema file. This layout has specific characteristics:

## Directory Structure
When `TheSchema.md` is present, the expected layout is:
```
wiki/
├── TheSchema.md          # Schema file (replaces SCHEMA.md)
├── index.md              # Global index (may be synchronized with wiki/index.md)
├── log.md                # Global log (may be synchronized with wiki/log.md)
├── raw/                  # Layer 1: Immutable sources
│   └── ...               # Source files
└── wiki/                 # Layer 2: Wiki maintenance layer
    ├── sources/          # Source summary pages (type: source)
    ├── entities/         # Entity pages (type: entity)
    ├── concepts/         # Concept pages (type: concept)
    ├── comparisons/      # Comparison pages (type: comparison)
    ├── overview/         # Overview/summary pages (type: overview)
    └── queries/          # Query result pages (type: query)
```

## Frontmatter Requirements (L1/L2/L3 Model)
TheSchema.md enforces a strict three-layer model in all wiki page frontmatter:

```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: source|entity|concept|comparison|overview|query
tags: [from taxonomy]
summary: One-sentence summary
sources: [relative/path/to/raw/file.md]
layer: L1|L2|L3          # REQUIRED - knowledge layer
confidence: high|medium|low  # REQUIRED for L2/L3
reasoning: Short explanation # REQUIRED for L2/L3
---
```

### Layer Definitions:
- **L1 (Fact Layer)**: Only facts directly supported by raw sources. No inference.
- **L2 (Inference Layer)**: Inductive/deductive reasoning from multiple L1 facts. Must show work.
- **L3 (Question Layer)**: Open questions, hypotheses, knowledge gaps. Not treated as established fact.

### Required Fields for L2/L3:
When `layer: L2` or `layer: L3`, both `confidence` and `reasoning` fields are mandatory.

## Migration Notes
If a repository has both `SCHEMA.md` and `TheSchema.md`:
1. `TheSchema.md` takes precedence as the canonical schema
2. The agent should read and follow `TheSchema.md` rules
3. `SCHEMA.md` may be ignored or treated as historical

## Validation Rules
- Every wiki page must specify `layer: L1|L2|L3`
- L2/L3 pages must have both `confidence` and `reasoning`
- `sources` must point to files under `raw/`
- `tags` must be defined in TheSchema.md's taxonomy
- Every page needs at least 2 outgoing `[[wikilinks]]`
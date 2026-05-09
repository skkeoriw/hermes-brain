#!/usr/bin/env bash
# verify-quality.sh — Automated quality check for wiki builds (Step 14b)
#
# Usage: bash /path/to/scripts/verify-quality.sh <wiki_local_path>
#
# Exit codes:
#   0 — all checks pass
#   1 — one or more checks failed
#
# The script prints a report to stdout showing which checks passed/failed.

set -euo pipefail

WIKI_PATH="${1:-}"
if [ -z "$WIKI_PATH" ]; then
  echo "Usage: $0 <wiki_local_path>"
  echo "Example: $0 /home/user/wiki/my-wiki"
  exit 1
fi

if [ ! -d "$WIKI_PATH/wiki" ]; then
  echo "ERROR: $WIKI_PATH/wiki does not exist"
  exit 1
fi

ALL_PASSED=true
TOTAL_PAGES=0

cd "$WIKI_PATH"

echo "========================================"
echo " WIKI QUALITY VERIFICATION"
echo " Location: $WIKI_PATH"
echo "========================================"
echo ""

# === CHECK 1: Frontmatter completeness ===
echo "--- [Check 1] Frontmatter completeness ---"
REQUIRED_FIELDS=("title:" "type:" "tags:" "summary:" "sources:" "layer:")
CHECK1_FAILED=false

while IFS= read -r -d '' page; do
  TOTAL_PAGES=$((TOTAL_PAGES + 1))
  REL="${page#$WIKI_PATH/}"
  FM=$(sed -n '1,/^---$/p' "$page" 2>/dev/null)
  
  for field in "${REQUIRED_FIELDS[@]}"; do
    if ! echo "$FM" | grep -q "^${field}"; then
      echo "  ❌ $REL: missing '$field'"
      CHECK1_FAILED=true
      ALL_PASSED=false
    fi
  done
done < <(find "$WIKI_PATH/wiki" -name '*.md' -print0)

if [ "$CHECK1_FAILED" = false ]; then
  echo "  ✅ All $TOTAL_PAGES pages have complete frontmatter"
fi
echo ""

# === CHECK 2: Wikilink count (at least 2 per page) ===
echo "--- [Check 2] Wikilink count (≥2 per page) ---"
CHECK2_FAILED=false

while IFS= read -r -d '' page; do
  REL="${page#$WIKI_PATH/}"
  
  # Get wikilinks from body (after frontmatter)
  WIKILINKS=$(awk 'BEGIN{found=0} /^---$/{found++;next} found>=2{print}' "$page" | grep -oP '\[\[\K[^]|]+(?:\|[^]]+)?(?=\]\])' || true)
  
  # Count non-mindmap links
  COUNT=0
  while IFS= read -r link; do
    [ -z "$link" ] && continue
    case "$link" in
      *"-模型深度分析简报"*) continue;;
      *"-深度对比及技术趋势简报"*) continue;;
      *"本地最强-Agent"*) continue;;
    esac
    COUNT=$((COUNT + 1))
  done <<< "$WIKILINKS"
  
  if [ "$COUNT" -lt 2 ]; then
    echo "  ❌ $REL: only $COUNT non-mindmap wikilinks"
    CHECK2_FAILED=true
    ALL_PASSED=false
  fi
done < <(find "$WIKI_PATH/wiki" -name '*.md' -print0)

if [ "$CHECK2_FAILED" = false ]; then
  echo "  ✅ All pages have ≥2 effective wikilinks"
fi
echo ""

# === CHECK 3: Content length ===
echo "--- [Check 3] Content length ---"
CHECK3_FAILED=false

while IFS= read -r -d '' page; do
  REL="${page#$WIKI_PATH/}"
  FTYPE=$(echo "$REL" | cut -d'/' -f1)
  
  BODY=$(awk 'BEGIN{found=0} /^---$/{found++;next} found>=2{print}' "$page" 2>/dev/null || true)
  LEN=$(echo "$BODY" | wc -m)
  
  case "$FTYPE" in
    sources|overview)
      if [ "$LEN" -lt 400 ]; then
        echo "  ❌ $REL: only $LEN chars (need ≥400)"
        CHECK3_FAILED=true
        ALL_PASSED=false
      fi
      ;;
    entities|concepts)
      if [ "$LEN" -lt 200 ]; then
        echo "  ❌ $REL: only $LEN chars (need ≥200)"
        CHECK3_FAILED=true
        ALL_PASSED=false
      fi
      ;;
  esac
done < <(find "$WIKI_PATH/wiki" -maxdepth 2 -name '*.md' -print0)

if [ "$CHECK3_FAILED" = false ]; then
  echo "  ✅ All pages meet minimum content length"
fi
echo ""

# === CHECK 4: Sources field files exist ===
echo "--- [Check 4] Sources field verification ---"
CHECK4_FAILED=false

while IFS= read -r -d '' page; do
  REL="${page#$WIKI_PATH/}"
  SOURCE_FILES=$(sed -n '1,/^---$/p' "$page" | grep '^\s*-\s*raw/' | sed 's/^\s*-\s*//' || true)
  
  while IFS= read -r src; do
    [ -z "$src" ] && continue
    if [ ! -f "$WIKI_PATH/$src" ] && [ ! -f "$(dirname "$WIKI_PATH")/$src" ]; then
      echo "  ❌ $REL: source '$src' not found"
      CHECK4_FAILED=true
      ALL_PASSED=false
    fi
  done <<< "$SOURCE_FILES"
done < <(find "$WIKI_PATH/wiki" -name '*.md' -print0)

if [ "$CHECK4_FAILED" = false ]; then
  echo "  ✅ All 'sources:' files exist in raw/"
fi
echo ""

# === CHECK 5: Dead links ===
echo "--- [Check 5] Dead link check ---"
CHECK5_FAILED=false

ALL_LINKS=$(grep -rho '\[\[[^]]*\]\]' "$WIKI_PATH/wiki" --include='*.md' 2>/dev/null | \
  sed 's/\[\[//;s/\]\]//;s/|.*//' | sort -u)

while IFS= read -r target; do
  [ -z "$target" ] && continue
  case "$target" in
    *"-模型深度分析简报"*) continue;;
    *"-深度对比及技术趋势简报"*) continue;;
    *"本地最强-Agent"*) continue;;
  esac
  
  # Path-prefixed wikilinks (e.g. [[sources/xxx]] → wiki/sources/xxx.md) use the prefix
  # as part of the wiki/ subdirectory. Use -path to match the full relative path.
  FOUND=$(find "$WIKI_PATH/wiki" -path "*/${target}.md" -print -quit 2>/dev/null || true)
  if [ -z "$FOUND" ]; then
    echo "  ❌ Dead link: [[${target}]] → no .md file found in wiki/"
    CHECK5_FAILED=true
    ALL_PASSED=false
  fi
done <<< "$ALL_LINKS"

if [ "$CHECK5_FAILED" = false ]; then
  echo "  ✅ No dead links found"
fi
echo ""

# === CHECK 6: Dual .md.md extension ===
echo "--- [Check 6] Double .md.md extension ---"
CHECK6_FAILED=false
DOUBLE_MD=$(find "$WIKI_PATH/wiki" -name '*.md.md' 2>/dev/null)
if [ -n "$DOUBLE_MD" ]; then
  echo "  ❌ Found files with double .md.md extension:"
  echo "$DOUBLE_MD" | while IFS= read -r f; do echo "       $f"; done
  CHECK6_FAILED=true
  ALL_PASSED=false
else
  echo "  ✅ No .md.md files found"
fi
echo ""

# === CHECK 7: Truncated filenames ===
echo "--- [Check 7] Truncated filename detection ---"
CHECK7_FAILED=false

# Build a map: basename → full path, including partial truncations
for link in $ALL_LINKS; do
  # Exact match check already done in Check 5; here we check if a file
  # exists whose name equals $link MINUS its last character (truncation pattern)
  [ -z "$link" ] && continue
  [ ${#link} -le 2 ] && continue
  TRUNCATED="${link:0:$((${#link}-1))}"
  TRUNC_FILE=$(find "$WIKI_PATH/wiki" -name "${TRUNCATED}.md" -print -quit 2>/dev/null || true)
  if [ -n "$TRUNC_FILE" ]; then
    REL="${TRUNC_FILE#$WIKI_PATH/}"
    echo "  ⚠️  Truncation detected: wikilink [[${link}]] → on-disk file '${REL}'"
    echo "       Suggestion: mv '${REL}' '$(dirname ${REL})/${link}.md'"
    CHECK7_FAILED=true
    ALL_PASSED=false
  fi
done

if [ "$CHECK7_FAILED" = false ]; then
  echo "  ✅ No truncated filenames detected"
fi
echo ""

# === SUMMARY ===
echo "========================================"
echo " RESULTS"
echo "========================================"
echo " Total pages checked: $TOTAL_PAGES"
echo ""

if [ "$ALL_PASSED" = true ]; then
  echo " ✅ ALL CHECKS PASSED"
  exit 0
else
  echo " ❌ SOME CHECKS FAILED — see above"
  exit 1
fi

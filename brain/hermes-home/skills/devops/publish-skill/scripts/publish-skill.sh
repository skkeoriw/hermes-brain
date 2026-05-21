#!/usr/bin/env bash
# publish-skill.sh — 将本地 skill 打包为 zip 发布，生成一键安装命令
#
# 用法: publish-skill.sh <skill-name> [skill-dir]
#
# 流程:
#   1. 将 skill 目录打成 zip 上传到文件服务器
#   2. 生成安装脚本（下载 zip → 解压 → 复制到目标目录）上传
#   3. 输出 bash <(curl -fsSL ...) 安装命令

set -euo pipefail

SKILL_NAME="${1:-}"
FILE_API_URL="${FILE_API_URL:-https://upload-r2.vyibc.com}"
FILE_API_TOKEN="${FILE_API_TOKEN:-123456}"
CDN_URL="${CDN_URL:-https://skill.vyibc.com}"
ALLOW_EXTERNAL_SKILL_DIR="${ALLOW_EXTERNAL_SKILL_DIR:-0}"

resolve_abs_path() {
  local path="$1"
  [[ -d "$path" ]] || return 1
  (cd "$path" && pwd -P)
}

is_allowed_skill_dir() {
  local dir_abs="$1"
  local candidate

  for candidate in \
    "${HOME}/.codex/skills/${SKILL_NAME}" \
    "${HOME}/.cursor/skills/${SKILL_NAME}" \
    "${HOME}/.copilot/skills/${SKILL_NAME}" \
    "${HOME}/.gemini/skills/${SKILL_NAME}" \
    "${HOME}/.gemini/antigravity/skills/${SKILL_NAME}" \
    "${HOME}/.claude/skills/${SKILL_NAME}" \
    "${HOME}/.openclaw/workspace/skills/${SKILL_NAME}" \
    "${HOME}/.agents/skills/${SKILL_NAME}"; do
    [[ -d "$candidate" ]] || continue
    if [[ "$dir_abs" == "$(resolve_abs_path "$candidate")" ]]; then
      return 0
    fi
  done

  return 1
}

# ── 参数检查 ──────────────────────────────────────────────
if [[ -z "$SKILL_NAME" ]]; then
  echo "用法: $0 <skill-name>" >&2
  echo ""
  echo "本机已安装的 skills:"
  for d in \
    "${HOME}/.codex/skills" \
    "${HOME}/.cursor/skills" \
    "${HOME}/.copilot/skills" \
    "${HOME}/.gemini/skills" \
    "${HOME}/.gemini/antigravity/skills" \
    "${HOME}/.claude/skills" \
    "${HOME}/.openclaw/workspace/skills" \
    "${HOME}/.agents/skills"; do
    [[ -d "$d" ]] && ls "$d" 2>/dev/null | grep -v '^\.' | sed "s|^|  [$d] |"
  done
  exit 1
fi

# ── 查找 skill 目录 ───────────────────────────────────────
SKILL_DIR="${2:-}"
if [[ -z "$SKILL_DIR" ]]; then
  for candidate in \
    "${HOME}/.codex/skills/${SKILL_NAME}" \
    "${HOME}/.cursor/skills/${SKILL_NAME}" \
    "${HOME}/.copilot/skills/${SKILL_NAME}" \
    "${HOME}/.gemini/skills/${SKILL_NAME}" \
    "${HOME}/.gemini/antigravity/skills/${SKILL_NAME}" \
    "${HOME}/.claude/skills/${SKILL_NAME}" \
    "${HOME}/.openclaw/workspace/skills/${SKILL_NAME}" \
    "${HOME}/.agents/skills/${SKILL_NAME}"; do
    if [[ -d "$candidate" ]]; then
      SKILL_DIR="$candidate"
      break
    fi
  done
fi

if [[ -n "$SKILL_DIR" && -d "$SKILL_DIR" ]]; then
  SKILL_DIR="$(resolve_abs_path "$SKILL_DIR")"
fi

if [[ -z "$SKILL_DIR" || ! -d "$SKILL_DIR" ]]; then
  echo "❌ 找不到 skill 目录: ${SKILL_NAME}" >&2
  echo "搜索路径: ~/.codex/skills/, ~/.cursor/skills/, ~/.copilot/skills/, ~/.gemini/skills/, ~/.gemini/antigravity/skills/, ~/.claude/skills/, ~/.openclaw/workspace/skills/, ~/.agents/skills/" >&2
  exit 1
fi

if ! is_allowed_skill_dir "$SKILL_DIR"; then
  if [[ "$ALLOW_EXTERNAL_SKILL_DIR" != "1" ]]; then
    echo "❌ skill 目录不在允许范围内: ${SKILL_DIR}" >&2
    echo "默认只允许发布以下路径中的 ${SKILL_NAME}:" >&2
    echo "  ~/.codex/skills/${SKILL_NAME}" >&2
    echo "  ~/.cursor/skills/${SKILL_NAME}" >&2
    echo "  ~/.copilot/skills/${SKILL_NAME}" >&2
    echo "  ~/.gemini/skills/${SKILL_NAME}" >&2
    echo "  ~/.gemini/antigravity/skills/${SKILL_NAME}" >&2
    echo "  ~/.claude/skills/${SKILL_NAME}" >&2
    echo "  ~/.openclaw/workspace/skills/${SKILL_NAME}" >&2
    echo "  ~/.agents/skills/${SKILL_NAME}" >&2
    echo "" >&2
    echo "如需从仓库目录等外部路径发布，请显式开启覆盖：" >&2
    echo "  ALLOW_EXTERNAL_SKILL_DIR=1 $0 ${SKILL_NAME} ${SKILL_DIR}" >&2
    exit 1
  fi
  echo "⚠️  使用外部 skill 目录发布: ${SKILL_DIR}" >&2
fi

echo "📦 打包 skill: ${SKILL_NAME}"
echo "   来源目录: ${SKILL_DIR}"
echo ""

TMPDIR_WORK=$(mktemp -d /tmp/publish-skill-XXXXXX)
trap 'rm -rf "$TMPDIR_WORK"' EXIT

TS=$(date +%Y%m%d%H%M%S)
ZIP_FILENAME="${SKILL_NAME}-${TS}.zip"
ZIP_PATH="${TMPDIR_WORK}/${ZIP_FILENAME}"

# ── 打 zip（保留目录结构，zip 解压后得到 <skill-name>/ 目录）──
echo "🗜  压缩..."
# 从 skill 目录的上一级打包，解压后是 <skill-name>/...
if command -v zip &>/dev/null; then
  (cd "$(dirname "$SKILL_DIR")" && zip -qr "$ZIP_PATH" "$(basename "$SKILL_DIR")")
elif command -v python3 &>/dev/null; then
  python3 -c "
import zipfile, os, sys
skill_dir = sys.argv[1]
zip_path  = sys.argv[2]
base      = os.path.basename(skill_dir)
parent    = os.path.dirname(skill_dir)
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(skill_dir):
        for f in files:
            abs_path = os.path.join(root, f)
            arc_name = os.path.join(base, os.path.relpath(abs_path, skill_dir))
            zf.write(abs_path, arc_name)
" "$SKILL_DIR" "$ZIP_PATH"
else
  echo "❌ 需要 zip 或 python3 来打包，请先安装其中一个" >&2
  exit 1
fi
echo "   ✅ $(du -sh "$ZIP_PATH" | cut -f1) — ${ZIP_PATH}"
echo ""

# ── 上传 zip ──────────────────────────────────────────────
echo "📤 上传 zip..."
ZIP_UPLOAD=$(curl -s --location "${FILE_API_URL}" \
  --header "Authorization: Bearer ${FILE_API_TOKEN}" \
  --form "file=@${ZIP_PATH};type=text/plain" \
  --form "domain=${CDN_URL}" \
  --form "name=${ZIP_FILENAME}")
ZIP_URL=$(echo "$ZIP_UPLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('image_url',''))" 2>/dev/null || true)

if [[ -z "$ZIP_URL" ]]; then
  echo "❌ zip 上传失败: $ZIP_UPLOAD" >&2
  exit 1
fi
echo "   ✅ ${ZIP_URL}"
echo ""

# ── 生成安装脚本 ──────────────────────────────────────────
INSTALL_FILENAME="install-${SKILL_NAME}.sh"
INSTALL_SCRIPT="${TMPDIR_WORK}/${INSTALL_FILENAME}"

cat > "$INSTALL_SCRIPT" << SCRIPT_EOF
#!/usr/bin/env bash
# Auto-generated one-click install script for: ${SKILL_NAME}
# Generated by publish-skill — https://skills.vyibc.com/install-publish-skill.sh
set -euo pipefail

SKILL_NAME="${SKILL_NAME}"
ZIP_URL="${ZIP_URL}"

# ── 工具选择 ──────────────────────────────────────────────
TARGET="\${1:-}"
if [[ -z "\$TARGET" ]]; then
  echo "🛠  选择安装 \${SKILL_NAME} 到哪个 AI 工具："
  echo "  1) Codex        (~/.codex/skills/)"
  echo "  2) Cursor       (~/.cursor/skills/)"
  echo "  3) Claude       (~/.claude/skills/)"
  echo "  4) Gemini       (~/.gemini/skills/)"
  echo "  5) Antigravity  (~/.gemini/antigravity/skills/)"
  echo "  6) Copilot      (~/.copilot/skills/)"
  echo "  7) OpenClaw     (~/.openclaw/workspace/skills/)"
  echo "  8) Agents       (~/.agents/skills/)"
  echo "  9) Hermes       (~/.hermes/skills/devops/)"
  echo " 10) 全部安装"
  read -rp "请输入编号 [1-10]: " CHOICE
  case "\$CHOICE" in
    1) TARGET="codex"       ;;
    2) TARGET="cursor"      ;;
    3) TARGET="claude"      ;;
    4) TARGET="gemini"      ;;
    5) TARGET="antigravity" ;;
    6) TARGET="copilot"     ;;
    7) TARGET="openclaw"    ;;
    8) TARGET="agents"      ;;
    9) TARGET="hermes"      ;;
   10) TARGET="all"         ;;
    *) echo "❌ 无效选项"; exit 1 ;;
  esac
fi

case "\$TARGET" in
  codex)       DIRS=("\$HOME/.codex/skills")                          ;;
  cursor)      DIRS=("\$HOME/.cursor/skills")                         ;;
  claude)      DIRS=("\$HOME/.claude/skills")  ;;
  gemini)      DIRS=("\$HOME/.gemini/skills")                         ;;
  antigravity) DIRS=("\$HOME/.gemini/antigravity/skills")             ;;
  copilot)     DIRS=("\$HOME/.copilot/skills")                 ;;
  openclaw)    DIRS=("\$HOME/.openclaw/workspace/skills")      ;;
  agents)      DIRS=("\$HOME/.agents/skills")                  ;;
  hermes)      DIRS=("\$HOME/.hermes/skills/devops")           ;;
  all)
    DIRS=(
      "\$HOME/.codex/skills"
      "\$HOME/.cursor/skills"
      "\$HOME/.claude/skills"
      "\$HOME/.gemini/skills"
      "\$HOME/.gemini/antigravity/skills"
      "\$HOME/.copilot/skills"
      "\$HOME/.openclaw/workspace/skills"
      "\$HOME/.agents/skills"
      "\$HOME/.hermes/skills/devops"
    ) ;;
  *) echo "❌ 不支持的 target: \$TARGET"; exit 1 ;;
esac

echo ""
echo "🚀 安装 \${SKILL_NAME} ..."
echo ""

# ── 下载 zip ──────────────────────────────────────────────
TMPWORK=\$(mktemp -d /tmp/install-skill-XXXXXX)
trap 'rm -rf "\$TMPWORK"' EXIT

echo "   下载 \${ZIP_URL} ..."
curl -fsSL "\${ZIP_URL}" -o "\${TMPWORK}/skill.zip"

# ── 解压到临时目录（优先 unzip，回退到 python3）────────────
mkdir -p "\${TMPWORK}/extracted"
if command -v unzip &>/dev/null; then
  unzip -q "\${TMPWORK}/skill.zip" -d "\${TMPWORK}/extracted"
elif command -v python3 &>/dev/null; then
  python3 -m zipfile -e "\${TMPWORK}/skill.zip" "\${TMPWORK}/extracted"
elif command -v python &>/dev/null; then
  python -m zipfile -e "\${TMPWORK}/skill.zip" "\${TMPWORK}/extracted"
else
  echo "❌ 需要 unzip 或 python3 来解压，请先安装其中一个" >&2
  exit 1
fi

# 解压后的目录就是 <skill-name>/
EXTRACTED_DIR="\${TMPWORK}/extracted/\${SKILL_NAME}"
if [[ ! -d "\$EXTRACTED_DIR" ]]; then
  # 兼容：如果 zip 里只有一个目录，用它
  EXTRACTED_DIR=\$(find "\${TMPWORK}/extracted" -mindepth 1 -maxdepth 1 -type d | head -1)
fi

# ── 复制到各目标目录 ──────────────────────────────────────
for BASE_DIR in "\${DIRS[@]}"; do
  DEST="\${BASE_DIR}/\${SKILL_NAME}"
  mkdir -p "\$BASE_DIR"
  rm -rf "\$DEST"
  cp -r "\$EXTRACTED_DIR" "\$DEST"
  find "\$DEST/scripts" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
  echo "  ✅ → \$DEST"
done

echo ""
echo "✅ 安装完成！对 AI 说触发词即可使用 \${SKILL_NAME}。"
echo ""
SCRIPT_EOF

chmod +x "$INSTALL_SCRIPT"

# ── 上传安装脚本 ──────────────────────────────────────────
echo "📤 上传安装脚本..."
SCRIPT_UPLOAD=$(curl -s --location "${FILE_API_URL}" \
  --header "Authorization: Bearer ${FILE_API_TOKEN}" \
  --form "file=@${INSTALL_SCRIPT};type=text/plain" \
  --form "domain=${CDN_URL}" \
  --form "name=${INSTALL_FILENAME}")
SCRIPT_URL=$(echo "$SCRIPT_UPLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('image_url',''))" 2>/dev/null || true)

if [[ -z "$SCRIPT_URL" ]]; then
  echo "❌ 安装脚本上传失败: $SCRIPT_UPLOAD" >&2
  exit 1
fi
echo "   ✅ ${SCRIPT_URL}"

# ── 生成文档页 ────────────────────────────────────────────
SKILL_MD=""
[[ -f "${SKILL_DIR}/SKILL.md" ]] && SKILL_MD=$(cat "${SKILL_DIR}/SKILL.md")

DOC_RESP=$(python3 - <<PYEOF
import json, urllib.request, sys

content = """# ${SKILL_NAME} — 一键安装

## 安装命令

\`\`\`bash
bash <(curl -fsSL ${SCRIPT_URL})
\`\`\`

---

${SKILL_MD}"""

body = json.dumps({"content": content, "title": "Install: ${SKILL_NAME}"}).encode()
req = urllib.request.Request(
    "https://upload.vyibc.com/v1beta/documents:toPage",
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print(r.read().decode())
except Exception as e:
    print("{}")
PYEOF
)
DOC_URL=$(echo "$DOC_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('page_url',''))" 2>/dev/null || true)

# ── 本地备份 ──────────────────────────────────────────────
LOCAL_OUT="${HOME}/.codex/skills/.system/published/${INSTALL_FILENAME}"
mkdir -p "$(dirname "$LOCAL_OUT")"
cp "$INSTALL_SCRIPT" "$LOCAL_OUT"

# ── 输出结果 ──────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Skill 发布成功！"
echo ""
echo "📦 Skill:   ${SKILL_NAME}"
echo "🗜  包文件:  ${ZIP_URL}"
echo ""
echo "🚀 一键安装命令："
echo ""
echo "   bash <(curl -fsSL ${SCRIPT_URL})"
echo ""
[[ -n "$DOC_URL" ]] && echo "📄 文档页面: ${DOC_URL}"
echo "💾 本地备份: ${LOCAL_OUT}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 机器可读输出（供 agent 解析）
python3 -c "
import json
print('PUBLISH_RESULT_JSON=' + json.dumps({
  'skill': '${SKILL_NAME}',
  'install_command': 'bash <(curl -fsSL ${SCRIPT_URL})',
  'script_url': '${SCRIPT_URL}',
  'zip_url': '${ZIP_URL}',
  'doc_url': '${DOC_URL}',
  'local_backup': '${LOCAL_OUT}'
}))
"

# Copilot 初始化任务：把这台机器变成已有 Hermes 大脑节点

你是运行在一台新机器上的 GitHub Copilot / coding agent。用户不想手动一步一步执行。请你直接完成下面的初始化。

目标：

- 使用私有仓库 `https://github.com/ChangfengHU/hermes-brain` 里的 Hermes 大脑数据初始化当前机器。
- 如果当前机器未安装 Hermes Agent，则安装。
- 将仓库里的 `brain/hermes-home/` 恢复到当前用户的 `${HERMES_HOME:-~/.hermes}`。
- 验证 Hermes、skills、memory、provider 配置是否可用。
- 默认把当前机器设置成 pull 身份，并安装自动同步 timer；不要让新机器默认 push。
- 如果用户明确要求当前机器成为主同步机器，运行 `./scripts/set_sync_role.sh push --git --push`。
- 不要把 token、secret、auth.json、.env 内容打印到终端或聊天里。

重要安全说明：

这个仓库是用户明确允许的私有测试用明文同步仓库，可能包含 `.env`、`auth.json`、OAuth token、API key、webhook secret、gateway pairing data、session transcript 等敏感数据。不要公开，不要上传到其他位置，不要在日志里输出 secrets。

执行策略：

1. 在用户 home 目录下确保仓库存在。
2. 如果不存在，clone：
   `git clone https://github.com/ChangfengHU/hermes-brain.git ~/hermes-brain`
3. 如果已存在，进入仓库并拉取最新：
   `git pull --ff-only`
4. 运行仓库内 bootstrap 脚本：
   - 如果 Hermes 已安装：`./scripts/bootstrap_new_machine.sh --skip-install`
   - 如果 Hermes 未安装：`./scripts/bootstrap_new_machine.sh`
5. 运行验证命令。
6. 如果 GitHub private repo 权限失败，向用户请求 GitHub PAT 或让用户先完成 GitHub auth；不要猜 token。
7. 如果 Hermes provider 登录失败，优先提醒用户重新执行 `hermes model` 或对应 OAuth 登录；不要手动编辑未知 token。
8. 初始化后的默认同步身份是 pull；只有用户明确要求“这台机器作为主同步机器/push 机器”时，才把当前机器设为 push。

推荐直接执行的 shell：

```bash
set -euo pipefail

cd "$HOME"

command -v git >/dev/null || { echo "missing git" >&2; exit 1; }
command -v python3 >/dev/null || { echo "missing python3" >&2; exit 1; }
command -v curl >/dev/null || { echo "missing curl" >&2; exit 1; }

if [ ! -d "$HOME/hermes-brain/.git" ]; then
  git clone https://github.com/ChangfengHU/hermes-brain.git "$HOME/hermes-brain"
fi

cd "$HOME/hermes-brain"
git pull --ff-only || true

if command -v hermes >/dev/null 2>&1; then
  ./scripts/bootstrap_new_machine.sh --skip-install
else
  ./scripts/bootstrap_new_machine.sh
fi

# Verification. Do not print secret file contents.
echo "== Hermes binary =="
command -v hermes
hermes --version || true

echo "== Hermes doctor =="
hermes doctor || true

echo "== Skills =="
hermes skills list | head -80 || true

echo "== Sessions =="
hermes sessions list | head -20 || true

echo "== Brain repo status =="
git status --short

echo "== Brain sync role =="
python3 scripts/hermes_brain_role.py status || true
systemctl --user --no-pager status hermes-brain-auto-sync.timer || true

echo "Bootstrap completed. Start Hermes with: hermes"
```

验证标准：

- `~/hermes-brain` 存在并 tracking `origin/main`。
- `~/.hermes` 存在。
- `~/.hermes/memories/` 存在。
- `~/.hermes/skills/` 存在。
- `~/.hermes/config.yaml` 存在。
- 如果仓库里有 `.env` / `auth.json`，恢复后 `~/.hermes/.env` / `~/.hermes/auth.json` 应存在，但不要读取/打印内容。
- `hermes doctor` 能运行。
- `hermes` 能启动。

Provider / 模型注意事项：

- OpenRouter、OpenAI API key、Anthropic 等 API-key 型 provider：如果 key 已在 `.env` 或 `config.yaml` 中，恢复后通常可直接使用。
- OpenAI Codex、Nous、GitHub Copilot 等 OAuth/device-code 型 provider：`auth.json` 已同步时可能直接可用，但也可能因为机器绑定、过期、刷新失败而需要重新登录。
- GitHub Copilot 特别注意：`gh auth login` 不等于 Hermes 的 Copilot provider 授权。如果 Copilot provider 出现 403 或认证失败，让用户运行 `hermes model` 并选择 GitHub Copilot，按 Hermes 的 Copilot/device-code 流程重新授权。
- VS Code 里的 Copilot 可用，不代表 Hermes CLI 一定已经能用 Copilot provider。

后续同步：

初始化后默认是 pull 身份，自动 timer 会定期执行：

```text
GitHub hermes-brain -> ~/hermes-brain/brain/hermes-home -> ~/.hermes
```

如果用户明确要求当前机器成为唯一主同步机器 / push 机器：

```bash
cd ~/hermes-brain
./scripts/set_sync_role.sh push --git --push
```

之后自动 timer 会定期执行：

```text
~/.hermes -> ~/hermes-brain/brain/hermes-home -> GitHub hermes-brain
```

从远程 repo 手动更新本机 Hermes：

```bash
cd ~/hermes-brain
git pull --ff-only
./scripts/sync_from_repo_to_local.sh
```

把本机 Hermes 新记忆/skills 推回 repo：

```bash
cd ~/hermes-brain
./scripts/sync_from_local_to_repo.sh --git --push -m "sync: update Hermes brain from $(hostname)"
```

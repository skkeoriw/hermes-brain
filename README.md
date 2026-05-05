# Hermes 大脑

Hermes 大脑（hermes-brain）是一个用于在多台机器之间复制和同步 Hermes Agent 持久化数据的仓库。

目标：

- 新机器 clone 本仓库后，可以一键安装 Hermes 并恢复已有 Hermes 大脑。
- 老机器可以把本机新产生的 memory、skill、session、webhook、config、密钥等同步回仓库。
- 所有机器共享同一套 Hermes 能力、记忆、技能和自动化流程。

重要说明：本仓库按用户要求采用“测试用明文全量同步模式”。如果你运行 full sync，仓库可能包含明文密钥、API key、OAuth token、webhook secret、Telegram token 等。必须使用 private 仓库，不要分享给不可信的人。

## 仓库结构

```text
hermes-brain/
  brain/hermes-home/        # 从 ~/.hermes 同步出来的 Hermes 持久化数据
  scripts/                  # 安装、导入、导出、检查脚本
  skills/hermes-brain-sync/ # 给 Hermes/Copilot/其它 agent 使用的操作 skill
  docs/                     # 数据地图、冲突策略、新机器 runbook
```

## 新机器一键恢复

```bash
git clone https://github.com/ChangfengHU/hermes-brain.git
cd hermes-brain
bash scripts/bootstrap_new_machine.sh
```

这个脚本会：

1. 检查 git、curl、python3。
2. 如果未安装 hermes，尝试安装 Hermes Agent。
3. 备份目标机器已有的 ~/.hermes。
4. 把 brain/hermes-home/ 恢复到 ~/.hermes。
5. 修复敏感文件权限。
6. 运行 hermes doctor。

## 从仓库恢复到本机

```bash
cd hermes-brain
bash scripts/sync_from_repo_to_local.sh
```

默认会备份当前 ~/.hermes 到：

```text
~/.hermes-brain-backups/
```

## 从本机同步回仓库

```bash
cd hermes-brain
bash scripts/sync_from_local_to_repo.sh
```

这个脚本会从 ~/.hermes 复制持久化数据到 brain/hermes-home/，排除运行时/可重建内容，例如 venv、logs、cache、lock、SQLite WAL/SHM 等，然后自动 git add/commit/push。

## 同步范围

默认同步 ~/.hermes 下的大部分持久化数据，包括但不限于：

- config.yaml
- .env
- auth.json
- memories/
- skills/
- sessions/
- state.db
- webhook_subscriptions.json
- channel_directory.json
- gateway_state.json
- pairing/
- profiles/
- cron/webhook/API/gateway 相关持久化配置
- 自定义 prompt、脚本、状态文件

默认排除：

- hermes-agent/ 源码和 venv
- logs/
- cache/
- audio_cache/
- __pycache__/
- *.lock
- state.db-wal
- state.db-shm
- 临时文件

## 明文密钥模式

本项目是测试仓库，按要求不加密密钥。请注意：

- private repo 不等于绝对安全。
- 如果密钥曾经明文提交，即使后续删除，也仍可能存在于 Git 历史。
- 生产环境请改用加密密钥同步。

## 给 agent 使用

新机器上如果你使用 Copilot、Hermes 或其它 coding agent，可以让它先阅读：

```text
skills/hermes-brain-sync/SKILL.md
```

然后执行里面的步骤完成安装、恢复和同步。

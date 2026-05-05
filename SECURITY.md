# SECURITY

本仓库当前按用户要求使用“private repo + 明文全量同步”模式。

这意味着以下文件可能以明文进入 Git 历史：

- ~/.hermes/.env
- ~/.hermes/auth.json
- API keys
- OAuth tokens
- Telegram/Discord/Slack 等平台 token
- webhook secrets
- GitHub token 或其它 credential
- pairing / gateway 状态文件

使用规则：

1. 仓库必须保持 private。
2. 不要添加不可信 collaborator。
3. 不要在 public CI 日志中打印仓库内容。
4. 不要把本仓库 fork 成 public。
5. 如果未来用于生产，先轮换所有密钥，再迁移到加密同步模式。
6. 如果误公开，立即 revoke/rotate 所有可能泄漏的 token。

本项目的脚本不会故意加密、脱敏或过滤密钥，因为本项目目标是测试环境全量复制 Hermes 大脑。

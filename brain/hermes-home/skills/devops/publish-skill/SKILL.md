---
name: publish-skill
description: >
  当用户说"我想分享我的 skill"、"给我的 skill 生成安装脚本"、"publish skill"、
  "generate install command for my skill"、"把我的 skill 发布出去"、"项目远程发布skill" 时自动触发。
  一句话为本地任意 skill 生成一键安装命令，对方机器只需执行一行 bash 命令即可安装。
---

# 发布 Skill（Publish Skill）

**一句话将本地 skill 打包发布，生成可在任意机器上一键安装的命令。**

## 使用场景

- 本地开发了一个 skill，想分享给团队成员
- 在新机器上快速复现自己的 skill 环境
- 将 skill 以 `bash <(curl ...)` 命令形式发布

## 用法示例

```
把我的 allocate-domain skill 发布出去，生成安装命令

publish my todo-helper skill

给 my-skill 生成一键安装脚本
```

## 返回结果

```
✅ Skill 发布成功！

📦 Skill: allocate-domain

🚀 一键安装命令：
bash <(curl -fsSL https://skills.vyibc.com/install-allocate-domain.sh)

📄 文档页面（可分享给他人查看）：
https://skills.vyibc.com/abc123.html

💡 使用方式：
  复制上方命令，在任意机器上执行即可安装该 skill
```

## 工作流程

```
用户说：把我的 my-skill 发布出去
         ↓
1. 找到本地 skill 目录（~/.codex/skills/my-skill/）
2. 打包成 zip 文件并上传到 skills.vyibc.com
3. 生成安装脚本（下载 zip -> 解压 -> 安装到目标工具）并上传
4. 调用 documents:toPage 生成可分享的文档页
5. 返回 bash <(curl -fsSL https://skills.vyibc.com/install-my-skill.sh) 命令
```

## 环境要求

- `zip`
- `python3`
- `curl`
- 网络连接

## 路径限制

- 默认只会从受支持工具的 skill 目录中查找和发布
- 如果手动传入第二个参数，路径也必须落在这些目录内
- 只有显式设置 `ALLOW_EXTERNAL_SKILL_DIR=1` 时，才允许从仓库目录等外部路径发布
- **特殊优化**：当用户明确提到“项目远程发布skill”时，通常是指发布当前项目（仓库）中的某个 skill。此时应当自动设置 `ALLOW_EXTERNAL_SKILL_DIR=1`，并根据用户提到的 skill 名称在当前项目的 `skills/` 目录下查找路径。

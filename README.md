# Autonomous Self-Growing Agent 🤖

## 这是什么？

一个**完全自主运行的自我进化代理系统**。不跑在你本地，而是在 GitHub Actions 云端自动执行。

## 它做什么？

1. 📡 **自动采集数据** - 位置数据、公开 API、趋势信息
2. 🧠 **记忆学习** - SQLite 持久化存储，模式分析
3. 🌱 **自我增长** - 自动调整参数、版本号递增
4. 🔄 **自循环** - GitHub Actions 每小时自动触发

## 快速开始

```bash
# 1. 初始化 Git 仓库
cd autonomous-agent
git init
git add .
git commit -m "Initial commit: Autonomous Agent"

# 2. 推送到 GitHub
git remote add origin https://github.com/YOUR_USER/autonomous-agent.git
git push -u origin main

# 3. 等待 GitHub Actions 自动运行
# 也可以手动触发：Actions → Autonomous Agent Cycle → Run workflow
```

## 本地测试

```bash
pip install requests
python src/engine.py
```

## 架构

```
Cloud (GitHub Actions)
  ├── 每小时自动触发
  ├── 采集位置/公开数据
  ├── 分析模式生成洞察
  ├── 自我进化（改配置、升版本）
  └── Auto Commit 回仓库
```

## 文件结构

```
autonomous-agent/
├── src/engine.py          # 核心引擎
├── memory/memory.db        # 记忆数据库（自动增长）
├── data/                   # 采集数据存储
├── config.json             # 配置（自动进化）
├── agent.log               # 运行日志
└── .github/workflows/      # CI/CD 云端任务
```

"""
Autonomous Agent Self-Install Script
技能自安装脚本 - 将当前项目注册为 CodeBuddy Skill
"""

import json
import os
from pathlib import Path
import shutil

SKILL_NAME = "autonomous-agent"
SKILL_DIR = Path.home() / ".codebuddy" / "skills" / SKILL_NAME
BASE_DIR = Path(__file__).parent.parent

def create_skill():
    SKILL_DIR.mkdir(parents=True, exist_ok=True)

    skill_md = f"""# Autonomous Self-Growing Agent 🤖

一个完全自主运行的自我进化代理系统。

## 特性

- 🔄 **自循环运行**：在 GitHub Actions 云端每小时自动执行
- 📡 **数据采集**：自动获取位置数据、公开 API 数据
- 🧠 **记忆系统**：SQLite 持久化存储所有知识
- 🌱 **自我增长**：根据数据自动调整参数、版本号
- 📊 **模式学习**：分析数据趋势，生成洞察

## 架构

```
┌─────────────────────────────────────────────────┐
│              GitHub Actions (Cloud)               │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐ │
│  │ Position │  │ Learning │  │ Self-Growth   │ │
│  │ Data     │→ │ Loop     │→ │ (Config/Bump) │ │
│  │ Fetcher  │  │          │  │               │ │
│  └──────────┘  └──────────┘  └───────────────┘ │
│       ↓              ↓               ↓           │
│  ┌──────────────────────────────────────────┐   │
│  │     Memory Bank (SQLite) - Auto Commit   │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## 使用方式

1. 将项目推送到 GitHub 仓库
2. GitHub Actions 自动每小时运行
3. Agent 自行采集数据、学习、进化
4. 所有增长自动 commit 回仓库

## 本地测试

```bash
pip install requests
python src/engine.py
```
"""
    with open(SKILL_DIR / "SKILL.md", 'w', encoding='utf-8') as f:
        f.write(skill_md)

    # 复制核心文件
    src_dir = BASE_DIR / "src"
    for f in src_dir.glob("*.py"):
        shutil.copy2(f, SKILL_DIR / f.name)

    # 创建 skill.json
    skill_json = {
        "name": SKILL_NAME,
        "version": "1.0.0",
        "description": "Autonomous self-growing agent with cloud execution",
        "author": "CodeBuddy",
        "triggers": ["autonomous", "self-growing", "agent", "自动运行", "自循环"],
        "entry": "src/engine.py",
        "runtime": "python"
    }
    with open(SKILL_DIR / "skill.json", 'w', encoding='utf-8') as f:
        json.dump(skill_json, f, indent=2, ensure_ascii=False)

    print(f"✅ Skill '{SKILL_NAME}' installed to {SKILL_DIR}")


if __name__ == "__main__":
    create_skill()

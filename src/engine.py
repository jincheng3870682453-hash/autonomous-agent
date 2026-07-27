"""
Autonomous Self-Growing Agent Engine
自循环自主增长代理引擎

架构：
  ┌─────────────────────────────────────────────────┐
  │                 Cloud Runner                      │
  │  ┌──────────┐  ┌──────────┐  ┌───────────────┐ │
  │  │ Position │  │ Learning │  │ Self-Growth   │ │
  │  │ Data     │→ │ Loop     │→ │ (Code/Config) │ │
  │  │ Fetcher  │  │          │  │               │ │
  │  └──────────┘  └──────────┘  └───────────────┘ │
  │       ↓              ↓               ↓           │
  │  ┌──────────────────────────────────────────┐   │
  │  │         Memory Bank (JSON/SQLite)         │   │
  │  └──────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────┘
"""

import json
import os
import time
import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
import logging

# ============================================================
# 配置
# ============================================================
BASE_DIR = Path(__file__).parent.parent
MEMORY_DIR = BASE_DIR / "memory"
DATA_DIR = BASE_DIR / "data"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AutonomousAgent")


class MemoryBank:
    """记忆银行 - 持久化存储所有学习到的知识"""

    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self.db_path = MEMORY_DIR / "memory.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    source TEXT DEFAULT 'self',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    UNIQUE(category, key)
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS growth_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    detail TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category);
                CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
            """)

    def remember(self, category: str, key: str, value: Any, confidence: float = 1.0, source: str = "self"):
        """存储一条知识"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO knowledge (category, key, value, confidence, source, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(category, key) DO UPDATE SET
                    value = excluded.value,
                    confidence = excluded.confidence,
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP,
                    access_count = knowledge.access_count + 1
            """, (category, key, json.dumps(value), confidence, source))

    def recall(self, category: str, key: str = None) -> List[Dict]:
        """检索知识"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if key:
                rows = conn.execute(
                    "SELECT * FROM knowledge WHERE category=? AND key=? ORDER BY confidence DESC",
                    (category, key)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM knowledge WHERE category=? ORDER BY updated_at DESC",
                    (category,)
                ).fetchall()
            return [dict(r) for r in rows]

    def record_event(self, event_type: str, payload: Dict):
        """记录事件"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO events (event_type, payload) VALUES (?, ?)",
                (event_type, json.dumps(payload))
            )

    def log_growth(self, action: str, detail: str = ""):
        """记录增长行为"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO growth_log (action, detail) VALUES (?, ?)",
                (action, detail)
            )
        logger.info(f"🌱 Growth: {action} - {detail}")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        with sqlite3.connect(str(self.db_path)) as conn:
            knowledge_count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
            events_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            growth_count = conn.execute("SELECT COUNT(*) FROM growth_log").fetchone()[0]
            categories = conn.execute(
                "SELECT category, COUNT(*) as cnt FROM knowledge GROUP BY category"
            ).fetchall()
        return {
            "total_knowledge": knowledge_count,
            "total_events": events_count,
            "total_growths": growth_count,
            "categories": {c[0]: c[1] for c in categories},
            "last_updated": datetime.now().isoformat()
        }


class DataCollector:
    """数据采集器 - 从外部获取数据"""

    def __init__(self, memory: MemoryBank):
        self.memory = memory
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def fetch_location_data(self, source: str = "ip-api") -> Optional[Dict]:
        """获取位置相关数据（IP定位等）"""
        try:
            if source == "ip-api":
                resp = requests.get("http://ip-api.com/json/?fields=61439", timeout=10)
                data = resp.json()
                if data.get("status") == "success":
                    self.memory.remember(
                        "location", f"ip_{data.get('query', 'unknown')}",
                        data, source="ip-api"
                    )
                    logger.info(f"📍 Location data fetched: {data.get('city')}, {data.get('country')}")
                    return data

            elif source == "ipinfo":
                resp = requests.get("https://ipinfo.io/json", timeout=10)
                data = resp.json()
                self.memory.remember("location", "ipinfo", data, source="ipinfo")
                logger.info(f"📍 Location data fetched via ipinfo: {data.get('city')}")
                return data

        except Exception as e:
            logger.warning(f"Failed to fetch location data: {e}")
            return None

    def fetch_public_data(self, api_type: str) -> Optional[Dict]:
        """采集各类公开数据"""
        apis = {
            "time": "http://worldtimeapi.org/api/ip",
            "github_trending": "https://api.github.com/search/repositories?q=stars:>1000+pushed:>2026-01-01&sort=stars&per_page=5",
            "hackernews": "https://hacker-news.firebaseio.com/v0/topstories.json",
        }

        if api_type not in apis:
            return None

        try:
            resp = requests.get(apis[api_type], timeout=15, headers={"User-Agent": "AutonomousAgent/1.0"})
            data = resp.json()
            self.memory.remember("public_data", api_type, data, source="api")
            self.memory.record_event("data_fetch", {"api_type": api_type, "status": "success"})
            logger.info(f"📡 Public data fetched: {api_type}")
            return data
        except Exception as e:
            logger.warning(f"Failed to fetch {api_type}: {e}")
            return None

    def collect_routine(self):
        """常规数据采集流程"""
        results = {
            "location": self.fetch_location_data(),
            "time": self.fetch_public_data("time"),
        }
        self.memory.record_event("routine_collect", {
            "timestamp": datetime.now().isoformat(),
            "results": {k: "ok" if v else "fail" for k, v in results.items()}
        })
        return results


class LearningLoop:
    """学习循环 - 基于已有数据生成新的洞察"""

    def __init__(self, memory: MemoryBank):
        self.memory = memory

    def analyze_patterns(self) -> List[Dict]:
        """分析记忆库中的模式"""
        insights = []

        # 分析数据采集频率
        stats = self.memory.get_stats()
        if stats["total_events"] > 0:
            insight = {
                "type": "pattern_detected",
                "title": "Data Collection Frequency",
                "content": f"Collected {stats['total_events']} events across {len(stats['categories'])} categories",
                "confidence": min(0.9, stats['total_events'] / 100)
            }
            insights.append(insight)

        # 分析知识增长趋势
        if stats["total_growths"] > 0:
            insight = {
                "type": "growth_trend",
                "title": "Knowledge Growth",
                "content": f"Agent has grown {stats['total_growths']} times, with {stats['total_knowledge']} knowledge entries",
                "confidence": 0.8
            }
            insights.append(insight)

        for insight in insights:
            self.memory.remember(
                "insight", insight["title"].lower().replace(" ", "_"),
                insight, confidence=insight["confidence"]
            )

        return insights

    def generate_summary(self) -> str:
        """生成当前状态的摘要"""
        stats = self.memory.get_stats()
        return (
            f"🧠 Knowledge: {stats['total_knowledge']} entries\n"
            f"📊 Events: {stats['total_events']}\n"
            f"🌱 Growths: {stats['total_growths']}\n"
            f"📂 Categories: {list(stats['categories'].keys())}\n"
            f"⏰ Last Updated: {stats['last_updated']}"
        )


class SelfGrowth:
    """自我增长模块 - 根据学习结果优化自身"""

    def __init__(self, memory: MemoryBank):
        self.memory = memory
        self.config_path = BASE_DIR / "config.json"
        self._load_config()

    def _load_config(self):
        default_config = {
            "version": "1.0.0",
            "collect_interval_minutes": 60,
            "learn_interval_minutes": 30,
            "max_memory_entries": 100000,
            "apis_enabled": ["ip-api", "worldtimeapi"],
            "auto_optimize": True,
            "created_at": datetime.now().isoformat()
        }
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = default_config
            self._save_config()

    def _save_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def evolve(self) -> Dict:
        """自我进化 - 根据数据调整自身参数"""
        changes = []
        stats = self.memory.get_stats()

        # 规则1: 知识越多，采集间隔可以适当延长（减少冗余）
        if stats["total_knowledge"] > 1000 and self.config["collect_interval_minutes"] < 120:
            self.config["collect_interval_minutes"] = min(120, self.config["collect_interval_minutes"] + 10)
            changes.append(f"Adjusted collect_interval to {self.config['collect_interval_minutes']}min")

        # 规则2: 增长事件越多，学习间隔缩短（加速进化）
        if stats["total_growths"] > 50 and self.config["learn_interval_minutes"] > 15:
            self.config["learn_interval_minutes"] = max(15, self.config["learn_interval_minutes"] - 5)
            changes.append(f"Adjusted learn_interval to {self.config['learn_interval_minutes']}min")

        # 规则3: 版本号自动递增
        parts = self.config["version"].split(".")
        if len(parts) == 3:
            patch = int(parts[2]) + 1
            if patch > 99:
                patch = 0
                parts[1] = str(int(parts[1]) + 1)
            parts[2] = str(patch)
            self.config["version"] = ".".join(parts)
            changes.append(f"Version bumped to {self.config['version']}")

        self.config["last_evolved"] = datetime.now().isoformat()
        self._save_config()

        if changes:
            self.memory.log_growth("evolve", "; ".join(changes))
            self.memory.record_event("evolution", {
                "version": self.config["version"],
                "changes": changes
            })

        return {"version": self.config["version"], "changes": changes}


class AutonomousAgent:
    """自主代理 - 主控制器"""

    def __init__(self):
        self.memory = MemoryBank()
        self.collector = DataCollector(self.memory)
        self.learner = LearningLoop(self.memory)
        self.growth = SelfGrowth(self.memory)
        self.cycle_count = 0

    def run_cycle(self) -> Dict:
        """执行一个完整的自主循环"""
        self.cycle_count += 1
        logger.info(f"🔄 Starting Cycle #{self.cycle_count}")

        report = {
            "cycle": self.cycle_count,
            "timestamp": datetime.now().isoformat(),
            "stages": {}
        }

        # Stage 1: 采集数据
        logger.info("📡 Stage 1: Collecting data...")
        collect_result = self.collector.collect_routine()
        report["stages"]["collect"] = {"status": "ok", "data_points": len(collect_result)}

        # Stage 2: 学习分析
        logger.info("🧠 Stage 2: Learning...")
        insights = self.learner.analyze_patterns()
        summary = self.learner.generate_summary()
        report["stages"]["learn"] = {
            "insights_found": len(insights),
            "insights": insights
        }

        # Stage 3: 自我增长
        logger.info("🌱 Stage 3: Self-growing...")
        evolution = self.growth.evolve()
        report["stages"]["growth"] = evolution

        # Stage 4: 记录完成
        self.memory.record_event("cycle_complete", {
            "cycle": self.cycle_count,
            "summary": summary
        })
        self.memory.log_growth("cycle_complete", f"Cycle #{self.cycle_count} finished")

        # 生成报告
        report["stats"] = self.memory.get_stats()
        report["summary"] = summary

        # 保存本轮报告
        report_path = DATA_DIR / f"cycle_{self.cycle_count:04d}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Cycle #{self.cycle_count} complete! Version: {self.growth.config['version']}")
        return report


# ============================================================
# 入口
# ============================================================
def main():
    agent = AutonomousAgent()

    # 执行循环
    report = agent.run_cycle()

    # 打印摘要
    print("\n" + "=" * 50)
    print(f"  🤖 Autonomous Agent - Cycle #{report['cycle']}")
    print("=" * 50)
    print(f"  Version: {agent.growth.config['version']}")
    print(f"  Knowledge: {report['stats']['total_knowledge']} entries")
    print(f"  Insights: {report['stages']['learn']['insights_found']}")
    print(f"  Changes: {report['stages']['growth']['changes']}")
    print("=" * 50)

    return report


if __name__ == "__main__":
    main()

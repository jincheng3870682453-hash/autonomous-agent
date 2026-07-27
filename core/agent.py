"""
Autonomous Agent - Main Controller
核心控制器：整合记忆、采集、学习、增长、技能、渠道
"""
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from . import load_config, load_soul, ensure_dirs, setup_logging, get_agent_id
from .memory import MemoryBank
from .collector import DataCollector
from .learner import LearningLoop
from .growth import SelfGrowth

logger = logging.getLogger("AutonomousAgent")


class AutonomousAgent:
    """自主智能体 - 平台级主控制器"""

    def __init__(self, config_path: str = None):
        ensure_dirs()
        self.config = load_config(Path(config_path) if config_path else None)
        self.soul = load_soul()
        self.agent_id = get_agent_id()
        self.config["agent"]["id"] = self.agent_id
        self.logger = setup_logging(self.config)

        # 初始化核心模块
        mem_cfg = self.config.get("memory", {})
        self.memory = MemoryBank(
            Path(mem_cfg.get("database", "memory/memory.db")),
            fts_enabled=mem_cfg.get("fts_enabled", True),
            graph_enabled=mem_cfg.get("graph_enabled", True)
        )
        self.collector = DataCollector(self.memory, self.config)
        self.learner = LearningLoop(self.memory, self.config.get("learning"))
        self.growth = SelfGrowth(self.memory, self.config)

        # 运行时状态
        self.cycle_count = self.memory.get_stats()["cycles"]["total"]
        self.started_at = datetime.now()
        self.status = "initialized"

        logger.info(f"🤖 Agent [{self.agent_id}] initialized - v{self.config['agent']['version']}")

    def run_cycle(self) -> Dict:
        """执行一个完整的自主循环"""
        self.cycle_count += 1
        cycle_start = time.time()
        self.status = "running"

        report = {
            "cycle": self.cycle_count,
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "stages": {}
        }

        try:
            # Stage 1: 采集数据
            logger.info(f"📡 [Cycle #{self.cycle_count}] Stage 1: Collecting...")
            collect_result = self.collector.collect_all()
            success_count = sum(1 for v in collect_result.values() if v.get("status") == "ok")
            report["stages"]["collect"] = {
                "status": "ok",
                "collectors_run": len(collect_result),
                "successful": success_count,
                "details": collect_result
            }

            # Stage 2: 学习分析
            logger.info(f"🧠 [Cycle #{self.cycle_count}] Stage 2: Learning...")
            learn_result = self.learner.run()
            report["stages"]["learn"] = learn_result

            # Stage 3: 自我增长
            logger.info(f"🌱 [Cycle #{self.cycle_count}] Stage 3: Growing...")
            evolution = self.growth.evolve(learn_result.get("insights", []))
            report["stages"]["growth"] = evolution

            # Stage 4: 存档
            logger.info(f"💾 [Cycle #{self.cycle_count}] Stage 4: Archiving...")
            summary = self.learner.generate_summary()
            report["summary"] = summary
            report["stats"] = self.memory.get_stats()
            report["version"] = self.config.get("agent", {}).get("version", "1.0.0")

            duration_ms = int((time.time() - cycle_start) * 1000)
            self.memory.save_cycle_report(self.cycle_count, report, duration_ms)
            self.memory.record_event("cycle_complete", {
                "cycle": self.cycle_count,
                "duration_ms": duration_ms,
                "collectors": success_count,
                "insights": learn_result.get("insights_generated", 0),
                "changes": len(evolution.get("changes", []))
            })
            self.memory.log_growth("cycle_complete", "cycle", 
                f"Cycle #{self.cycle_count} finished in {duration_ms}ms")

            # 保存数据快照
            snapshot_path = Path("data") / f"cycle_{self.cycle_count:04d}.json"
            with open(snapshot_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            self.status = "idle"
            report["duration_ms"] = duration_ms
            report["status"] = "completed"

            logger.info(f"✅ Cycle #{self.cycle_count} complete! "
                       f"v{self.config['agent']['version']} | "
                       f"{duration_ms}ms | "
                       f"{len(evolution.get('changes', []))} changes")

        except Exception as e:
            self.status = "error"
            duration_ms = int((time.time() - cycle_start) * 1000)
            logger.error(f"❌ Cycle #{self.cycle_count} failed: {e}")
            self.memory.record_event("cycle_error", {
                "cycle": self.cycle_count,
                "error": str(e),
                "duration_ms": duration_ms
            }, severity="error")
            report["status"] = "error"
            report["error"] = str(e)
            report["duration_ms"] = duration_ms

        return report

    def get_status(self) -> Dict:
        """获取 Agent 完整状态"""
        return {
            "agent_id": self.agent_id,
            "version": self.config["agent"]["version"],
            "status": self.status,
            "cycle_count": self.cycle_count,
            "uptime_seconds": int((datetime.now() - self.started_at).total_seconds()),
            "started_at": self.started_at.isoformat(),
            "stats": self.memory.get_stats(),
            "collector_health": self.collector.get_health(),
            "recent_growth": self.memory.get_recent_growth(5),
            "recent_cycles": self.memory.get_cycle_history(5),
            "config_summary": {
                "cycle_interval": self.config.get("runtime", {}).get("cycle_interval"),
                "collectors_enabled": [
                    name for name, cfg in self.config.get("collectors", {}).items()
                    if cfg.get("enabled")
                ],
                "llm_enabled": self.config.get("llm", {}).get("enabled", False),
                "channels_enabled": [
                    name for name, cfg in self.config.get("channels", {}).items()
                    if cfg.get("enabled")
                ]
            }
        }

    def __repr__(self):
        return f"<AutonomousAgent id={self.agent_id} v{self.config['agent']['version']} cycles={self.cycle_count}>"

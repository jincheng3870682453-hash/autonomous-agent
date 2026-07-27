"""
Self Growth - 自我增长模块
参数调优 + 版本管理 + 策略进化 + 自我修复
"""
import json
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..memory import MemoryBank

logger = logging.getLogger("AutonomousAgent.Growth")


class ParamTuner:
    """参数自动调优器"""

    def __init__(self, memory: MemoryBank, config: Dict = None):
        self.memory = memory
        self.config = config or {}
        self.learning_rate = self.config.get("learning_rate", 0.1)
        self.learning_rate_step = self.config.get("learning_rate_step", 0.05)
        self.max_learning_rate = self.config.get("max_learning_rate", 1.0)

    def tune(self, insights: List[Dict], full_config: Dict) -> List[str]:
        """根据洞察自动调整参数"""
        changes = []
        stats = self.memory.get_stats()

        # 规则1: 知识快速增长 → 提高学习率
        if stats["knowledge"]["total"] > 1000 and self.learning_rate < self.max_learning_rate:
            old_lr = self.learning_rate
            self.learning_rate = min(self.max_learning_rate, self.learning_rate + self.learning_rate_step)
            changes.append(f"learning_rate: {old_lr} → {self.learning_rate}")

        # 规则2: 错误率高 → 增加采集超时
        for insight in insights:
            if insight.get("source") == "high_error_rate":
                current_timeout = full_config.get("collectors", {}).get("location", {}).get("timeout", 10)
                new_timeout = current_timeout + 5
                if "collectors" not in full_config:
                    full_config["collectors"] = {}
                if "location" not in full_config["collectors"]:
                    full_config["collectors"]["location"] = {}
                full_config["collectors"]["location"]["timeout"] = new_timeout
                changes.append(f"location_timeout: {current_timeout}s → {new_timeout}s (due to errors)")

        # 规则3: 长时间运行 → 启用自动归档
        if stats["cycles"]["total"] > 100:
            if not full_config.get("memory", {}).get("auto_archive_cycles"):
                full_config["memory"]["auto_archive_cycles"] = 100
                changes.append("Enabled auto-archive (100 cycles)")

        # 规则4: 图节点多 → 可以考虑启用 LLM 增强
        graph_nodes = stats.get("graph", {}).get("nodes", 0)
        if graph_nodes > 50 and not full_config.get("llm", {}).get("enabled"):
            changes.append("Consider enabling LLM for richer insights (graph: {graph_nodes} nodes)")

        return changes


class VersionManager:
    """版本管理器"""

    def __init__(self, config: Dict = None):
        self.config = config or {}

    def bump(self, change_type: str = "patch") -> str:
        """版本号递增"""
        version = self.config.get("agent", {}).get("version", "1.0.0")
        parts = version.split(".")
        
        if change_type == "major":
            parts[0] = str(int(parts[0]) + 1)
            parts[1] = "0"
            parts[2] = "0"
        elif change_type == "minor":
            parts[1] = str(int(parts[1]) + 1)
            parts[2] = "0"
        else:  # patch
            parts[2] = str(int(parts[2]) + 1)

        new_version = ".".join(parts)
        self.config["agent"]["version"] = new_version
        logger.info(f"📦 Version: {version} → {new_version}")
        return new_version

    def determine_bump_type(self, insights: List[Dict], changes: List[str]) -> str:
        """根据变化量决定版本类型"""
        if not changes:
            return None
        has_major = any("major" in c.lower() or "breaking" in c.lower() for c in changes)
        has_feature = len(changes) > 2
        if has_major:
            return "major"
        elif has_feature:
            return "minor"
        return "patch"


class StrategyEvolver:
    """策略进化器 - 让 Agent 学会更好的采集/学习策略"""

    def __init__(self, memory: MemoryBank, config: Dict = None):
        self.memory = memory
        self.config = config or {}

    def evolve(self) -> List[str]:
        """进化采集和学习策略"""
        changes = []
        
        # 分析哪些采集器最有效
        stats = self.memory.get_stats()
        categories = stats["knowledge"].get("categories", {})
        
        # 如果某个类别数据太少，考虑增加采集
        if "weather" not in categories:
            changes.append("Weather data not yet collected - consider enabling weather collector")

        # 如果洞察置信度普遍偏低，降低 min_confidence 阈值
        recent_insights = self.memory.recall("insight", limit=10)
        if recent_insights:
            avg_conf = sum(i.get("confidence", 0) for i in recent_insights) / len(recent_insights)
            if avg_conf < 0.5:
                changes.append(f"Low insight confidence ({avg_conf:.2f}) - consider adjusting thresholds")

        return changes


class SelfHealer:
    """自我修复器"""

    def __init__(self, memory: MemoryBank, config: Dict = None):
        self.memory = memory
        self.config = config or {}
        self.max_failures = self.config.get("health", {}).get("max_consecutive_failures", 3)

    def diagnose(self) -> List[Dict]:
        """诊断系统问题"""
        issues = []
        
        # 检查数据库完整性
        try:
            import sqlite3
            conn = sqlite3.connect(str(self.memory.db_path))
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                issues.append({"component": "database", "issue": result[0], "severity": "critical"})
            conn.close()
        except Exception as e:
            issues.append({"component": "database", "issue": str(e), "severity": "critical"})

        # 检查最近的失败
        stats = self.memory.get_stats()
        recent_errors = stats["events"].get("recent_24h", {}).get("collect_error", 0)
        if recent_errors >= self.max_failures:
            issues.append({
                "component": "collector",
                "issue": f"{recent_errors} collection errors in 24h",
                "severity": "high"
            })

        return issues

    def heal(self, issues: List[Dict]) -> List[str]:
        """尝试修复检测到的问题"""
        fixes = []
        for issue in issues:
            if issue["component"] == "database" and issue["severity"] == "critical":
                # 尝试数据库恢复
                try:
                    import sqlite3
                    conn = sqlite3.connect(str(self.memory.db_path))
                    conn.execute("PRAGMA integrity_check")
                    conn.execute("REINDEX")
                    conn.close()
                    fixes.append("Database reindexed")
                except Exception as e:
                    fixes.append(f"Database recovery failed: {e}")
                    # 备份并重建
                    backup_path = self.memory.db_path.with_suffix(".db.bak")
                    self.memory.db_path.rename(backup_path)
                    self.memory._init_db()
                    fixes.append(f"Database rebuilt from scratch (old DB saved as {backup_path.name})")

        return fixes


class SelfGrowth:
    """自我增长管理器"""

    def __init__(self, memory: MemoryBank, config: Dict = None):
        self.memory = memory
        self.config = config or {}
        self.tuner = ParamTuner(memory, config.get("growth"))
        self.version_mgr = VersionManager(config)
        self.strategist = StrategyEvolver(memory, config.get("growth"))
        self.healer = SelfHealer(memory, config)

    def evolve(self, insights: List[Dict]) -> Dict:
        """执行完整的自我进化循环"""
        all_changes = []
        config_changes = {}

        # 1. 自我修复检查
        if self.config.get("growth", {}).get("self_healing", True):
            issues = self.healer.diagnose()
            if issues:
                logger.warning(f"🔧 Found {len(issues)} issues")
                fixes = self.healer.heal(issues)
                all_changes.extend(fixes)
                self.memory.log_growth("self_heal", "healing", "; ".join(fixes))

        # 2. 参数调优
        if self.config.get("growth", {}).get("auto_tune", True):
            tune_changes = self.tuner.tune(insights, self.config)
            all_changes.extend(tune_changes)

        # 3. 策略进化
        if self.config.get("growth", {}).get("strategy_evolution", True):
            strategy_changes = self.strategist.evolve()
            all_changes.extend(strategy_changes)

        # 4. 版本号递增
        new_version = None
        if self.config.get("growth", {}).get("version_bump", True):
            bump_type = self.version_mgr.determine_bump_type(insights, all_changes)
            if bump_type:
                new_version = self.version_mgr.bump(bump_type)

        # 5. 记录增长
        if all_changes:
            self.memory.log_growth(
                "evolve", "evolution",
                "; ".join(all_changes),
                {"version": new_version, "change_count": len(all_changes)}
            )
            self.memory.record_event("evolution", {
                "version": new_version,
                "changes": all_changes
            })

        # 6. 保存配置
        self._save_config()

        return {
            "version": new_version or self.config.get("agent", {}).get("version"),
            "changes": all_changes,
            "change_count": len(all_changes)
        }

    def _save_config(self):
        """保存配置到 YAML 文件"""
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

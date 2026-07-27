"""
Learning Loop - 学习循环模块
模式检测 + 异常检测 + 预测 + 洞察生成
"""
import json
import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import statistics

from ..memory import MemoryBank

logger = logging.getLogger("AutonomousAgent.Learner")


class PatternDetector:
    """模式检测器"""

    def __init__(self, memory: MemoryBank, config: Dict = None):
        self.memory = memory
        self.config = config or {}
        self.min_data_points = self.config.get("min_data_points", 5)
        self.window_size = self.config.get("window_size", 100)

    def detect(self) -> List[Dict]:
        """检测数据中的模式"""
        patterns = []
        
        # 1. 检测类别分布模式
        stats = self.memory.get_stats()
        categories = stats["knowledge"].get("categories", {})
        if len(categories) > 1:
            total = sum(categories.values())
            dominant = max(categories.items(), key=lambda x: x[1])
            if dominant[1] / total > 0.5:
                patterns.append({
                    "type": "category_dominance",
                    "title": "Knowledge Focus",
                    "detail": f"Category '{dominant[0]}' dominates with {dominant[1]}/{total} entries ({dominant[1]/total*100:.1f}%)",
                    "confidence": min(0.9, dominant[1] / total)
                })

        # 2. 检测采集频率模式
        recent_events = stats["events"].get("recent_24h", {})
        if recent_events:
            total_events = sum(recent_events.values())
            patterns.append({
                "type": "activity_pattern",
                "title": "24h Activity",
                "detail": f"{total_events} events in last 24h across {len(recent_events)} types",
                "confidence": min(0.8, total_events / 50)
            })

        # 3. 检测增长趋势
        if stats["growth"]["total"] > self.min_data_points:
            patterns.append({
                "type": "growth_momentum",
                "title": "Growth Momentum",
                "detail": f"Agent has grown {stats['growth']['total']} times",
                "confidence": 0.85
            })

        # 4. 知识图谱分析
        graph = stats.get("graph", {})
        if graph.get("nodes", 0) > 0:
            patterns.append({
                "type": "graph_structure",
                "title": "Knowledge Graph",
                "detail": f"{graph['nodes']} nodes, {graph['edges']} edges, density={graph['density']}",
                "confidence": 0.7
            })

        return patterns


class AnomalyDetector:
    """异常检测器"""

    def __init__(self, memory: MemoryBank, config: Dict = None):
        self.memory = memory
        self.config = config or {}
        self.threshold = self.config.get("threshold", 2.0)

    def detect(self) -> List[Dict]:
        """检测异常"""
        anomalies = []
        
        # 检查最近的错误率
        with __import__('sqlite3').connect(str(self.memory.db_path)) as conn:
            error_count = conn.execute(
                "SELECT COUNT(*) FROM events WHERE severity='error' AND created_at > datetime('now', '-1 hour')"
            ).fetchone()[0]
            success_count = conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type='collect_success' AND created_at > datetime('now', '-1 hour')"
            ).fetchone()[0]
            total = error_count + success_count
            if total > 0 and error_count / total > 0.5:
                anomalies.append({
                    "type": "high_error_rate",
                    "title": "High Error Rate",
                    "detail": f"{error_count}/{total} operations failed in last hour ({error_count/total*100:.1f}%)",
                    "severity": "high",
                    "suggestion": "Check API connectivity and rate limits"
                })

            # 检查是否有连续空数据
            recent_collects = conn.execute("""
                SELECT payload FROM events 
                WHERE event_type='collect_empty' 
                AND created_at > datetime('now', '-2 hours')
                ORDER BY created_at DESC
            """).fetchall()
            if len(recent_collects) >= 3:
                anomalies.append({
                    "type": "empty_collections",
                    "title": "Empty Collections",
                    "detail": f"{len(recent_collects)} consecutive empty collections",
                    "severity": "medium",
                    "suggestion": "Data sources may be unavailable"
                })

        return anomalies


class InsightGenerator:
    """洞察生成器"""

    def __init__(self, memory: MemoryBank, config: Dict = None):
        self.memory = memory
        self.config = config or {}
        self.min_confidence = self.config.get("min_confidence", 0.6)

    def generate(self, patterns: List[Dict], anomalies: List[Dict]) -> List[Dict]:
        """基于模式和异常生成洞察"""
        insights = []

        for pattern in patterns:
            if pattern["confidence"] >= self.min_confidence:
                insight = {
                    "type": "insight",
                    "title": pattern.get("title", "Pattern Insight"),
                    "content": pattern.get("detail", ""),
                    "confidence": pattern["confidence"],
                    "source": pattern["type"],
                    "actionable": self._is_actionable(pattern)
                }
                insights.append(insight)
                self.memory.remember("insight", pattern["type"], insight, confidence=pattern["confidence"])

        for anomaly in anomalies:
            insight = {
                "type": "warning",
                "title": anomaly.get("title", "Anomaly Detected"),
                "content": f"{anomaly.get('detail', '')}. Suggestion: {anomaly.get('suggestion', 'Investigate.')}",
                "confidence": 0.9,
                "source": anomaly["type"],
                "severity": anomaly.get("severity", "low"),
                "actionable": True
            }
            insights.append(insight)
            self.memory.remember("insight", anomaly["type"], insight, confidence=0.9)

        return insights

    def _is_actionable(self, pattern: Dict) -> bool:
        """判断模式是否可采取行动"""
        actionable_types = ["high_error_rate", "empty_collections", "growth_momentum"]
        return pattern.get("type") in actionable_types


class LearningLoop:
    """学习循环 - 整合模式检测、异常检测、洞察生成"""

    def __init__(self, memory: MemoryBank, config: Dict = None):
        self.memory = memory
        self.config = config or {}
        self.pattern_detector = PatternDetector(memory, config.get("pattern_detection"))
        self.anomaly_detector = AnomalyDetector(memory, config.get("anomaly_detection"))
        self.insight_generator = InsightGenerator(memory, config.get("insight_generation"))

    def run(self) -> Dict:
        """执行完整学习循环"""
        # 1. 模式检测
        patterns = self.pattern_detector.detect()
        logger.info(f"🔍 Detected {len(patterns)} patterns")

        # 2. 异常检测
        anomalies = self.anomaly_detector.detect()
        if anomalies:
            logger.warning(f"⚠️ Detected {len(anomalies)} anomalies")

        # 3. 洞察生成
        insights = self.insight_generator.generate(patterns, anomalies)
        logger.info(f"💡 Generated {len(insights)} insights")

        return {
            "patterns_found": len(patterns),
            "patterns": patterns,
            "anomalies_found": len(anomalies),
            "anomalies": anomalies,
            "insights_generated": len(insights),
            "insights": insights
        }

    def generate_summary(self) -> str:
        """生成当前状态摘要"""
        stats = self.memory.get_stats()
        insights = self.memory.recall("insight", limit=5)
        growth = self.memory.get_recent_growth(5)

        lines = [
            f"🧠 Knowledge: {stats['knowledge']['total']} entries in {len(stats['knowledge']['categories'])} categories",
            f"📊 Events: {stats['events']['total']} total",
            f"🌱 Growth: {stats['growth']['total']} actions",
            f"🔄 Cycles: {stats['cycles']['total']} completed",
            f"🔧 Skills: {stats['skills']['installed']} installed",
        ]

        if insights:
            latest = insights[0]
            lines.append(f"💡 Latest insight: {latest.get('title', 'N/A')}")

        if stats.get("graph", {}).get("nodes", 0) > 0:
            lines.append(f"🕸 Graph: {stats['graph']['nodes']} nodes, {stats['graph']['edges']} edges")

        return "\n".join(lines)

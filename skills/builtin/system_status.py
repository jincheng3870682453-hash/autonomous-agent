"""
内置技能: 系统状态报告
"""
import json
from pathlib import Path
from datetime import datetime


def run(memory=None, **kwargs) -> dict:
    """生成系统状态报告"""
    if memory is None:
        return {"error": "Memory bank not available"}
    
    stats = memory.get_stats()
    return {
        "skill": "system_status",
        "timestamp": datetime.now().isoformat(),
        "report": {
            "knowledge_entries": stats["knowledge"]["total"],
            "categories": len(stats["knowledge"]["categories"]),
            "events_total": stats["events"]["total"],
            "growth_actions": stats["growth"]["total"],
            "cycles_completed": stats["cycles"]["total"],
            "graph_nodes": stats.get("graph", {}).get("nodes", 0),
            "top_categories": dict(
                sorted(stats["knowledge"]["categories"].items(), 
                       key=lambda x: x[1], reverse=True)[:5]
            )
        }
    }

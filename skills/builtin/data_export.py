"""
内置技能: 数据导出
"""
import json
from pathlib import Path
from datetime import datetime


def run(memory=None, category: str = None, format: str = "json", **kwargs) -> dict:
    """导出记忆数据"""
    if memory is None:
        return {"error": "Memory bank not available"}
    
    data = memory.recall(category=category, limit=1000)
    
    export_path = Path("data") / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    return {
        "skill": "data_export",
        "category": category or "all",
        "records": len(data),
        "exported_to": str(export_path),
        "timestamp": datetime.now().isoformat()
    }

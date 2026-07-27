"""
Autonomous Agent - Core Engine
自循环进化智能体 - 核心引擎
"""

from pathlib import Path
import yaml
import json
import uuid
import logging
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).parent.parent
MEMORY_DIR = BASE_DIR / "memory"
DATA_DIR = BASE_DIR / "data"
SKILLS_DIR = BASE_DIR / "skills"


def load_config(config_path: Path = None) -> Dict[str, Any]:
    """加载 YAML 配置文件"""
    if config_path is None:
        config_path = BASE_DIR / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_soul(soul_path: Path = None) -> Dict[str, Any]:
    """加载 Agent 灵魂文件"""
    if soul_path is None:
        soul_path = BASE_DIR / "agent.json"
    with open(soul_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def ensure_dirs():
    """确保所有运行时目录存在"""
    for d in [MEMORY_DIR, DATA_DIR, SKILLS_DIR / "installed"]:
        d.mkdir(parents=True, exist_ok=True)


def setup_logging(config: Dict[str, Any]):
    """配置日志系统"""
    level = getattr(logging, config.get("agent", {}).get("log_level", "INFO"))
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(BASE_DIR / "agent.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("AutonomousAgent")


def get_agent_id() -> str:
    """获取或生成 Agent 唯一 ID"""
    id_file = MEMORY_DIR / "agent_id.txt"
    if id_file.exists():
        return id_file.read_text().strip()
    agent_id = str(uuid.uuid4())[:8]
    id_file.write_text(agent_id)
    return agent_id

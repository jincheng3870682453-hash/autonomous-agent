"""
Multi-Channel Gateway - 多渠道网关
CLI + Telegram + Discord
"""
import sys
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("AutonomousAgent.Channel")


class BaseChannel(ABC):
    """渠道基类"""
    
    def __init__(self, agent=None, config: Dict = None):
        self.agent = agent
        self.config = config or {}

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    def format_response(self, data: Any) -> str:
        """格式化响应"""
        if isinstance(data, dict):
            return json.dumps(data, indent=2, ensure_ascii=False)
        return str(data)


class CLIChannel(BaseChannel):
    """命令行交互渠道"""

    def __init__(self, agent=None, config: Dict = None):
        super().__init__(agent, config)
        self.commands = {
            "status": self._cmd_status,
            "stats": self._cmd_stats,
            "cycle": self._cmd_cycle,
            "skills": self._cmd_skills,
            "memory": self._cmd_memory,
            "growth": self._cmd_growth,
            "summary": self._cmd_summary,
            "help": self._cmd_help,
            "exit": None,
            "quit": None,
        }

    def start(self):
        """启动 CLI 交互循环"""
        print("\n" + "=" * 60)
        print(f"  🧬 Autonomous Agent CLI")
        print(f"  Agent ID: {self.agent.agent_id if self.agent else 'N/A'}")
        print(f"  Type 'help' for commands, 'exit' to quit")
        print("=" * 60)

        while True:
            try:
                cmd = input("\n🤖 > ").strip().lower()
                if not cmd:
                    continue
                if cmd in ("exit", "quit"):
                    print("👋 Goodbye!")
                    break
                
                handler = self.commands.get(cmd)
                if handler:
                    result = handler()
                    if result:
                        print(result)
                else:
                    print(f"Unknown command: {cmd}. Type 'help' for available commands.")
            
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    def stop(self):
        pass

    def _cmd_status(self) -> str:
        if not self.agent:
            return "Agent not initialized"
        status = self.agent.get_status()
        lines = [
            f"🆔 Agent: {status['agent_id']}",
            f"📦 Version: {status['version']}",
            f"🔵 Status: {status['status']}",
            f"🔄 Cycles: {status['cycle_count']}",
            f"⏱ Uptime: {status['uptime_seconds']}s",
        ]
        return "\n".join(lines)

    def _cmd_stats(self) -> str:
        if not self.agent:
            return "Agent not initialized"
        stats = self.agent.memory.get_stats()
        lines = [
            f"🧠 Knowledge: {stats['knowledge']['total']} entries",
            f"📊 Events: {stats['events']['total']}",
            f"🌱 Growths: {stats['growth']['total']}",
            f"🔄 Cycles: {stats['cycles']['total']}",
            f"🔧 Skills: {stats['skills']['installed']}",
            f"🕸 Graph: {stats['graph'].get('nodes', 0)} nodes, {stats['graph'].get('edges', 0)} edges",
        ]
        return "\n".join(lines)

    def _cmd_cycle(self) -> str:
        if not self.agent:
            return "Agent not initialized"
        result = self.agent.run_cycle()
        return f"✅ Cycle #{result['cycle']} complete in {result['duration_ms']}ms\n{result.get('summary', '')}"

    def _cmd_skills(self) -> str:
        try:
            from skills import SkillManager
            mgr = SkillManager(self.agent.memory if self.agent else None)
            skills = mgr.get_available_skills()
            installed = skills.get("installed", [])
            if not installed:
                return "No skills installed"
            lines = [f"📦 {len(installed)} skills installed:"]
            for s in installed:
                lines.append(f"  • {s['name']} v{s['version']} - {s.get('description', '')}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    def _cmd_memory(self) -> str:
        if not self.agent:
            return "Agent not initialized"
        recent = self.agent.memory.recall(limit=10)
        lines = [f"🧠 {len(recent)} recent memories:"]
        for m in recent:
            lines.append(f"  [{m['category']}] {m['key']} (conf: {m['confidence']})")
        return "\n".join(lines)

    def _cmd_growth(self) -> str:
        if not self.agent:
            return "Agent not initialized"
        growth = self.agent.memory.get_recent_growth(10)
        lines = [f"🌱 {len(growth)} recent growths:"]
        for g in growth:
            lines.append(f"  [{g['category']}] {g['action']}: {g.get('detail', '')}")
        return "\n".join(lines)

    def _cmd_summary(self) -> str:
        if not self.agent:
            return "Agent not initialized"
        return self.agent.learner.generate_summary()

    def _cmd_help(self) -> str:
        return """
Available commands:
  status   - Agent status overview
  stats    - Detailed statistics
  cycle    - Run a cycle manually
  skills   - List installed skills
  memory   - View recent memories
  growth   - View growth history
  summary  - Current state summary
  help     - This help message
  exit     - Quit CLI
"""

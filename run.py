#!/usr/bin/env python3
"""
Autonomous Agent - Entry Point
运行模式: cloud | api | cli | cycle
"""
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core import load_config, ensure_dirs, setup_logging


def main():
    parser = argparse.ArgumentParser(description="🧬 Autonomous Agent - Self-Growing AI Agent Platform")
    parser.add_argument("mode", nargs="?", default="cycle",
                        choices=["cycle", "api", "cli", "status"],
                        help="Run mode: cycle (single run), api (start server), cli (interactive), status (show status)")
    parser.add_argument("--config", "-c", default=None, help="Path to config file")
    args = parser.parse_args()

    config = load_config(Path(args.config) if args.config else None)
    ensure_dirs()
    logger = setup_logging(config)

    if args.mode == "cycle":
        # Cloud mode: single cycle
        from core.agent import AutonomousAgent
        agent = AutonomousAgent(args.config)
        report = agent.run_cycle()
        print(f"\n✅ Cycle #{report['cycle']} complete - v{report.get('version', '?')} - {report.get('duration_ms', 0)}ms")
        return 0 if report.get("status") == "completed" else 1

    elif args.mode == "api":
        # Start API server
        import uvicorn
        api_cfg = config.get("channels", {}).get("api", {})
        uvicorn.run(
            "api.server:app",
            host=api_cfg.get("host", "0.0.0.0"),
            port=api_cfg.get("port", 8000),
            reload=False
        )

    elif args.mode == "cli":
        # Interactive CLI
        from core.agent import AutonomousAgent
        from core.channel import CLIChannel
        agent = AutonomousAgent(args.config)
        cli = CLIChannel(agent)
        cli.start()

    elif args.mode == "status":
        # Show status and exit
        from core.agent import AutonomousAgent
        agent = AutonomousAgent(args.config)
        status = agent.get_status()
        print(f"🤖 Agent: {status['agent_id']}")
        print(f"📦 Version: {status['version']}")
        print(f"🔵 Status: {status['status']}")
        print(f"🔄 Cycles: {status['cycle_count']}")
        print(f"⏱ Uptime: {status['uptime_seconds']}s")
        print(f"🧠 Knowledge: {status['stats']['knowledge']['total']} entries")
        print(f"📊 Events: {status['stats']['events']['total']}")
        print(f"🌱 Growths: {status['stats']['growth']['total']}")


if __name__ == "__main__":
    sys.exit(main())

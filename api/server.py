"""
FastAPI Server - REST API for Autonomous Agent
"""
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime

from core.agent import AutonomousAgent
from core import load_config

# ---- Global State ----
agent: Optional[AutonomousAgent] = None
app = FastAPI(
    title="Autonomous Agent API",
    description="Self-growing, self-evolving AI agent platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_agent() -> AutonomousAgent:
    """Lazy init agent singleton"""
    global agent
    if agent is None:
        agent = AutonomousAgent()
    return agent


# ---- Pydantic Models ----
class CycleResponse(BaseModel):
    cycle: int
    status: str
    version: str
    duration_ms: int
    summary: str = ""

class StatusResponse(BaseModel):
    agent_id: str
    version: str
    status: str
    cycle_count: int
    uptime_seconds: int
    stats: Dict
    collector_health: List[Dict]
    recent_growth: List[Dict]

class MemoryQuery(BaseModel):
    query: str
    limit: int = 20

class SkillInstallRequest(BaseModel):
    name_or_url: str


# ---- Agent Routes ----
@app.get("/")
async def root():
    """根路径重定向到 Dashboard"""
    return RedirectResponse(url="/dashboard/index.html")

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """获取 Agent 完整状态"""
    return get_agent().get_status()

@app.post("/api/cycle", response_model=CycleResponse)
async def run_cycle():
    """手动触发一次循环"""
    result = get_agent().run_cycle()
    return result

@app.get("/api/cycles")
async def get_cycles(limit: int = Query(20, le=100)):
    """获取循环历史"""
    a = get_agent()
    return a.memory.get_cycle_history(limit)

@app.get("/api/summary")
async def get_summary():
    """获取当前摘要"""
    return {"summary": get_agent().learner.generate_summary()}


# ---- Memory Routes ----
@app.get("/api/memory/stats")
async def memory_stats():
    """记忆系统统计"""
    return get_agent().memory.get_stats()

@app.get("/api/memory/recall")
async def memory_recall(
    category: Optional[str] = None,
    key: Optional[str] = None,
    limit: int = Query(100, le=500),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0)
):
    """检索记忆"""
    return get_agent().memory.recall(category, key, limit, min_confidence)

@app.post("/api/memory/search")
async def memory_search(query: MemoryQuery):
    """全文搜索记忆"""
    return get_agent().memory.search(query.query, query.limit)

@app.get("/api/memory/insights")
async def memory_insights(limit: int = Query(20, le=100)):
    """获取洞察记录"""
    return get_agent().memory.recall("insight", limit=limit)


# ---- Growth Routes ----
@app.get("/api/growth/log")
async def growth_log(limit: int = Query(20, le=100)):
    """增长日志"""
    return get_agent().memory.get_recent_growth(limit)

@app.get("/api/growth/config")
async def get_config():
    """当前配置"""
    return get_agent().config


# ---- Skill Routes ----
@app.get("/api/skills")
async def list_skills():
    """列出所有技能"""
    from skills import SkillManager
    mgr = SkillManager(get_agent().memory)
    return mgr.get_available_skills()

@app.post("/api/skills/install")
async def install_skill(req: SkillInstallRequest):
    """安装技能"""
    from skills import SkillManager
    mgr = SkillManager(get_agent().memory)
    success = mgr.install_skill(req.name_or_url)
    return {"success": success, "skill": req.name_or_url}

@app.get("/api/skills/loaded")
async def loaded_skills():
    """已加载的技能"""
    from skills import SkillLoader
    loader = SkillLoader()
    return {"loaded": loader.list_loaded()}

@app.post("/api/skills/discover")
async def discover_skills(query: str = None):
    """自动发现技能"""
    from skills import SkillManager
    mgr = SkillManager(get_agent().memory)
    installed = mgr.discover_and_install(query)
    return {"installed": installed}


# ---- Health Routes ----
@app.get("/api/health")
async def health_check():
    """健康检查"""
    a = get_agent()
    return {
        "status": a.status,
        "agent_id": a.agent_id,
        "version": a.config["agent"]["version"],
        "uptime_seconds": int((datetime.now() - a.started_at).total_seconds()),
        "memory_ok": True,
        "timestamp": datetime.now().isoformat()
    }


# ---- Static Files (Frontend) ----
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=str(frontend_dir), html=True), name="dashboard")


# ---- Startup ----
@app.on_event("startup")
async def startup():
    global agent
    agent = AutonomousAgent()
    print(f"[OK] Agent [{agent.agent_id}] started via API server")
    print(f"[OK] Docs: http://localhost:8000/docs")
    print(f"[OK] Dashboard: http://localhost:8000/dashboard")


# ---- Main ----
def main():
    import uvicorn
    config = load_config()
    api_cfg = config.get("channels", {}).get("api", {})
    uvicorn.run(
        "api.server:app",
        host=api_cfg.get("host", "0.0.0.0"),
        port=api_cfg.get("port", 8000),
        reload=False
    )


if __name__ == "__main__":
    main()

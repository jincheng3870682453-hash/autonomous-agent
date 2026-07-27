"""
Memory Bank - 记忆银行 (SQLite + FTS5 + Knowledge Graph)
"""
import sqlite3
import json
import networkx as nx
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger("AutonomousAgent.Memory")


class MemoryBank:
    """三层记忆系统: SQLite + FTS5 全文搜索 + 知识图谱"""

    def __init__(self, db_path: Path, fts_enabled: bool = True, graph_enabled: bool = True):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.fts_enabled = fts_enabled
        self.graph_enabled = graph_enabled
        self.graph = nx.DiGraph() if graph_enabled else None
        self._init_db()
        self._load_graph()

    # ---- 数据库初始化 ----
    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")

            # 核心知识表
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    source TEXT DEFAULT 'self',
                    tags TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    UNIQUE(category, key)
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    source TEXT DEFAULT 'internal',
                    severity TEXT DEFAULT 'info',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS growth_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    detail TEXT,
                    metrics TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS skill_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    version TEXT,
                    status TEXT DEFAULT 'installed',
                    metadata TEXT DEFAULT '{}',
                    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS cycle_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_number INTEGER NOT NULL,
                    report TEXT NOT NULL,
                    duration_ms INTEGER,
                    status TEXT DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- 索引
                CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category);
                CREATE INDEX IF NOT EXISTS idx_knowledge_updated ON knowledge(updated_at);
                CREATE INDEX IF NOT EXISTS idx_knowledge_confidence ON knowledge(confidence);
                CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
                CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
                CREATE INDEX IF NOT EXISTS idx_growth_action ON growth_log(action);
                CREATE INDEX IF NOT EXISTS idx_cycle_number ON cycle_reports(cycle_number);
            """)

            # FTS5 全文搜索
            if self.fts_enabled:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts 
                    USING fts5(category, key, value, content=knowledge, content_rowid=id)
                """)
                # 触发器保持 FTS 同步
                conn.executescript("""
                    CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
                        INSERT INTO knowledge_fts(rowid, category, key, value) 
                        VALUES (new.id, new.category, new.key, new.value);
                    END;
                    CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
                        INSERT INTO knowledge_fts(knowledge_fts, rowid, category, key, value) 
                        VALUES ('delete', old.id, old.category, old.key, old.value);
                    END;
                    CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
                        INSERT INTO knowledge_fts(knowledge_fts, rowid, category, key, value) 
                        VALUES ('delete', old.id, old.category, old.key, old.value);
                        INSERT INTO knowledge_fts(rowid, category, key, value) 
                        VALUES (new.id, new.category, new.key, new.value);
                    END;
                """)

    # ---- 知识图谱 ----
    def _load_graph(self):
        """从数据库重建知识图谱"""
        if not self.graph_enabled:
            return
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                rows = conn.execute(
                    "SELECT category, key, tags FROM knowledge WHERE tags != ''"
                ).fetchall()
            for cat, key, tags in rows:
                self.graph.add_node(f"{cat}:{key}", category=cat)
                if tags:
                    for tag in json.loads(tags):
                        self.graph.add_node(tag, category="tag")
                        self.graph.add_edge(f"{cat}:{key}", tag, relation="tagged")
        except Exception as e:
            logger.warning(f"Failed to load graph: {e}")

    def _add_to_graph(self, category: str, key: str, tags: List[str] = None):
        """添加节点到知识图谱"""
        if not self.graph_enabled or not tags:
            return
        node_id = f"{category}:{key}"
        self.graph.add_node(node_id, category=category)
        for tag in tags:
            self.graph.add_node(tag, category="tag")
            self.graph.add_edge(node_id, tag, relation="tagged")

    # ---- CRUD 操作 ----
    def remember(self, category: str, key: str, value: Any, 
                 confidence: float = 1.0, source: str = "self", 
                 tags: List[str] = None) -> int:
        """存储一条知识"""
        tags_json = json.dumps(tags) if tags else ""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("""
                INSERT INTO knowledge (category, key, value, confidence, source, tags, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(category, key) DO UPDATE SET
                    value = excluded.value,
                    confidence = excluded.confidence,
                    source = excluded.source,
                    tags = excluded.tags,
                    updated_at = CURRENT_TIMESTAMP,
                    access_count = knowledge.access_count + 1
            """, (category, key, json.dumps(value, ensure_ascii=False), 
                  confidence, source, tags_json))
            self._add_to_graph(category, key, tags)
            return cursor.lastrowid

    def recall(self, category: str = None, key: str = None, 
               limit: int = 100, min_confidence: float = 0.0) -> List[Dict]:
        """检索知识"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM knowledge WHERE confidence >= ?"
            params = [min_confidence]
            if category:
                query += " AND category = ?"
                params.append(category)
            if key:
                query += " AND key = ?"
                params.append(key)
            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """FTS5 全文搜索"""
        if not self.fts_enabled:
            return self.recall(limit=limit)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute("""
                    SELECT k.* FROM knowledge k
                    JOIN knowledge_fts fts ON k.id = fts.rowid
                    WHERE knowledge_fts MATCH ?
                    ORDER BY rank LIMIT ?
                """, (query, limit)).fetchall()
                return [dict(r) for r in rows]
            except sqlite3.OperationalError:
                # FTS 查询语法错误时回退到 LIKE
                like_q = f"%{query}%"
                rows = conn.execute(
                    "SELECT * FROM knowledge WHERE value LIKE ? OR key LIKE ? LIMIT ?",
                    (like_q, like_q, limit)
                ).fetchall()
                return [dict(r) for r in rows]

    def get_related(self, category: str, key: str) -> List[Dict]:
        """获取知识图谱中的关联节点"""
        if not self.graph_enabled:
            return []
        node_id = f"{category}:{key}"
        if node_id not in self.graph:
            return []
        related = []
        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph.get_edge_data(node_id, neighbor)
            related.append({
                "node": neighbor,
                "relation": edge_data.get("relation", "unknown")
            })
        return related

    def record_event(self, event_type: str, payload: Dict, 
                     source: str = "internal", severity: str = "info"):
        """记录事件"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO events (event_type, payload, source, severity) VALUES (?, ?, ?, ?)",
                (event_type, json.dumps(payload, ensure_ascii=False), source, severity)
            )

    def log_growth(self, action: str, category: str = "general", 
                   detail: str = "", metrics: Dict = None):
        """记录增长行为"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO growth_log (action, category, detail, metrics) VALUES (?, ?, ?, ?)",
                (action, category, detail, json.dumps(metrics or {}, ensure_ascii=False))
            )
        logger.info(f"🌱 Growth [{category}]: {action} - {detail}")

    def save_cycle_report(self, cycle: int, report: Dict, duration_ms: int, status: str = "completed"):
        """保存循环报告"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO cycle_reports (cycle_number, report, duration_ms, status) VALUES (?, ?, ?, ?)",
                (cycle, json.dumps(report, ensure_ascii=False), duration_ms, status)
            )

    # ---- 统计与分析 ----
    def get_stats(self) -> Dict:
        """获取综合统计"""
        with sqlite3.connect(str(self.db_path)) as conn:
            knowledge_count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
            events_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            growth_count = conn.execute("SELECT COUNT(*) FROM growth_log").fetchone()[0]
            skills_count = conn.execute("SELECT COUNT(*) FROM skill_registry").fetchone()[0]
            cycles_count = conn.execute("SELECT COUNT(*) FROM cycle_reports").fetchone()[0]

            categories = conn.execute(
                "SELECT category, COUNT(*) as cnt FROM knowledge GROUP BY category ORDER BY cnt DESC"
            ).fetchall()

            # 最近24小时的事件
            recent_events = conn.execute(
                "SELECT event_type, COUNT(*) as cnt FROM events "
                "WHERE created_at > datetime('now', '-1 day') "
                "GROUP BY event_type ORDER BY cnt DESC"
            ).fetchall()

            # 知识增长趋势（最近7天）
            daily_knowledge = conn.execute("""
                SELECT date(created_at) as day, COUNT(*) as cnt 
                FROM knowledge 
                WHERE created_at > datetime('now', '-7 days')
                GROUP BY day ORDER BY day
            """).fetchall()

            # 图统计
            graph_stats = {}
            if self.graph_enabled and self.graph.number_of_nodes() > 0:
                graph_stats = {
                    "nodes": self.graph.number_of_nodes(),
                    "edges": self.graph.number_of_edges(),
                    "density": round(nx.density(self.graph), 4)
                }

        return {
            "knowledge": {"total": knowledge_count, "categories": dict(categories)},
            "events": {"total": events_count, "recent_24h": dict(recent_events)},
            "growth": {"total": growth_count},
            "skills": {"installed": skills_count},
            "cycles": {"total": cycles_count},
            "trends": {"daily_knowledge": dict(daily_knowledge)},
            "graph": graph_stats,
            "last_updated": datetime.now().isoformat()
        }

    def get_recent_growth(self, limit: int = 10) -> List[Dict]:
        """获取最近的增长记录"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM growth_log ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_cycle_history(self, limit: int = 20) -> List[Dict]:
        """获取循环历史"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT cycle_number, duration_ms, status, created_at FROM cycle_reports ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ---- 技能注册 ----
    def register_skill(self, name: str, version: str = "1.0.0", metadata: Dict = None):
        """注册一个技能"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO skill_registry (name, version, metadata) VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET version=excluded.version, metadata=excluded.metadata
            """, (name, version, json.dumps(metadata or {}, ensure_ascii=False)))

    def get_skills(self) -> List[Dict]:
        """获取所有已注册的技能"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM skill_registry ORDER BY installed_at DESC").fetchall()
            return [dict(r) for r in rows]

    def record_skill_usage(self, name: str):
        """记录技能使用"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "UPDATE skill_registry SET last_used = CURRENT_TIMESTAMP WHERE name = ?", (name,)
            )

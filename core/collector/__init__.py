"""
Data Collector - 数据采集器模块
支持多源数据采集，可插拔式架构
"""
import time
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests

from ..memory import MemoryBank

logger = logging.getLogger("AutonomousAgent.Collector")


class BaseCollector(ABC):
    """采集器基类 - 所有采集器必须实现此接口"""
    
    def __init__(self, memory: MemoryBank, config: Dict = None):
        self.memory = memory
        self.config = config or {}
        self.name = self.__class__.__name__
        self.success_count = 0
        self.failure_count = 0

    @abstractmethod
    def collect(self) -> Optional[Dict]:
        """执行采集，返回数据或 None"""
        pass

    def run(self) -> Dict:
        """带统计的采集执行"""
        start = time.time()
        try:
            data = self.collect()
            elapsed = time.time() - start
            if data:
                self.success_count += 1
                self.memory.record_event("collect_success", {
                    "collector": self.name,
                    "elapsed_ms": int(elapsed * 1000)
                })
                return {"status": "ok", "data": data, "elapsed_ms": int(elapsed * 1000)}
            else:
                self.failure_count += 1
                self.memory.record_event("collect_empty", {"collector": self.name}, severity="warning")
                return {"status": "empty", "elapsed_ms": int(elapsed * 1000)}
        except Exception as e:
            self.failure_count += 1
            elapsed = time.time() - start
            logger.error(f"Collector {self.name} failed: {e}")
            self.memory.record_event("collect_error", {
                "collector": self.name, "error": str(e)
            }, severity="error")
            return {"status": "error", "error": str(e), "elapsed_ms": int(elapsed * 1000)}

    @property
    def health(self) -> Dict:
        total = self.success_count + self.failure_count
        return {
            "name": self.name,
            "success": self.success_count,
            "failure": self.failure_count,
            "success_rate": round(self.success_count / total, 3) if total > 0 else 0
        }


class LocationCollector(BaseCollector):
    """地理位置采集器"""

    PROVIDERS = {
        "ip-api": "http://ip-api.com/json/?fields=61439",
        "ipinfo": "https://ipinfo.io/json",
    }

    def collect(self) -> Optional[Dict]:
        providers = self.config.get("providers", ["ip-api"])
        results = {}
        for provider in providers:
            url = self.PROVIDERS.get(provider)
            if not url:
                continue
            try:
                resp = requests.get(url, timeout=self.config.get("timeout", 10))
                data = resp.json()
                if provider == "ip-api" and data.get("status") != "success":
                    continue
                results[provider] = data
                self.memory.remember(
                    "location", f"ip_{data.get('query', data.get('ip', 'unknown'))}",
                    data, source=provider
                )
                logger.info(f"📍 Location: {data.get('city', '?')}, {data.get('country', '?')} [{provider}]")
            except Exception as e:
                logger.warning(f"Location provider {provider} failed: {e}")
        return results if results else None


class WeatherCollector(BaseCollector):
    """天气采集器（需要 API Key）"""
    
    def collect(self) -> Optional[Dict]:
        api_key = self.config.get("api_key")
        if not api_key:
            return None
        try:
            # OpenWeatherMap
            resp = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": self.config.get("city", "Beijing"), "appid": api_key, "units": "metric"},
                timeout=10
            )
            data = resp.json()
            if data.get("cod") == 200:
                self.memory.remember("weather", datetime.now().strftime("%Y%m%d-%H"), data, source="openweathermap")
                logger.info(f"🌤 Weather: {data['main']['temp']}°C, {data['weather'][0]['description']}")
                return data
        except Exception as e:
            logger.warning(f"Weather fetch failed: {e}")
        return None


class GitHubCollector(BaseCollector):
    """GitHub 趋势采集器"""

    def collect(self) -> Optional[Dict]:
        if not self.config.get("trending", False):
            return None
        try:
            headers = {"User-Agent": "AutonomousAgent/1.0"}
            resp = requests.get(
                "https://api.github.com/search/repositories",
                params={"q": "stars:>1000", "sort": "stars", "per_page": self.config.get("per_page", 5)},
                headers=headers, timeout=15
            )
            data = resp.json()
            repos = [{
                "name": r["full_name"],
                "stars": r["stargazers_count"],
                "description": r.get("description", ""),
                "language": r.get("language"),
                "url": r["html_url"]
            } for r in data.get("items", [])]
            
            self.memory.remember("github_trending", datetime.now().strftime("%Y%m%d-%H"), repos, source="github_api")
            logger.info(f"🐙 GitHub Trending: {len(repos)} repos fetched")
            return {"repos": repos, "total_count": data.get("total_count", 0)}
        except Exception as e:
            logger.warning(f"GitHub fetch failed: {e}")
        return None


class SystemCollector(BaseCollector):
    """自身系统状态采集器"""
    
    def collect(self) -> Optional[Dict]:
        try:
            stats = self.memory.get_stats()
            data = {
                "knowledge_total": stats["knowledge"]["total"],
                "events_total": stats["events"]["total"],
                "growth_total": stats["growth"]["total"],
                "cycles_total": stats["cycles"]["total"],
                "graph_nodes": stats["graph"].get("nodes", 0),
                "timestamp": datetime.now().isoformat()
            }
            self.memory.remember("system_status", "latest", data, source="self")
            return data
        except Exception as e:
            logger.warning(f"System collection failed: {e}")
            return None


class DataCollector:
    """数据采集管理器 - 管理所有采集器"""

    def __init__(self, memory: MemoryBank, config: Dict = None):
        self.memory = memory
        self.config = config or {}
        self.collectors: List[BaseCollector] = []
        self._setup_collectors()

    def _setup_collectors(self):
        collectors_cfg = self.config.get("collectors", {})
        
        if collectors_cfg.get("location", {}).get("enabled", True):
            self.collectors.append(LocationCollector(self.memory, collectors_cfg["location"]))
        
        if collectors_cfg.get("weather", {}).get("enabled", False):
            self.collectors.append(WeatherCollector(self.memory, collectors_cfg["weather"]))
        
        if collectors_cfg.get("github", {}).get("enabled", True):
            self.collectors.append(GitHubCollector(self.memory, collectors_cfg["github"]))
        
        if collectors_cfg.get("system", {}).get("enabled", True):
            self.collectors.append(SystemCollector(self.memory, collectors_cfg["system"]))

    def collect_all(self) -> Dict:
        """运行所有采集器"""
        results = {}
        for collector in self.collectors:
            results[collector.name] = collector.run()
        return results

    def get_health(self) -> List[Dict]:
        """获取所有采集器的健康状态"""
        return [c.health for c in self.collectors]

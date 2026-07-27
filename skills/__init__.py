"""
Skill Marketplace - 技能市场系统
注册表 + 安装器 + 热加载
"""
import json
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests

logger = logging.getLogger("AutonomousAgent.Skills")

BASE_DIR = Path(__file__).parent.parent
SKILLS_DIR = BASE_DIR / "skills"
INSTALLED_DIR = SKILLS_DIR / "installed"
BUILTIN_DIR = SKILLS_DIR / "builtin"
REGISTRY_PATH = SKILLS_DIR / "registry.json"


class SkillRegistry:
    """技能注册表 - 管理本地和远程技能索引"""

    def __init__(self):
        self.local_skills: Dict[str, Dict] = {}
        self.remote_skills: Dict[str, Dict] = {}
        self._load_local()

    def _load_local(self):
        """加载本地技能注册表"""
        if REGISTRY_PATH.exists():
            with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.local_skills = {s["name"]: s for s in data.get("skills", [])}

    def _save_local(self):
        """保存本地技能注册表"""
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REGISTRY_PATH, 'w', encoding='utf-8') as f:
            json.dump({"skills": list(self.local_skills.values())}, f, indent=2, ensure_ascii=False)

    def register_local(self, name: str, version: str, description: str, 
                       author: str = "self", path: str = None, **kwargs):
        """注册一个本地技能"""
        skill_info = {
            "name": name,
            "version": version,
            "description": description,
            "author": author,
            "path": path or f"skills/installed/{name}",
            "installed_at": __import__('datetime').datetime.now().isoformat(),
            **kwargs
        }
        self.local_skills[name] = skill_info
        self._save_local()
        logger.info(f"📋 Registered skill: {name} v{version}")

    def unregister(self, name: str):
        """注销技能"""
        if name in self.local_skills:
            del self.local_skills[name]
            self._save_local()
            logger.info(f"🗑 Unregistered skill: {name}")

    def get_skill(self, name: str) -> Optional[Dict]:
        """获取技能信息"""
        return self.local_skills.get(name)

    def list_skills(self) -> List[Dict]:
        """列出所有本地技能"""
        return list(self.local_skills.values())

    def fetch_remote_registry(self, url: str = None) -> List[Dict]:
        """从远程拉取技能注册表"""
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            self.remote_skills = {s["name"]: s for s in data.get("skills", [])}
            logger.info(f"🌐 Fetched {len(self.remote_skills)} remote skills")
            return list(self.remote_skills.values())
        except Exception as e:
            logger.warning(f"Failed to fetch remote registry: {e}")
            return []

    def search(self, query: str) -> List[Dict]:
        """搜索技能（本地+远程）"""
        results = []
        query_lower = query.lower()
        for name, skill in {**self.local_skills, **self.remote_skills}.items():
            if (query_lower in name.lower() or 
                query_lower in skill.get("description", "").lower() or
                query_lower in " ".join(skill.get("tags", []))):
                results.append(skill)
        return results


class SkillInstaller:
    """技能安装器 - 从 GitHub 拉取和安装技能"""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        INSTALLED_DIR.mkdir(parents=True, exist_ok=True)

    def install_from_github(self, repo_url: str, skill_name: str = None) -> bool:
        """从 GitHub 仓库安装技能"""
        import subprocess
        import shutil

        if not skill_name:
            skill_name = repo_url.rstrip("/").split("/")[-1]

        target_dir = INSTALLED_DIR / skill_name
        if target_dir.exists():
            logger.info(f"Skill '{skill_name}' already installed, updating...")
            shutil.rmtree(target_dir)

        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(target_dir)],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                logger.error(f"Failed to clone {repo_url}: {result.stderr}")
                return False

            # 查找 skill.json 或 SKILL.md
            skill_json = target_dir / "skill.json"
            if skill_json.exists():
                with open(skill_json, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                self.registry.register_local(
                    name=info.get("name", skill_name),
                    version=info.get("version", "1.0.0"),
                    description=info.get("description", ""),
                    author=info.get("author", repo_url.split("/")[-2]),
                    path=str(target_dir),
                    **{k: v for k, v in info.items() if k not in ["name", "version", "description", "author"]}
                )
            else:
                self.registry.register_local(
                    name=skill_name,
                    version="1.0.0",
                    description=f"Installed from {repo_url}",
                    author=repo_url.split("/")[-2],
                    path=str(target_dir)
                )

            logger.info(f"✅ Installed skill: {skill_name} from {repo_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to install skill '{skill_name}': {e}")
            return False

    def install_from_local(self, source_dir: Path, skill_name: str = None) -> bool:
        """从本地目录安装技能"""
        import shutil
        if not source_dir.exists():
            return False
        if not skill_name:
            skill_name = source_dir.name
        target_dir = INSTALLED_DIR / skill_name
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)
        self.registry.register_local(
            name=skill_name, version="1.0.0",
            description=f"Local skill: {skill_name}",
            path=str(target_dir)
        )
        return True

    def uninstall(self, skill_name: str) -> bool:
        """卸载技能"""
        import shutil
        target_dir = INSTALLED_DIR / skill_name
        if target_dir.exists():
            shutil.rmtree(target_dir)
        self.registry.unregister(skill_name)
        logger.info(f"🗑 Uninstalled skill: {skill_name}")
        return True


class SkillLoader:
    """技能热加载器 - 动态导入技能模块"""

    def __init__(self):
        self.loaded_modules: Dict[str, Any] = {}

    def load(self, skill_name: str, skill_path: Path = None) -> Optional[Any]:
        """热加载一个技能模块"""
        if skill_name in self.loaded_modules:
            return self.loaded_modules[skill_name]

        if not skill_path:
            skill_path = INSTALLED_DIR / skill_name
        if not skill_path.exists():
            # 尝试内置技能
            skill_path = BUILTIN_DIR
            module_file = skill_path / f"{skill_name}.py"
        else:
            module_file = skill_path / "main.py"
            if not module_file.exists():
                module_file = skill_path / f"{skill_name}.py"

        if not module_file.exists():
            logger.warning(f"Skill module not found: {skill_name}")
            return None

        try:
            module_name = f"skills.{skill_name}"
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            self.loaded_modules[skill_name] = module
            logger.info(f"🔌 Loaded skill: {skill_name}")
            return module
        except Exception as e:
            logger.error(f"Failed to load skill '{skill_name}': {e}")
            return None

    def reload(self, skill_name: str) -> Optional[Any]:
        """重新加载技能"""
        if skill_name in self.loaded_modules:
            del self.loaded_modules[skill_name]
        if skill_name in sys.modules:
            del sys.modules[f"skills.{skill_name}"]
        return self.load(skill_name)

    def list_loaded(self) -> List[str]:
        """列出已加载的技能"""
        return list(self.loaded_modules.keys())


class SkillManager:
    """技能管理器 - 统一入口"""

    def __init__(self, memory=None):
        self.registry = SkillRegistry()
        self.installer = SkillInstaller(self.registry)
        self.loader = SkillLoader()
        self.memory = memory
        self._load_builtin_skills()

    def _load_builtin_skills(self):
        """加载内置技能"""
        if BUILTIN_DIR.exists():
            for py_file in BUILTIN_DIR.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                name = py_file.stem
                self.registry.register_local(
                    name=name, version="1.0.0",
                    description=f"Built-in skill: {name}",
                    author="system", path=str(BUILTIN_DIR)
                )

    def discover_and_install(self, query: str = None) -> List[str]:
        """自动发现并安装匹配的技能"""
        installed = []
        remote_url = "https://raw.githubusercontent.com/jincheng3870682453-hash/autonomous-agent/main/skills/registry.json"
        remote_skills = self.registry.fetch_remote_registry(remote_url)
        
        for skill in remote_skills:
            if query and query.lower() not in skill.get("name", "").lower():
                continue
            if skill["name"] not in self.registry.local_skills:
                repo = skill.get("repo_url")
                if repo:
                    success = self.installer.install_from_github(repo, skill["name"])
                    if success and self.memory:
                        self.memory.register_skill(skill["name"], skill.get("version"), skill)
                    installed.append(skill["name"])
        
        return installed

    def get_available_skills(self) -> Dict:
        """获取所有可用技能（已安装 + 远程）"""
        self.registry.fetch_remote_registry()
        return {
            "installed": self.registry.list_skills(),
            "available": list(self.registry.remote_skills.values()),
            "loaded": self.loader.list_loaded()
        }

    def install_skill(self, name_or_url: str) -> bool:
        """安装技能（自动判断来源）"""
        if name_or_url.startswith("http"):
            return self.installer.install_from_github(name_or_url)
        # 尝试从远程注册表查找
        remote = self.registry.remote_skills.get(name_or_url)
        if remote and remote.get("repo_url"):
            return self.installer.install_from_github(remote["repo_url"], name_or_url)
        return False

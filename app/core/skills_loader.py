"""
Skills System - Dynamic skill loading and management
"""
import os
import sys
import json
import ast
import inspect
import importlib.util
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any, Protocol, get_type_hints
from dataclasses import dataclass, asdict
from pathlib import Path
import aiofiles

from app.core.config import settings
from app.core.database import Skill as SkillModel
import logging

logger = logging.getLogger(__name__)


class BaseToolExecutor(Protocol):
    async def execute(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        ...
    
    def get_tool_schema(self, function_name: str) -> Dict[str, Any]:
        ...


class BaseExecutor(ABC):
    @abstractmethod
    async def execute(self, module: Any, function_name: str, *args, **kwargs) -> Any:
        pass
    
    @abstractmethod
    def get_tool_schema(self, info: SkillInfo, module: Any) -> Dict[str, Any]:
        pass


class OpenClawExecutor(BaseExecutor):
    async def execute(self, module: Any, function_name: str, *args, **kwargs) -> Any:
        func = getattr(module, function_name, None)
        if not func:
            raise ValueError(f"Function {function_name} not found")
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    def get_tool_schema(self, info: SkillInfo, module: Any) -> Dict[str, Any]:
        return {
            "type": "function", 
            "function": {
                "name": info.name, 
                "description": info.description,
                "parameters": {"type": "object", "properties": {}}
            }
        }


class MCPClientExecutor(BaseExecutor):
    async def execute(self, module: Any, function_name: str, *args, **kwargs) -> Any:
        logger.info(f"[MCP-Sandbox] Dispatching to isolated env")
        return f"[Sandbox] Ожидает реализации изоляции"

    def get_tool_schema(self, info: SkillInfo, module: Any) -> Dict[str, Any]:
        return {
            "type": "function", 
            "function": {
                "name": info.name, 
                "description": info.description, 
                "parameters": {"type": "object", "properties": {}}
            }
        }


@dataclass
class SkillInfo:
    """Skill metadata"""
    name: str
    description: str
    category: str
    source: str  # system, custom, external
    version: str = "1.0.0"
    author: str = "Unknown"
    commands: List[str] = None
    file_path: Optional[str] = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.commands is None:
            self.commands = []


class SkillLoader:
    """Dynamic skill loader and manager"""
    
    def __init__(self):
        self.skills: Dict[str, Any] = {}  # Loaded skill instances
        self.skill_info: Dict[str, SkillInfo] = {}  # Skill metadata
        self.handlers: Dict[str, Callable] = {}  # Command handlers
        self.skills_dir = Path(settings.SKILLS_DIR)
        self._native_executor = OpenClawExecutor()
        self._mcp_executor = MCPClientExecutor()
    
    async def load_all_skills(self):
        """Load all skills from skills directory"""
        logger.info("Loading skills...")
        
        # Load system skills
        system_dir = self.skills_dir / "system"
        if system_dir.exists():
            await self._load_from_directory(system_dir, "system")
        
        # Load custom skills
        custom_dir = self.skills_dir / "custom"
        if custom_dir.exists():
            await self._load_from_directory(custom_dir, "custom")
        
        # Load external skills
        external_dir = self.skills_dir / "external"
        if external_dir.exists():
            await self._load_from_directory(external_dir, "external")
        
        logger.info(f"Loaded {len(self.skills)} skills")
    
    async def _load_from_directory(self, directory: Path, source: str):
        """Load skills from a directory"""
        for file_path in directory.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
            
            try:
                await self._load_skill_file(file_path, source)
            except Exception as e:
                logger.error(f"Failed to load skill from {file_path}: {e}")
    
    async def _load_skill_file(self, file_path: Path, source: str):
        """Load a single skill file"""
        skill_name = file_path.stem
        
        # Read and validate code
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            code = await f.read()
        
        # Validate syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            return
        
        # Load module
        spec = importlib.util.spec_from_file_location(skill_name, file_path)
        module = importlib.util.module_from_spec(spec)
        
        # Add to path temporarily
        sys.path.insert(0, str(file_path.parent))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.pop(0)
        
        # Extract skill info
        info = SkillInfo(
            name=getattr(module, 'SKILL_NAME', skill_name),
            description=getattr(module, 'SKILL_DESCRIPTION', 'No description'),
            category=getattr(module, 'SKILL_CATEGORY', 'general'),
            source=source,
            version=getattr(module, 'SKILL_VERSION', '1.0.0'),
            author=getattr(module, 'SKILL_AUTHOR', 'Unknown'),
            commands=getattr(module, 'SKILL_COMMANDS', []),
            file_path=str(file_path),
            is_active=True
        )
        
        # Store skill
        self.skills[info.name] = module
        self.skill_info[info.name] = info
        
        # Register handlers if any
        if hasattr(module, 'setup_handlers'):
            try:
                handlers = module.setup_handlers()
                if handlers:
                    for command, handler in handlers.items():
                        self.handlers[command] = handler
            except Exception as e:
                logger.error(f"Failed to setup handlers for {info.name}: {e}")
        
        logger.info(f"Loaded skill: {info.name} ({source})")
    
    async def create_skill(
        self,
        name: str,
        description: str,
        code: str,
        category: str = "custom",
        author: str = "User"
    ) -> SkillInfo:
        """Create a new skill from code"""
        
        # Validate name
        if not name.replace('_', '').isalnum():
            raise ValueError("Skill name must be alphanumeric with underscores only")
        
        # Validate code syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")
        
        # Ensure directory exists
        custom_dir = self.skills_dir / "custom"
        custom_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = custom_dir / f"{name}.py"
        
        # Add metadata header if not present
        if 'SKILL_NAME' not in code:
            header = f'''"""
{description}
"""
SKILL_NAME = "{name}"
SKILL_DESCRIPTION = "{description}"
SKILL_CATEGORY = "{category}"
SKILL_VERSION = "1.0.0"
SKILL_AUTHOR = "{author}"
SKILL_COMMANDS = []

'''
            code = header + code
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(code)
        
        # Load the new skill
        await self._load_skill_file(file_path, "custom")
        
        return self.skill_info.get(name)
    
    async def update_skill(self, name: str, code: str) -> bool:
        """Update existing skill code"""
        if name not in self.skill_info:
            return False
        
        info = self.skill_info[name]
        
        # Validate code
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")
        
        # Update file
        if info.file_path:
            async with aiofiles.open(info.file_path, 'w', encoding='utf-8') as f:
                await f.write(code)
            
            # Reload skill
            await self._load_skill_file(Path(info.file_path), info.source)
            return True
        
        return False
    
    async def delete_skill(self, name: str) -> bool:
        """Delete a skill"""
        if name not in self.skill_info:
            return False
        
        info = self.skill_info[name]
        
        # Prevent deleting system skills
        if info.source == "system":
            raise ValueError("Cannot delete system skills")
        
        # Remove file
        if info.file_path and os.path.exists(info.file_path):
            os.remove(info.file_path)
        
        # Remove from memory
        del self.skills[name]
        del self.skill_info[name]
        
        # Remove handlers
        for cmd in info.commands:
            if cmd in self.handlers:
                del self.handlers[cmd]
        
        return True
    
    def get_skill(self, name: str) -> Optional[Any]:
        """Get loaded skill module"""
        return self.skills.get(name)
    
    def get_skill_info(self, name: str) -> Optional[SkillInfo]:
        """Get skill metadata"""
        return self.skill_info.get(name)
    
    def list_skills(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[SkillInfo]:
        """List skills with optional filtering"""
        skills = list(self.skill_info.values())
        
        if source:
            skills = [s for s in skills if s.source == source]
        
        if category:
            skills = [s for s in skills if s.category == category]
        
        return skills
    
    async def get_skill_code(self, name: str) -> Optional[str]:
        """Get skill source code"""
        info = self.skill_info.get(name)
        if not info or not info.file_path:
            return None
        
        try:
            async with aiofiles.open(info.file_path, 'r', encoding='utf-8') as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Failed to read skill code: {e}")
            return None
    
    async def execute_skill(
        self,
        name: str,
        function_name: str,
        *args,
        **kwargs
    ) -> Any:
        """Execute a skill function"""
        skill = self.skills.get(name)
        if not skill:
            raise ValueError(f"Skill {name} not found")
        
        info = self.skill_info.get(name)
        if not info:
            raise ValueError(f"Skill metadata for {name} not found")
        
        if info.source == "system":
            return await self._native_executor.execute(skill, function_name, *args, **kwargs)
        else:
            return await self._mcp_executor.execute(skill, function_name, *args, **kwargs)

    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        """Собирает все инструменты (MCP Tools Primitive)"""
        schemas = []
        for name, info in self.skill_info.items():
            module = self.skills.get(name)
            if info.source == "system":
                schemas.append(self._native_executor.get_tool_schema(info, module))
            else:
                schemas.append(self._mcp_executor.get_tool_schema(info, module))
        return schemas
    
    def search_skills(self, query: str) -> List[SkillInfo]:
        """Search skills by name or description"""
        query = query.lower()
        results = []
        
        for info in self.skill_info.values():
            if (query in info.name.lower() or 
                query in info.description.lower() or
                query in info.category.lower()):
                results.append(info)
        
        return results
    
    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        categories = set()
        for info in self.skill_info.values():
            categories.add(info.category)
        return sorted(list(categories))


# Global skill loader instance
skill_loader = SkillLoader()


class OpenClawExecutorDirect:
    """Нативный экзекутор для системных RAG-навыков (Zero-latency)"""
    def __init__(self, module: Any):
        self.module = module

    def get_tool_schema(self, function_name: str) -> Dict[str, Any]:
        func = getattr(self.module, function_name)
        sig = inspect.signature(func)
        hints = get_type_hints(func)
        
        schema = {
            "name": function_name,
            "description": inspect.getdoc(func) or f"System tool: {function_name}",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
        
        for name, param in sig.parameters.items():
            if name == "self": continue
            param_type = hints.get(name, str)
            
            type_name = "string"
            if param_type == int: type_name = "integer"
            elif param_type == bool: type_name = "boolean"
            elif param_type == float: type_name = "number"
            
            schema["parameters"]["properties"][name] = {"type": type_name}
            
            if param.default == inspect.Parameter.empty:
                schema["parameters"]["required"].append(name)
                
        return schema

    async def execute(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        func = getattr(self.module, function_name)
        if inspect.iscoroutinefunction(func):
            return await func(**arguments)
        return func(**arguments)


class MCPClientExecutorDirect:
    """Адаптер для вызова пользовательских навыков в изолированной песочнице (DinD/Wasmtime)"""
    def __init__(self, server_endpoint: str):
        self.endpoint = server_endpoint

    def get_tool_schema(self, function_name: str) -> Dict[str, Any]:
        return {"name": function_name, "description": "External MCP Tool", "parameters": {}}

    async def execute(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        return f"Mocked isolated execution of {function_name}"


class SkillLoaderFacade:
    def __init__(self):
        self.executors: Dict[str, BaseToolExecutor] = {}

    def register_system_skill(self, name: str, module: Any):
        self.executors[name] = OpenClawExecutorDirect(module)
        
    def register_external_skill(self, name: str, endpoint: str):
        self.executors[name] = MCPClientExecutorDirect(endpoint)

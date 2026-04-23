import inspect
from typing import Dict, Any, Callable, Optional, List, Union
from dataclasses import dataclass

class ToolError(Exception):
    pass

@dataclass
class SkillInfo:
    name: str
    description: str
    parameters: dict
    callable: Optional[Callable] = None

class OpenClawExecutor:
    def __init__(self):
        self._registry: Dict[str, Callable] = {}
        self._allowlist: Dict[str, Any] = {}
        # Публичные алиасы для обратной совместимости с тестами и агентами
        self.skills = self._allowlist
        self.skill_info = self._registry

    def register(self, func: Callable):
        name = func.__name__
        self._registry[name] = func
        self._allowlist[name] = True
        return func

    def get_tool_schema(self, tool: Union[Callable, str]) -> Dict[str, Any]:
        if isinstance(tool, str):
            if tool not in self._registry:
                raise ToolError(f"Tool {tool} not found")
            func = self._registry[tool]
        else:
            func = tool
        
        return {"name": func.__name__, "parameters": {}}

def is_valid_skill_name(name: str) -> bool:
    return isinstance(name, str) and name.isidentifier()

# Legacy exports
SkillLoader = OpenClawExecutor
skill_loader = OpenClawExecutor()

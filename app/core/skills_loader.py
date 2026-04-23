import inspect
import importlib.util
from typing import Any, Dict, Optional, Type, get_type_hints
from pydantic import BaseModel, ValidationError

class ToolError(BaseModel):
    """Унифицированный конверт ошибки выполнения (Adapter Pattern)."""
    error_code: str
    message: str
    type: str = "ExecutionError"
    ok: bool = False

class BaseExecutor:
    """Базовый контракт для всех экзекуторов MFDBA."""
    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        raise NotImplementedError

class OpenClawExecutor(BaseExecutor):
    """
    Детерминированный экзекутор (MFDBA-Lite).
    Реализует Hybrid Reflection Engine (Pydantic + inspect) и строгий Allowlist.
    """
    def __init__(self):
        self._allowlist: Dict[str, callable] = {}
        self._registry: Dict[str, Dict[str, Any]] = {}

    def register_module(self, module_path: str):
        """Изолированная загрузка навыков с отсечением приватных неймспейсов."""
        spec = importlib.util.spec_from_file_location("skill_module", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith('_'):
                self._allowlist[name] = func
                self._registry[name] = self._generate_pydantic_schema(func)

    def _generate_pydantic_schema(self, func: callable) -> Dict[str, Any]:
        """Генерация JSON Schema на базе аннотаций типов."""
        hints = get_type_hints(func)
        model_type = next((t for t in hints.values() if inspect.isclass(t) and issubclass(t, BaseModel)), None)
        
        if model_type:
            return {
                "name": func.__name__,
                "description": func.__doc__ or "System Skill",
                "parameters": model_type.model_json_schema()
            }
        
        return {"name": func.__name__, "parameters": {"type": "object", "properties": {}}}

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name not in self._allowlist:
            return ToolError(
                error_code="ACCESS_DENIED", 
                message=f"Attempt to access blocked or unregistered tool: {tool_name}"
            )

        func = self._allowlist[tool_name]
        hints = get_type_hints(func)
        model_type = next((t for t in hints.values() if inspect.isclass(t) and issubclass(t, BaseModel)), None)

        try:
            if model_type:
                validated_args = model_type(**args)
                return await func(validated_args) if inspect.iscoroutinefunction(func) else func(validated_args)
            
            return await func(**args) if inspect.iscoroutinefunction(func) else func(**args)
            
        except ValidationError as e:
            return ToolError(error_code="VALIDATION_FAILED", message=str(e), type="ValidationError")
        except Exception as e:
            return ToolError(error_code="RUNTIME_ERROR", message=str(e), type="RuntimeError")

    def get_tool_schema(self, func_name: str) -> Optional[Dict[str, Any]]:
        return self._registry.get(func_name)

    def get_all_schemas(self) -> list[Dict[str, Any]]:
        return list(self._registry.values())
from typing import Dict, Any
from app.runtime.registry import BaseInstruction
from app.runtime.builder import StepResultBuilder

class CallLLMInstruction(BaseInstruction):
    """Вызов LLM-провайдера и сохранение текстового результата."""
    
    async def execute(self, step_id: str, params: Dict[str, Any], ctx: Any) -> Any:
        result = await ctx.llm.generate(**params)
        
        # Адаптация к новой сигнатуре Tuple[str, Optional[List]]
        # Если адаптер возвращает кортеж с tool_calls, извлекаем только текст для передачи дальше
        text_response = result[0] if isinstance(result, tuple) else result
        
        return StepResultBuilder(step_id).ok(text_response)

"""
CallLLMInstruction — вызов LLM через LLMProtocol адаптер.

Params:
    prompt   (str, required)  — текст запроса
    role     (str, default="default") — роль для маппинга модели
    system   (str, optional)  — системный промпт

Output: str — текст ответа LLM
"""
import time
from typing import Dict

from app.runtime.builder import StepResultBuilder
from app.runtime.context import VMContext
from app.runtime.instructions.base import BaseInstruction


class CallLLMInstruction(BaseInstruction):
    name = "call_llm"

    async def execute(self, step_id: str, params: Dict, ctx: VMContext):
        prompt: str = params["prompt"]
        role: str = params.get("role", "default")
        system = params.get("system")

        t0 = time.monotonic()
        response_text = await ctx.llm.generate(prompt, role=role, system=system)
        latency_ms = int((time.monotonic() - t0) * 1000)

        return (
            StepResultBuilder(step_id, self.name)
            .output(response_text)
            .meta(latency_ms=latency_ms, provider="llm")
            .build()
        )

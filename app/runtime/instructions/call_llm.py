from typing import Dict
from ..builder import StepResultBuilder
from ..context import VMContext
from .base import BaseInstruction


class CallLLMInstruction(BaseInstruction):
    name = "call_llm"

    async def execute(self, step_id: str, params: Dict, ctx: VMContext):
        prompt = params["prompt"]

        response = await ctx.llm.generate(prompt)

        return (
            StepResultBuilder(step_id, self.name)
            .output(response)
            .meta(provider="llm")
            .build()
        )

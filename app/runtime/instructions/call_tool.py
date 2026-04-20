from typing import Dict
from ..builder import StepResultBuilder
from ..context import VMContext
from .base import BaseInstruction


class CallToolInstruction(BaseInstruction):
    name = "call_tool"

    async def execute(self, step_id: str, params: Dict, ctx: VMContext):
        tool_name = params["tool"]
        args = params.get("args", {})

        result = await ctx.tools.execute(tool_name, args)

        return (
            StepResultBuilder(step_id, self.name)
            .output(result)
            .build()
        )

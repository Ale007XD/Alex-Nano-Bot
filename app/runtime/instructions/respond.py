from typing import Dict
from ..builder import StepResultBuilder
from ..context import VMContext
from .base import BaseInstruction


class RespondInstruction(BaseInstruction):
    name = "respond"

    async def execute(self, step_id: str, params: Dict, ctx: VMContext):
        text = params.get("text", "")

        return (
            StepResultBuilder(step_id, self.name)
            .message(text)
            .build()
        )

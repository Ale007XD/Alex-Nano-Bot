from abc import ABC, abstractmethod
from typing import Dict

from ..context import VMContext
from ..step_result import StepResult


class BaseInstruction(ABC):
    name: str

    @abstractmethod
    async def execute(
        self,
        step_id: str,
        params: Dict,
        ctx: VMContext,
    ) -> StepResult:
        pass

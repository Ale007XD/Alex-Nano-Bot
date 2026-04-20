from typing import Dict, Type
from .instructions.base import BaseInstruction


class InstructionRegistry:
    def __init__(self):
        self._registry: Dict[str, Type[BaseInstruction]] = {}

    def register(self, name: str, cls: Type[BaseInstruction]):
        self._registry[name] = cls

    def get(self, name: str) -> Type[BaseInstruction]:
        if name not in self._registry:
            raise ValueError(f"Instruction not found: {name}")
        return self._registry[name]

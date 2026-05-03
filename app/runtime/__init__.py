"""
app/runtime — детерминированный VM-слой.

Публичный API:
    from app.runtime import ExecutionVM, InstructionRegistry, VMContext
    from app.runtime import StateContext
    from app.runtime import MultiProviderLLMAdapter, MockLLMAdapter
    from app.runtime import default_registry
"""

from app.runtime.vm import ExecutionVM, VMRunResult
from app.runtime.registry import InstructionRegistry
from app.runtime.context import VMContext
from app.runtime.state_context import StateContext, OutboxEntry, MemorySnapshot
from app.runtime.step_result import (
    StepResult,
    MemoryWrite,
    FSMTransition,
    OutboxMessage,
)
from app.runtime.builder import StepResultBuilder
from app.runtime.llm_adapter import MultiProviderLLMAdapter, MockLLMAdapter, LLMProtocol
from app.runtime.tool_registry import ToolRegistry

from app.runtime.instructions.base import BaseInstruction
from app.runtime.instructions.call_llm import CallLLMInstruction
from app.runtime.instructions.call_tool import CallToolInstruction
from app.runtime.instructions.respond import RespondInstruction
from app.runtime.instructions.store_memory import StoreMemoryInstruction


def default_registry() -> InstructionRegistry:
    """
    Создать реестр со всеми встроенными инструкциями.
    Вызывать при старте бота (bot.py) один раз.
    """
    reg = InstructionRegistry()
    reg.register("call_llm", CallLLMInstruction)
    reg.register("call_tool", CallToolInstruction)
    reg.register("respond", RespondInstruction)
    reg.register("store_memory", StoreMemoryInstruction)
    return reg


__all__ = [
    "ExecutionVM",
    "VMRunResult",
    "InstructionRegistry",
    "VMContext",
    "StateContext",
    "OutboxEntry",
    "MemorySnapshot",
    "StepResult",
    "MemoryWrite",
    "FSMTransition",
    "OutboxMessage",
    "StepResultBuilder",
    "MultiProviderLLMAdapter",
    "MockLLMAdapter",
    "LLMProtocol",
    "BaseInstruction",
    "CallLLMInstruction",
    "CallToolInstruction",
    "RespondInstruction",
    "StoreMemoryInstruction",
    "default_registry",
    "ToolRegistry",
]

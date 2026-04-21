"""
LLMAdapter — изолирует runtime от конкретной реализации MultiProviderLLMClient.

VM и instructions зависят от LLMProtocol, не от llm_client_v2.
Это позволяет:
    - тестировать VM без реального LLM (MockLLMAdapter)
    - заменить провайдер без изменения instructions
"""
from __future__ import annotations

from typing import Optional, runtime_checkable, List, Dict, Any, Tuple
from typing import Protocol


# ---------------------------------------------------------------------------
# Protocol (structural typing — не требует наследования)
# ---------------------------------------------------------------------------

@runtime_checkable
class LLMProtocol(Protocol):
    """
    Минимальный контракт LLM-адаптера для runtime.
    VM и instructions зависят только от этого протокола.
    """

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """
        Генерация ответа по prompt.

        Args:
            prompt:  пользовательский текст / инструкция шага
            system_prompt:  системный промпт (опционально)
            tools: JSON-схемы для tool calls (опционально)

        Returns:
            Кортеж (текст ответа, опциональный список tool_calls).
        """
        ...


# ---------------------------------------------------------------------------
# Конкретный адаптер для MultiProviderLLMClient
# ---------------------------------------------------------------------------

class MultiProviderLLMAdapter:
    """
    Адаптирует MultiProviderLLMClient под LLMProtocol.

    Использование:
        from app.core.llm_client_v2 import llm_client
        adapter = MultiProviderLLMAdapter(llm_client)
        ctx = VMContext(..., llm=adapter, ...)
    """

    def __init__(self, client):
        """
        Args:
            client: инстанс MultiProviderLLMClient (llm_client_v2.llm_client)
        """
        self._client = client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        from app.core.llm_client_v2 import Message

        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=prompt))

        response = await self._client.chat(
            messages=messages,
            tools=tools,
        )

        if isinstance(response, dict):
            return response.get("text", ""), response.get("tool_calls")
        return str(response), None


# ---------------------------------------------------------------------------
# Mock для тестов
# ---------------------------------------------------------------------------

class MockLLMAdapter:
    """Детерминированный адаптер для unit-тестов VM."""

    def __init__(self, fixed_response: str = "mock_response"):
        self.fixed_response = fixed_response
        self.calls: list[dict] = []

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "tools": tools})
        if tools:
            mock_tool_call = [{"name": tools[0]["name"], "arguments": {}}]
            return f"Mocked tool response to: {prompt}", mock_tool_call
        return self.fixed_response, None

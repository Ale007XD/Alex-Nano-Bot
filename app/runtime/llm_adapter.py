"""
LLMAdapter — изолирует runtime от конкретной реализации MultiProviderLLMClient.

VM и instructions зависят от LLMProtocol, не от llm_client_v2.
Это позволяет:
    - тестировать VM без реального LLM (MockLLMAdapter)
    - заменить провайдер без изменения instructions
"""
from __future__ import annotations

from typing import Optional, runtime_checkable
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
        role: str = "default",
        system: Optional[str] = None,
    ) -> str:
        """
        Генерация ответа по prompt.

        Args:
            prompt:  пользовательский текст / инструкция шага
            role:    роль для маппинга модели ('default', 'planner', 'coder')
            system:  системный промпт (опционально)

        Returns:
            Текст ответа (str).
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
        role: str = "default",
        system: Optional[str] = None,
    ) -> str:
        from app.core.llm_client_v2 import Message  # локальный импорт — нет цикла

        messages = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))

        response = await self._client.chat(
            messages=messages,
            model=role,        # role → _map_model_to_provider()
        )
        return response.content


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
        role: str = "default",
        system: Optional[str] = None,
    ) -> str:
        self.calls.append({"prompt": prompt, "role": role, "system": system})
        return self.fixed_response

"""
Planner — генерирует DSL-программу из user_input.

Контракт: Planner(user_input, context) → Program (dict)

Модель: role="planner" → llama-3.3-70b-versatile (Groq p1)

Программа v0.1 поддерживает инструкции:
    call_llm    — запрос к LLM
    respond     — отправить текст пользователю
    store_memory — сохранить в ChromaDB

Формат Program:
{
    "plan": [
        {
            "id":          "step1",           # уникальный идентификатор шага
            "instruction": "call_llm",        # имя инструкции из registry
            "on_error":    "abort",           # "abort" | "continue"
            "params": { ... }                 # параметры инструкции
        }
    ]
}

$-refs: значение параметра вида "$step_id" резолвится в output шага step_id.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.runtime.llm_adapter import LLMProtocol

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt для Planner LLM
# ---------------------------------------------------------------------------

_PLANNER_SYSTEM = """\
Ты — Planner, компонент детерминированного AI-рантайма.
Твоя единственная задача: преобразовать запрос пользователя в JSON-программу.

ДОСТУПНЫЕ ИНСТРУКЦИИ:
- call_llm    params: {prompt: str, role?: str, system?: str}
- respond     params: {text: str}   — текст или $ref на output предыдущего шага
- store_memory params: {content: str, memory_type?: str}

ПРАВИЛА:
1. Всегда возвращай ТОЛЬКО валидный JSON.
2. Каждый шаг имеет уникальный id (step1, step2, ...).
3. Последний шаг ВСЕГДА "respond" с text = $<id предыдущего шага>.
4. store_memory добавляй только если пользователь просит запомнить факт.
5. КРИТИЧЕСКИ ВАЖНО: Если в тексте "ЗАПРОС ПОЛЬЗОВАТЕЛЯ" присутствует блок, начинающийся с "[СИСТЕМНЫЙ КОНТЕКСТ: ИЗВЕСТНЫЕ ФАКТЫ / ВОСПОМИНАНИЯ]", ты ОБЯЗАН скопировать весь этот блок в параметр `system` внутри инструкции `call_llm`. Сам вопрос пользователя помести в `prompt`. Никогда не игнорируй системный контекст!

ПРИМЕР (вопрос с контекстом):
ЗАПРОС ПОЛЬЗОВАТЕЛЯ:
Что я просил запомнить?
[СИСТЕМНЫЙ КОНТЕКСТ: ИЗВЕСТНЫЕ ФАКТЫ / ВОСПОМИНАНИЯ]
- Сообщение 2

ОТВЕТ PLANNER:
{
  "plan": [
    {
      "id": "step1",
      "instruction": "call_llm",
      "on_error": "abort",
      "params": {
        "prompt": "Что я просил запомнить?",
        "system": "[СИСТЕМНЫЙ КОНТЕКСТ: ИЗВЕСТНЫЕ ФАКТЫ / ВОСПОМИНАНИЯ]\n- Сообщение 2",
        "role": "default"
      }
    },
    {
      "id": "step2",
      "instruction": "respond",
      "on_error": "continue",
      "params": {"text": "$step1"}
    }
  ]
}

ПРИМЕР (простой вопрос):
{
  "plan": [
    {
      "id": "step1",
      "instruction": "call_llm",
      "on_error": "abort",
      "params": {"prompt": "Как работает asyncio?", "role": "default"}
    },
    {
      "id": "step2",
      "instruction": "respond",
      "on_error": "continue",
      "params": {"text": "$step1"}
    }
  ]
}

ПРИМЕР (запомнить факт):
{
  "plan": [
    {
      "id": "step1",
      "instruction": "call_llm",
      "on_error": "abort",
      "params": {"prompt": "Подтверди что запомнил: люблю Python", "role": "default"}
    },
    {
      "id": "step2",
      "instruction": "store_memory",
      "on_error": "continue",
      "params": {"content": "Пользователь любит Python", "memory_type": "note"}
    },
    {
      "id": "step3",
      "instruction": "respond",
      "on_error": "continue",
      "params": {"text": "$step1"}
    }
  ]
}
"""

# Fallback-программа если Planner вернул невалидный JSON
def _fallback_program(user_input: str) -> Dict[str, Any]:
    return {
        "plan": [
            {
                "id": "step1",
                "instruction": "call_llm",
                "on_error": "abort",
                "params": {"prompt": user_input, "role": "default"},
            },
            {
                "id": "step2",
                "instruction": "respond",
                "on_error": "continue",
                "params": {"text": "$step1"},
            },
        ]
    }


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class Planner:
    """
    Генерирует Program из user_input через LLM (role="planner").

    Использование:
        planner = Planner(llm_adapter)
        program = await planner.generate(user_input, history)
        run_result = await vm.run(program, ctx)
    """

    def __init__(self, llm: LLMProtocol):
        self._llm = llm

    async def generate(
        self,
        user_input: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Сгенерировать Program.

        Args:
            user_input: текст сообщения пользователя
            history:    последние N сообщений [{"role": "user"|"assistant", "content": ...}]
                        используются для контекста (вставляются в промпт)

        Returns:
            Program dict. При любой ошибке возвращает fallback_program (2 шага).
        """
        prompt = self._build_prompt(user_input, history)

        try:
            raw_result = await self._llm.generate(
                prompt=prompt,
                role="planner",
                system=_PLANNER_SYSTEM,
            )
            raw = raw_result[0] if isinstance(raw_result, tuple) else raw_result
            program = self._parse(raw, user_input)
            logger.info(
                "Planner generated program: %d steps for input=%r",
                len(program.get("plan", [])),
                user_input[:60],
            )
            return program

        except Exception as e:
            logger.warning("Planner failed (%s), using fallback program", e)
            return _fallback_program(user_input)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        user_input: str,
        history: Optional[List[Dict[str, str]]],
    ) -> str:
        parts = []

        if history:
            # последние 6 обменов для контекста (не перегружаем prompt)
            recent = history[-12:]
            lines = []
            for msg in recent:
                role = "Пользователь" if msg["role"] == "user" else "Ассистент"
                lines.append(f"{role}: {msg['content']}")
            if lines:
                parts.append("ИСТОРИЯ ДИАЛОГА:\n" + "\n".join(lines))

        parts.append(f"ЗАПРОС ПОЛЬЗОВАТЕЛЯ:\n{user_input}")
        parts.append("Верни JSON-программу.")

        return "\n\n".join(parts)

    def _parse(self, raw: str, user_input: str) -> Dict[str, Any]:
        """
        Извлечь JSON из ответа LLM.
        LLM иногда оборачивает в ```json ... ``` — зачищаем.
        """
        # убрать markdown-блоки
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()

        # найти первый { ... } блок
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"No JSON object found in planner output: {raw[:200]}")

        json_str = cleaned[start:end + 1]
        # Sanitize unescaped newlines in JSON strings
        import re
        # Find strings inside JSON and replace literal newlines with \\n
        # (This is a simplified heuristic, but effective for LLM outputs)
        json_str = re.sub(r'(?<!\\)\n', r'\\n', json_str)
        try:
            program = json.loads(json_str)
        except json.JSONDecodeError as e:
            # Fallback for strict control characters (e.g., tabs, literal \r)
            sanitized = ''.join(c for c in json_str if ord(c) >= 32 or c in '\n\r\t')
            program = json.loads(sanitized)

        # базовая валидация
        if "plan" not in program or not isinstance(program["plan"], list):
            raise ValueError(f"Invalid program structure: missing 'plan' list")
        if len(program["plan"]) == 0:
            raise ValueError("Empty plan")

        # гарантировать on_error на каждом шаге
        for step in program["plan"]:
            step.setdefault("on_error", "abort")

        return program

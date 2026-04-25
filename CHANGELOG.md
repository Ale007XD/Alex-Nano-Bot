# Changelog

All notable changes to Alex-Nano-Bot will be documented in this file.

## [1.5.0] - 2026-04-25 (patch 6: Planner JSON fix + RAG pipeline)

### Fixed — Planner JSON parser (критический)
- **`app/runtime/planner.py`**: удалён `re.sub(r'(?<!\\)\n', r'\\n', json_str)` — ломал структуру JSON при каждом запросе, Planner падал в fallback на 100% запросов
- Добавлен `_fix_newlines_in_strings()` — посимвольный проход, экранирует `\n`/`\r` только внутри строковых значений, не трогает структуру JSON
- Добавлен `_ensure_rag_in_system()` — детерминированная гарантия контракта: если Planner не положил RAG-блок в `params.system` первого `call_llm` шага — подставляется автоматически. Не хардкод логики, страховка контракта между `messages.py` и VM

### Fixed — RAG pipeline
- **`app/handlers/messages.py`**: `n_memories=4` → `n_memories=8` — ChromaDB возвращает больше релевантных записей
- **`app/handlers/messages.py`**: `mem_texts` дополнен датой: `"- {content} (сохранено: {created_at[:10]})"` — LLM видит хронологию и корректно разрешает конфликты между записями с одинаковым номером сообщения

### Verified — store_memory работает end-to-end
- ChromaDB `memories` collection: 10+ записей с корректным `user_id=1` (db_user.id)
- RAG читает и пишет с одним `user_id` — несоответствия нет
- `_ensure_rag_in_system` подтверждён в проде: контекст доходит до `call_llm`

### Result
```
Planner failed → 0 (было: 100% запросов)
Injected memories: 8 (было: 4)
store_memory: работает, данные персистируются в ./data/vector_store
```

---

## [1.5.0] - 2026-04-24 (patch 5: ToolRegistry + P-6 + deprecation cleanup)

### Added — ToolRegistry (P-6 завершён)
- **`app/runtime/tool_registry.py`** — `ToolRegistry` адаптирует `SkillLoader` к `ctx.tools.execute()`
- **`app/runtime/__init__.py`** — `ToolRegistry` в публичном API

### Changed — CallToolInstruction, messages.py, skills_loader.py
- Guard на отсутствие `tool` param и `ctx.tools is None`
- `tools=None` → `tools=_tool_registry` в `messages.py`
- `SkillLoader` и `OpenClawExecutor` разделены (SRP)

### Fixed — DeprecationWarnings (5 штук)
- aiogram: `DefaultBotProperties`
- Pydantic v2: `ConfigDict` в `state_context.py`, `step_result.py`
- Python 3.12: `datetime.now(timezone.utc)` в `builder.py`

### Tests
- `test_runtime.py`: 51 → 60 тестов
- Итого: **79/79 passed, 1 warning**

---

## [1.5.0] - 2026-04-22 (patch 4)

### Added — CI/CD pipeline
- `.github/workflows/python-tests.yml` — GitHub Actions, Python 3.12

### Added — OpenClaw + MCP архитектура (scaffold)
### Changed — Ренейминг агентов (P-rename): Nanobot→FastBot, Claudbot→PlanBot, Moltbot→SkillBot

---

## [1.5.0] - 2026-04-21 (patch 3)
### Added — Тесты runtime: 51/51 passed, `tests/conftest.py`

## [1.5.0] - 2026-04-21 (patch 2)
### Fixed — StateContext персистентность: `from_db()` + `to_db_context()` + `flush()`

## [1.5.0] - 2026-04-21
### Added — Runtime VM: δ(S, Program) → S', DSL v0.1, `/mode` → ⚙️ Runtime VM

## [1.5.0] - 2026-04-20
### Fixed — LLM-модели (Groq mixtral → llama), `/providers` UI

## [1.4.0] - 2026-04-19
### Added — Knowledge Base скилл
### Fixed — BUG-1 scheduler, BUG-2 coroutine, BUG-3 двойной singleton

## [1.3.0] - 2026-02-08
### Added — Голосовые сообщения (Groq Whisper), Multi-provider LLM v2, APScheduler

## [1.2.0] - 2026-02
### Added — Hot-swap провайдеров, Fernet-шифрование, access control

## [1.1.0] - 2026-02-07
### Added — Русский интерфейс, Groq API

## [1.0.0] - 2026-02
### Added — FastBot/PlanBot/SkillBot, ChromaDB, динамические навыки, Docker Compose

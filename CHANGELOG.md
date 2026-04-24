# Changelog

All notable changes to Alex-Nano-Bot will be documented in this file.

## [1.5.0] - 2026-04-24 (patch 5)

### Added — ToolRegistry (P-6 завершён)
- **`app/runtime/tool_registry.py`** — новый файл. `ToolRegistry` адаптирует `SkillLoader` к интерфейсу `ctx.tools`, ожидаемому `CallToolInstruction`:
  - `execute(tool_name, args)` — находит callable через `SkillLoader.get_skill()`, поддерживает sync и async
  - При ошибке (не найден / упал) возвращает строку `[ToolRegistry] ...` — VM не падает, шаг получает `status="error"`
  - `list_tools()` — список активных инструментов для отладки
- **`app/runtime/__init__.py`** — `ToolRegistry` добавлен в публичный API и `__all__`

### Changed — CallToolInstruction (P-6)
- **`app/runtime/instructions/call_tool.py`** — полная переработка:
  - Guard: отсутствие param `tool` → `status="error"`
  - Guard: `ctx.tools is None` → `status="error"` (предотвращает `AttributeError`)
  - Распознавание `[ToolRegistry]`-строк → `status="error"` вместо передачи мусора в `output`

### Changed — messages.py runtime branch (P-6)
- **`app/handlers/messages.py`**: `tools=None` → `tools=_tool_registry`
- Singleton `_tool_registry = ToolRegistry(skill_loader)` создаётся при импорте модуля
- Импорты: добавлены `ToolRegistry` и `skill_loader`

### Changed — skills_loader.py (P-6-fix, полная перепись)
- **`app/core/skills_loader.py`** — два класса с чёткими границами SRP:
  - `SkillLoader` — файловая система: `load_all_skills`, `list_skills`, `get_skill`, `get_skill_info`, `get_skill_code`, `create_skill`, `delete_skill`, `get_all_tool_schemas`. Публичные свойства `skills` и `skill_info` (алиас, обратная совместимость)
  - `OpenClawExecutor` — исполнитель: allowlist, `register(func)`, Pydantic-path `model_json_schema()`, `execute()` возвращает `ToolError` как значение при ACCESS_DENIED (не бросает исключение)
  - `ToolError` — экспортируется явно
  - `MCPClientExecutorDirect` — заглушка (P-mcp)
  - `SkillLoaderFacade` — реестр треков (system/external)
  - Singleton: `skill_loader = SkillLoader()`

### Fixed — aiogram DeprecationWarning
- **`app/bot.py`**: `Bot(token=..., parse_mode=ParseMode.HTML)` → `Bot(token=..., default=DefaultBotProperties(parse_mode=ParseMode.HTML))`
- Импорты: добавлены `DefaultBotProperties` из `aiogram.client.default`

### Fixed — Pydantic v2 DeprecationWarnings
- **`app/runtime/state_context.py`**: `class Config: frozen = True` → `model_config = ConfigDict(frozen=True)`
- **`app/runtime/step_result.py`**: аналогично

### Fixed — Python 3.12 DeprecationWarning
- **`app/runtime/builder.py`**: `from datetime import datetime` → `from datetime import datetime, timezone`; `datetime.utcnow()` → `datetime.now(timezone.utc)`

### Tests — расширение test_runtime.py
- **`tests/test_runtime.py`** — добавлено 9 тестов (51 → 60):
  - `TestToolRegistry` (5): sync callable, async callable, unknown tool returns error string, exception returns error string, list_tools фильтрует inactive
  - `TestCallToolInstruction` (4): success, missing param → error, None registry → error, unknown tool → error step
- `TestMockLLMAdapter.test_generate_records_call` — исправлен под актуальную сигнатуру `generate() → Tuple[str, Optional[list]]`

### Result
```
79 passed, 1 warning in 0.76s
test_bot.py: 17/17 ✅  test_mfdba_core.py: 2/2 ✅  test_runtime.py: 60/60 ✅
CI: 🟢
```

---

## [1.5.0] - 2026-04-22 (patch 4)

### Added — CI/CD pipeline
- **`.github/workflows/python-tests.yml`** — GitHub Actions CI: Python 3.12, ubuntu-latest
- Запускает `tests/test_mfdba_core.py` + `tests/test_runtime.py` при push/PR в `main`

### Added — OpenClaw + MCP архитектура (P-6 / P-mcp, scaffold)
- **`app/core/skills_loader.py`** — scaffold классов: `OpenClawExecutorDirect`, `MCPClientExecutorDirect`, `SkillLoaderFacade`, `BaseToolExecutor`, `BaseExecutor`
- `get_all_tool_schemas()` в `SkillLoader` — MCP Tools Primitive

### Changed — Ренейминг агентов завершён (P-rename)
- `app/agents/nanobot.py` → `fastbot.py`, `claudbot.py` → `planbot.py`, `moltbot.py` → `skillbot.py`

### Known issues (закрыты в patch 5)
- BUG-4: `test_mfdba_core.py` сломан, CI красный — исправлено в patch 5

---

## [1.5.0] - 2026-04-21 (patch 3)

### Added — Тесты runtime (P-next-3)
- **`tests/test_runtime.py`** — 51 тест, 7 классов
- **`tests/conftest.py`** — `sys.modules` patching
- Результат: **51/51 passed**

---

## [1.5.0] - 2026-04-21 (patch 2)

### Fixed — StateContext персистентность (P-next-2)
- **`app/handlers/messages.py`** runtime branch: `from_db()` + `to_db_context()` + `flush()`
- Верифицировано на VPS

### Verified — Smoke-тест Planner (P-next-1)
- Groq p1 стабилен (646–2000ms planner, 730–1400ms executor)

---

## [1.5.0] - 2026-04-21

### Added — Runtime VM / Program-driven execution
- **`app/runtime/`** — δ(S, Program) → S'
- `state_context.py`, `llm_adapter.py`, `context.py`, `vm.py`, `planner.py`, `step_result.py`, `builder.py`, `registry.py`, `instructions/`
- **`messages.py`**: runtime branch `if agent_mode == 'runtime'`
- **`/mode`**: новая опция ⚙️ Runtime VM

### Added — MFDBA стратегия
- MFDBA-Lite (FastBot) и MFDBA-DAG (PlanBot)

### Changed — `/providers` UI объединён
- Устранён конфликт роутинга aiogram

---

## [1.5.0] - 2026-04-20

### Fixed — сломанные LLM-модели (PR-1)
- Groq: `mixtral-8x7b-32768` → `llama-3.3-70b-versatile`
- OpenRouter: `mistralai/mistral-7b-instruct` → `meta-llama/llama-3.3-70b-instruct:free`

### Added — выбор моделей через UI (PR-2)
- `/providers`: статус, модели, `set_model()`, health check

---

## [1.4.0] - 2026-04-19

### Added — Knowledge Base скилл
- `skills/custom/knowledge_base.py`: channel_post → SQLite + ChromaDB, cron 03:00

### Fixed — критические баги
- BUG-1: `scheduler.py` AttributeError
- BUG-2: `handlers/skills.py` coroutine без await
- BUG-3: два экземпляра `MultiProviderLLMClient`

---

## [1.3.0] - 2026-02-08

### Added
- Голосовые сообщения: Groq Whisper API
- Multi-provider LLM v2: Groq→OpenRouter→Anthropic→OpenAI, health-monitor
- APScheduler: `/remind`, `/daily`, `/weekly`, `/tasks`

---

## [1.2.0] - 2026-02

### Added
- Hot-swap провайдеров, Fernet-шифрование ключей, `BOT_TIMEZONE`, `get_allowed_users()`

---

## [1.1.0] - 2026-02-07

### Added
- Русский интерфейс, Groq API, логирование меню

---

## [1.0.0] - 2026-02

### Added
- Три агента: Nanobot, Claudbot, Moltbot. ChromaDB + fastembed, динамические навыки, Docker Compose

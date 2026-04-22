# Changelog

All notable changes to Alex-Nano-Bot will be documented in this file.

## [1.5.0] - 2026-04-22 (patch 4)

### Added — CI/CD pipeline
- **`.github/workflows/python-tests.yml`** — GitHub Actions CI: Python 3.12, ubuntu-latest
- Запускает `tests/test_mfdba_core.py` + `tests/test_runtime.py` при push/PR в `main`
- Устанавливает `requirements.txt` + `pytest pytest-asyncio pydantic`

### Added — OpenClaw + MCP архитектура (P-6 / P-mcp, частично)
- **`app/core/skills_loader.py`** — два новых слоя поверх `SkillLoader`:
  - `OpenClawExecutorDirect` — нативный экзекутор для системных навыков (zero-latency): allowlist по публичным функциям модуля, Pydantic-first валидация аргументов через `model_json_schema()`, возврат `{"ok": False, "error": {...}}` при нарушении безопасности или ValidationError
  - `MCPClientExecutorDirect` — заглушка MCP-адаптера (sandbox/DinD/Wasmtime, ожидает реализации изоляции)
  - `SkillLoaderFacade` — реестр экзекуторов: `register_system_skill()` / `register_external_skill()`
  - `get_all_tool_schemas()` в `SkillLoader` — MCP Tools Primitive (собирает схемы всех навыков)
  - `BaseToolExecutor` (Protocol) и `BaseExecutor` (ABC) — контракты для обоих треков

### Changed — Ренейминг агентов завершён на уровне файловой системы (P-rename)
- `app/agents/nanobot.py` → `app/agents/fastbot.py`
- `app/agents/claudbot.py` → `app/agents/planbot.py`
- `app/agents/moltbot.py` → `app/agents/skillbot.py`

### Added — Тест-заглушка P-6 (test_mfdba_core.py)
- **`tests/test_mfdba_core.py`** — два теста под `OpenClawExecutorDirect`-интерфейс
- ⚠️ **Сломан**: импортирует `OpenClawExecutor` и `ToolError` из `skills_loader` — оба не соответствуют реализации (`ToolError` отсутствует, `OpenClawExecutor` имеет другую сигнатуру). CI красный. Требует фикса в рамках P-6.

---

## [1.5.0] - 2026-04-21 (patch 3)

### Added — Тесты runtime (P-next-3)
- **`tests/test_runtime.py`** — 51 тест, 7 классов: `TestMockLLMAdapter`, `TestStateContext`, `TestStepResultBuilder`, `TestInstructionRegistry`, `TestExecutionVM`, `TestVMResolve`, `TestPlannerParse`
- **`tests/conftest.py`** — изоляция через `sys.modules` patching; `app` и `app.core` остаются реальными пакетами; заглушки для leaf-модулей и внешних зависимостей (chromadb, sqlalchemy, aiogram, apscheduler, fastembed)
- Результат: **51/51 passed, 1.24s** на VPS

---

## [1.5.0] - 2026-04-21 (patch 2)

### Fixed — StateContext персистентность (P-next-2)
- **`app/handlers/messages.py`** runtime branch: `StateContext.from_defaults()` → `StateContext.from_db(db_user_state)`
- Lazy get-or-create `UserState` (FK `users.id`) внутри существующей `async_session_maker` сессии
- После `_vm.run()`: `db_user_state.context = run_result.state.to_db_context()` + `session.flush()`
- Верифицировано: `UserState.context = {'fsm_state': 'idle'}` записывается корректно

### Verified — Smoke-тест Planner (P-next-1)
- Два LLM-вызова на каждый запрос в prod-логах: planner=`llama-3.3-70b-versatile` + executor=`llama-3.1-8b-instant`
- Groq p1 стабилен (646–2000ms planner, 730–1400ms executor), fallback не триггерился
- KB cron `+07:00` корректен (`BOT_TIMEZONE=Asia/Ho_Chi_Minh`)

---

## [1.5.0] - 2026-04-21

### Added — Runtime VM / Program-driven execution

- **`app/runtime/`** — детерминированная система δ(S, Program) → S'
  - `state_context.py`: `StateContext` (frozen Pydantic), `MemorySnapshot`, `OutboxEntry`; мост к `UserState.context` через `from_db()` / `to_db_context()`
  - `llm_adapter.py`: `LLMProtocol` (structural typing), `MultiProviderLLMAdapter`, `MockLLMAdapter`
  - `context.py`: `VMContext` — state, llm, memory, tools, variables
  - `vm.py`: `ExecutionVM`, `VMRunResult`; `on_error: abort|continue` per-step; рекурсивный `_resolve()` (dict + list)
  - `planner.py`: `Planner.generate(user_input, history)` → Program; role=planner → llama-3.3-70b-versatile; fallback-программа при невалидном JSON; история диалога (12 сообщений) в промпт
  - `instructions/store_memory.py`: персистирует `content` через `VectorMemory.add_memory()`
  - `__init__.py`: `default_registry` фабрика
- **`messages.py`**: runtime branch `if agent_mode == 'runtime'` → Planner → VM; синглтоны `_llm_adapter` и `_planner` при импорте модуля
- **`/mode`**: новая опция ⚙️ Runtime VM → `UserState.current_agent='runtime'`

### Added — Архитектурный рефакторинг (стратегия MFDBA)

- Утверждено разделение рантайма: **MFDBA-Lite** (sequential, low latency, FastBot) и **MFDBA-DAG** (graph, reflection, PlanBot)
- Декаплинг ядра бота от Telegram-монолита — подготовка к омниканальной архитектуре
- **P-6 повышен до High**: OpenClaw `ToolExecutor` как протокол для `skills_loader`

### Changed — Ренейминг агентов (white-label, логика)

- `Nanobot` → **FastBot**, `Claudbot` → **PlanBot**, `Moltbot` → **SkillBot**
- Отвязка от брендов коммерческих LLM для B2B/white-label дистрибуции

### Changed — `/providers` UI объединён

- Управление ключами и управление моделями объединены в единой карточке
- Устранён конфликт роутинга aiogram; бесшовная навигация `show` → `models` → `set` → back

### Known limitations

- ChromaDB PostHog `capture()` error — безопасный шум, конфликт версий, не баг
- Оверрайды `set_model` in-memory — сбрасываются при рестарте (P-7)

---

## [1.5.0] - 2026-04-20

### Fixed — сломанные LLM-модели (PR-1)
- **Groq p1**: `mixtral-8x7b-32768` → `llama-3.3-70b-versatile`
- **OpenRouter p2**: `mistralai/mistral-7b-instruct` → `meta-llama/llama-3.3-70b-instruct:free`; убрана платная `anthropic/claude-3-haiku`
- **`_register_kb_refresh_cron`**: убран фильтр по несуществующей колонке `ScheduledTask.status`

### Added — выбор моделей через UI (PR-2)
- `/providers`: статус, текущие модели, `set_model()`, `get_models_info()`, health check из UI

---

## [1.4.0] - 2026-04-19

### Added — Knowledge Base скилл
- `skills/custom/knowledge_base.py`: channel_post → SQLite + ChromaDB, граф связей (jaccard), cron 03:00
- `app/handlers/channel.py`: `@router.channel_post()`

### Fixed — критические баги (аудит)
- `scheduler.py`: AttributeError при каждом срабатывании
- `handlers/skills.py`: `callback.answer()` без await
- Два экземпляра `MultiProviderLLMClient` → удалён `llm_client.py`, все на v2 singleton

---

## [1.3.0] - 2026-02-08

### Added
- Голосовые сообщения: Groq Whisper API.
- Multi-provider LLM v2: Groq→OpenRouter→Anthropic→OpenAI, health-monitor.
- APScheduler: `/remind`, `/daily`, `/weekly`, `/tasks`.

---

## [1.2.0] - 2026-02

### Added
- Hot-swap провайдеров, Fernet-шифрование ключей, `BOT_TIMEZONE`, `get_allowed_users()`.

---

## [1.1.0] - 2026-02-07

### Added
- Русский интерфейс, Groq API, логирование меню.

---

## [1.0.0] - 2026-02

### Added
- Три агента: Nanobot, Claudbot, Moltbot. ChromaDB + fastembed, динамические навыки, Docker Compose.

# Changelog

All notable changes to Alex-Nano-Bot will be documented in this file.

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
- **P-6 повышен до High**: OpenClaw `ToolExecutor` как протокол для `skills_loader` (строгие JSON-схемы, детерминированные вызовы)

### Changed — Ренейминг агентов (white-label)

- `Nanobot` → **FastBot** (`app/agents/fastbot.py`)
- `Claudbot` → **PlanBot** (`app/agents/planbot.py`)
- `Moltbot` → **SkillBot** (`app/agents/skillbot.py`)
- Отвязка от брендов коммерческих LLM для B2B/white-label дистрибуции

### Changed — `/providers` UI объединён

- Управление ключами и управление моделями объединены в единой карточке `/providers`
- Устранён конфликт роутинга aiogram между отдельными FSM-хендлерами
- Бесшовная навигация: `providers:show` → `providers:models` → `providers:set` → back

### Known limitations

- `StateContext` персистентность (`from_db` / `to_db_context`) — реализована и верифицирована (см. patch 2)
- ChromaDB PostHog `capture()` error — безопасный шум, конфликт версий, не баг
- Оверрайды `set_model` in-memory — сбрасываются при рестарте (P-7)

---

## [1.5.0] - 2026-04-20

### Fixed — сломанные LLM-модели (PR-1)
- **Groq p1**: `mixtral-8x7b-32768` → `llama-3.3-70b-versatile` (удалена с Groq 2025-03-20; 400 Bad Request, 3 ретрая × 2с до fallback)
- **OpenRouter p2**: `mistralai/mistral-7b-instruct` → `meta-llama/llama-3.3-70b-instruct:free` (404 Not Found)
- **OpenRouter p2**: удалена `anthropic/claude-3-haiku` из списка (платная)
- **`_map_model_to_provider`**: обновлены маппинги `planner` и `default` для groq и openrouter
- **`bot.py` / `_register_kb_refresh_cron`**: `ScheduledTask.status` не существует как колонка → `AttributeError`; убран фильтр по `status`, идемпотентность по `name`

### Added — выбор моделей через интерфейс бота (PR-2)
- **`/providers`** — меню: статус (🟢/🟡/🔴), приоритет, текущие модели по ролям
- **`providers:show:<n>`** — карточка провайдера с назначениями `default / coder / planner`
- **`providers:models:<n>:<role>`** — список моделей с отметкой текущей (✅)
- **`providers:set:<n>:<role>:<idx>`** — применить модель по индексу
- **`providers:refresh`** — health check всех провайдеров из UI
- **`llm_client_v2.set_model(provider, role, idx)`** — in-memory оверрайд
- **`llm_client_v2.get_models_info()`** — список провайдеров с текущими ролями для UI

---

## [1.4.0] - 2026-04-19

### Added — Knowledge Base скилл
- **`skills/custom/knowledge_base.py`**: автосбор статей из Telegram-канала через `channel_post` хендлер
- URL из `message.entities` (text_link/url) + regex-fallback
- Хранение: SQLite `data/knowledge_base.db` (articles + article_links) + ChromaDB (`memory_type='article'`)
- `article_id = sha1(url)[:12]`, граф связей по jaccard тегов и тем
- Команды: `kb add`, `kb search`, `kb related`, `kb refresh`, `kb refresh_stale`, `kb list`, `kb stats`
- Cron `0 3 * * *` через sentinel `__kb_refresh_stale__` в `ScheduledTask.message_text`
- `_register_kb_refresh_cron` идемпотентна — проверяет наличие задачи по `name`
- `app/handlers/channel.py`: `@router.channel_post()`, добавлен в `allowed_updates`

### Fixed — критические баги (аудит)
- `scheduler.py`: `select(get_or_create_user.__self__)` → `AttributeError` при каждом срабатывании
- `handlers/skills.py`: `check_callback_access()` sync → async; `callback.answer()` без await
- Два экземпляра `MultiProviderLLMClient`: `llm_client.py` удалён, все импорты на v2 singleton

### Fixed — хендлеры (аудит)
- `settings:*` callback хендлеры добавлены в `commands.py`
- `sanitize_html()` в `helpers.py`, применяется к LLM-ответу перед отправкой
- `parse_time_input()` в `helpers.py`, принимает `bot_timezone` как аргумент
- Дубль `check_callback_access` удалён из `skills.py`
- `action:cancel` определяет контекст по FSM-состоянию
- `memory.py`: `check_access_callback` во всех 4 callback хендлерах
- `reminders.py`: `process_reminder_time` корректно читает `reminder_type` → daily/weekly
- `mistralai/mistral-7b-instruct:free` → без `:free` суффикса (был 404)

### Added — `llm_client_v2.py`
- `chat_with_fallback()`, `stream_chat()` stub, `check_health()` публичный

### Refactored
- `ReminderStates` перенесён в `states.py`
- `create_interval_task`: добавлен `timezone=settings.BOT_TIMEZONE`

---

## [1.3.0] - 2026-02-08

### Added
- Голосовые сообщения: Groq Whisper API, группы, лимит 300 сек.
- Multi-provider LLM v2: Groq→OpenRouter→Anthropic→OpenAI, health-monitor, pending tasks.
- APScheduler: `/remind`, `/daily`, `/weekly`, `/tasks`, `/cancel_task`, `/scheduler_stats`.

---

## [1.2.0] - 2026-02

### Added
- Hot-swap провайдеров через `/providers` (FSM, Fernet, DB persistence).
- `crypto.py`: `encrypt_key()`, `decrypt_key()`, `mask_key()`.
- `ProviderConfig` таблица; `_load_provider_configs_from_db()` при старте.
- `BOT_TIMEZONE` единый источник для scheduler и reminders.
- `get_allowed_users()` во всех хендлерах, хардкод ID удалён.
- Anthropic API fix: `/v1/messages`, `x-api-key`, `system` top-level.

---

## [1.1.0] - 2026-02-07

### Added
- Русский интерфейс, прямое подключение к Groq API, логирование меню.

---

## [1.0.0] - 2026-02

### Added
- Три агента: Nanobot, Claudbot, Moltbot.
- ChromaDB + fastembed, динамические навыки, SQLite + SQLAlchemy async, Docker Compose.

# Прогресс разработки Alex-Nano-Bot

## Последнее обновление: 21.04.2026 — v1.5.0

---

## ✅ Выполнено

### v1.5.0 — Runtime VM + Архитектурный рефакторинг (21.04.2026)

**Runtime VM — Program-driven execution**

- `app/runtime/` — детерминированная система δ(S, Program) → S'
- `StateContext` (frozen Pydantic): `apply(StepResult)` → новый инстанс; мост к `UserState.context` через `from_db()` / `to_db_context()`
- `LLMProtocol` + `MultiProviderLLMAdapter`: VM зависит от протокола, не от `MultiProviderLLMClient` напрямую; `MockLLMAdapter` для тестов
- `VMRunResult`: `state + results + aborted + outbox + failed_steps`
- `on_error: abort|continue` на каждом шаге; `call_llm` → abort, `respond` → continue
- Рекурсивный `_resolve()` — покрывает dict/list на любой глубине (фикс для `call_tool` с вложенными args)
- `Planner.generate(user_input, history)` → Program; история диалога (12 сообщений) в промпт; fallback-программа при ParseError
- `instructions/store_memory.py`: `VectorMemory.add_memory()` → ChromaDB
- `messages.py`: синглтоны `_llm_adapter`, `_planner` при импорте; runtime branch не ломает FastBot/PlanBot/SkillBot
- **Smoke-тест пройден**: режим Runtime VM задеплоен и отвечает через VM (лог: groq success, нет app.agents.router)

**Ренейминг агентов (white-label)**

| Старое | Новое | Файл |
|--------|-------|------|
| Nanobot | FastBot | `app/agents/fastbot.py` |
| Claudbot | PlanBot | `app/agents/planbot.py` |
| Moltbot | SkillBot | `app/agents/skillbot.py` |

Цель: отвязка от брендов коммерческих LLM, подготовка к B2B/white-label дистрибуции.

**`/providers` UI объединён**

- Управление ключами и управление моделями в единой карточке
- Устранён конфликт роутинга aiogram
- Навигация: `providers:show` → `providers:models` → `providers:set` → back

**MFDBA архитектурная стратегия**

```
FastBot  →  MFDBA-Lite  (sequential, low latency)
PlanBot  →  MFDBA-DAG   (graph, reflection, Redis queue)
SkillBot →  OpenClaw ToolExecutor (strict JSON schemas)
```

Telegram выступает одним из Gateway — ядро декаплировано от монолита.

---

### v1.5.0 — Исправление моделей + выбор модели через UI (20.04.2026)

**PR-1 / Сломанные LLM-модели**

- Groq: `mixtral-8x7b-32768` удалена (2025-03-20) → 400 Bad Request. Заменена на `llama-3.3-70b-versatile`.
- OpenRouter: `mistralai/mistral-7b-instruct` → 404. Заменена на `meta-llama/llama-3.3-70b-instruct:free`. Убрана платная `anthropic/claude-3-haiku`.
- `bot.py / _register_kb_refresh_cron`: `ScheduledTask.status` не существует → `AttributeError` при старте. Убран фильтр по `status`.

**PR-2 / Выбор модели через UI**

- `/providers`: статус провайдеров, текущие модели по ролям, health check из UI.
- `set_model()` — in-memory оверрайд. `get_models_info()` — данные для UI.
- ⚠️ Оверрайды не персистентны (сбрасываются при рестарте) — P-7.

---

### v1.4.0 — Knowledge Base + аудит хендлеров (19.04.2026)

- `skills/custom/knowledge_base.py`: channel_post → SQLite + ChromaDB, граф связей (jaccard), cron 03:00
- BUG-1: `scheduler.py` — AttributeError при каждом срабатывании задачи
- BUG-2: `skills.py` — `callback.answer()` без await → вечный spinner
- BUG-3: два независимых `MultiProviderLLMClient` → hot-swap не работал

---

### v1.3.0 — Multi-provider + Scheduler + Voice (08.02.2026)
- Groq Whisper, APScheduler, `/remind` `/daily` `/weekly`

### v1.2.0 — Hot-swap + Security (февраль 2026)
- `/providers` FSM, Fernet, ProviderConfig, BOT_TIMEZONE, access control

### v1.1.0 — Русификация (07.02.2026)

### v1.0.0 — Initial (февраль 2026)
- FastBot, PlanBot, SkillBot, ChromaDB, навыки, Docker Compose

---

## 📋 Pending

| ID | Задача | Приоритет |
|----|--------|-----------|
| P-next-1 | Smoke-тест Planner: 'Привет' + 'Запомни: я люблю Python' — 2 LLM-вызова в логах | **high** |
| P-next-2 | `StateContext` персистентность: `from_db` при загрузке + `to_db_context` при сохранении | **high** |
| P-next-3 | Тесты: `MockLLMAdapter` + `vm.run()` e2e + `Planner._parse()` unit (невалидный JSON) | **high** |
| P-6 | OpenClaw `ToolExecutor` как протокол для `skills_loader` (строгие JSON-схемы) | **high** ↑ |
| P-2 | `tests/test_bot.py` — patch consumers, conftest с mock env | medium |
| P-3 | `handle_photo` — `aiohttp` → `httpx` | medium |
| P-rename | Завершить ренейминг агентов в файловой системе, клавиатурах и документации | medium |
| P-4 | Vision-модель в `settings` (захардкожена в `messages.py`) | low |
| P-5 | `asyncio.gather` для параллельных skills | low |
| P-7 | Персистентность `set_model` через `ProviderConfig` | low |
| P-dsl-4 | DSL v0.4: `$step.output.field`, `$memories[0]` — reference resolver | low |
| P-dsl-5 | DSL v0.5: typed conditions (AST) — branching | low |
| P-dag | MFDBA-DAG: graph runtime + Redis queue для PlanBot | low |
| P-sandbox | Изоляция `vm.py` в песочнице (Docker-in-Docker / WASM) | low |
| P-decouple | Миграция `app/runtime/` в независимую библиотеку MFDBA | low |
| P-volume | Volume mount в `docker-compose.yml` | low |
| P-planner-v2 | Planner v2: `retrieve_memory` перед генерацией программы | low |
| **P-mcp** | **Гибридная интеграция OpenClaw и MCP** | **medium** |

---

## 🔮 Backlog (перспективные эпики)

### P-mcp — Гибридная интеграция OpenClaw и MCP *(medium)*

**Цель:** сохранить low-latency для FastBot (MFDBA-Lite) и дать PlanBot/SkillBot (MFDBA-DAG) стандартизированную интеграцию внешних инструментов без усложнения монолита. Закрывает два вектора: P-6 (детерминированность вызовов) и P-sandbox (изоляция `vm.py`).

**Подзадачи:**

`app/runtime/llm_adapter.py` — адаптация формата передачи контекста под спецификацию MCP Primitives (Tools, Resources, Prompts); ядро OpenClaw сохраняется.

`app/core/skills_loader.py` — паттерн Adapter с двумя треками:
- **fast-track**: прямой вызов OpenClaw `ToolExecutor` для системных/лёгких навыков (низкая задержка)
- **isolated-track**: прослойка OpenClaw-to-MCP для внешних инструментов (Git, БД, Docker) в изолированных MCP-серверах

---

## 🔧 Текущая конфигурация

**LLM singleton:** `app.core.llm_client_v2.llm_client` (`MultiProviderLLMClient`)
**Провайдеры:** Groq p1 → OpenRouter p2 → Anthropic p3 → OpenAI p4
**Groq модели:** `llama-3.1-8b-instant` (default/coder), `llama-3.3-70b-versatile` (planner)
**OpenRouter модели:** `llama-3.3-70b-instruct:free` (default/planner), `llama-3.1-8b-instruct:free` (coder)

**Runtime VM:**
- Path: `app/runtime/`
- DSL: v0.1 (`call_llm`, `respond`, `store_memory`, `call_tool`)
- Planner: `llama-3.3-70b-versatile` (role=planner, Groq p1)
- Executor: `llama-3.1-8b-instant` (role=default, Groq p1)
- Integration: `messages.py` runtime branch

**Агенты:** FastBot (`fastbot.py`) · PlanBot (`planbot.py`) · SkillBot (`skillbot.py`)
**Timezone:** `settings.BOT_TIMEZONE` = `Asia/Irkutsk`
**Access control:** `get_allowed_users()` → `settings.ADMIN_IDS`
**FSM-состояния:** `app/utils/states.py`
**Ключи провайдеров:** Fernet-encrypted в `provider_configs`

**Деплой (COPY в образ — всегда build перед up):**
```bash
docker compose build alex-nano-bot && docker compose up -d alex-nano-bot
```
**VPS path:** `~/my-bots/Alex-Nano-Bot`

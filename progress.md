# Прогресс разработки Alex-Nano-Bot

## Последнее обновление: 24.04.2026 — v1.5.0 (patch 5: ToolRegistry + P-6 + deprecation cleanup)

---

## ✅ Выполнено (25 фич)

### patch 5 — ToolRegistry + P-6 + cleanup (24.04.2026)

**P-6-fix + P-6 закрыты**

`app/core/skills_loader.py` — полная перепись с чёткими границами ответственности:

| Класс | Ответственность | Статус |
|-------|----------------|--------|
| `SkillLoader` | Файловая система: `load_all_skills`, `list_skills`, `create_skill`, `delete_skill`, `get_skill_code` | ✅ реализован |
| `OpenClawExecutor` | Исполнитель: allowlist + Pydantic-first `model_json_schema()`, возврат `ToolError` как значения | ✅ реализован |
| `MCPClientExecutorDirect` | MCP-заглушка (P-mcp) | ⚙️ заглушка |
| `SkillLoaderFacade` | Реестр экзекуторов: system/external треки | ✅ реализован |
| `ToolError` | Structured error при ACCESS_DENIED / NOT_FOUND | ✅ экспортируется |

Публичные свойства `SkillLoader`: `skills`, `skill_info` (алиас, обратная совместимость с `test_bot.py`).

`app/runtime/tool_registry.py` — новый файл. `ToolRegistry` адаптирует `SkillLoader` к интерфейсу `ctx.tools.execute(name, args)`:
- Поддержка sync и async callable
- Ловит исключения навыков, возвращает строки `[ToolRegistry] ...` (VM не падает)
- `list_tools()` для отладки

`app/runtime/instructions/call_tool.py` — обновлён:
- Guard на `tool` param missing
- Guard на `ctx.tools is None`
- Распознавание `[ToolRegistry]`-ошибок → `status="error"` в `StepResult`

`app/handlers/messages.py`:
- `tools=None` → `tools=_tool_registry` (singleton `ToolRegistry(skill_loader)`)
- Импорт `ToolRegistry` и `skill_loader` при старте модуля

`app/runtime/__init__.py` — `ToolRegistry` добавлен в публичный API.

**aiogram DeprecationWarning устранён**

`app/bot.py`: `Bot(token=..., parse_mode=...)` → `Bot(token=..., default=DefaultBotProperties(parse_mode=ParseMode.HTML))`.

**Pydantic v2 DeprecationWarnings устранены**

`app/runtime/state_context.py`: `class Config: frozen = True` → `model_config = ConfigDict(frozen=True)`.
`app/runtime/step_result.py`: аналогично.

**Python 3.12 DeprecationWarning устранён**

`app/runtime/builder.py`: `datetime.utcnow()` → `datetime.now(timezone.utc)`.

**Тесты расширены**

`tests/test_runtime.py` — добавлены 9 тестов (итого **60/60** в файле):
- `TestToolRegistry` (5 тестов): sync/async callable, unknown tool, exception handling, list_tools
- `TestCallToolInstruction` (4 теста): success, missing param, None registry, unknown tool → error step

**Итоговое состояние CI: 79/79 passed, 1 warning** (`pytest.mark.integration` не зарегистрирован — низкий приоритет).

---

### patch 4 — CI + OpenClaw scaffold (22.04.2026)

**CI/CD pipeline**

`.github/workflows/python-tests.yml` — GitHub Actions: Python 3.12, ubuntu-latest, push/PR в `main`.

**OpenClaw + MCP архитектура (scaffold)**

Классы добавлены, унификация выполнена в patch 5.

**P-rename завершён**

`nanobot.py` → `fastbot.py`, `claudbot.py` → `planbot.py`, `moltbot.py` → `skillbot.py`.

---

### patch 3 — Тесты runtime (21.04.2026)

`tests/test_runtime.py` — 7 классов, 51 тест (расширено до 60 в patch 5):

| Класс | Тестов (patch 3) |
|-------|--------|
| `TestMockLLMAdapter` | 4 |
| `TestStateContext` | 10 |
| `TestStepResultBuilder` | 7 |
| `TestInstructionRegistry` | 3 |
| `TestExecutionVM` | 7 |
| `TestVMResolve` | 7 |
| `TestPlannerParse` | 13 |

`tests/conftest.py` — `sys.modules` patching, изоляция leaf-модулей.

---

### patch 2 — StateContext персистентность (21.04.2026)

`messages.py` runtime branch: `from_db()` + `to_db_context()` + `flush()`. Верифицировано на VPS.

---

### v1.5.0 — Runtime VM + MFDBA (21.04.2026)

`app/runtime/` — δ(S, Program) → S': StateContext, LLMProtocol, VMContext, ExecutionVM, Planner, DSL v0.1. `/mode` → ⚙️ Runtime VM.

### v1.5.0 — модели + UI (20.04.2026)

PR-1: Groq/OR модели исправлены. PR-2: выбор модели через `/providers`.

### v1.4.0 — KB + аудит (19.04.2026)

Knowledge Base скилл. BUG-1/2/3 исправлены.

### v1.0.0–v1.3.0 (февраль 2026)

- Initial: FastBot/PlanBot/SkillBot, ChromaDB, навыки, Docker Compose
- v1.2.0: hot-swap, Fernet, access control
- v1.3.0: Whisper, APScheduler

---

## 🐛 Известные дефекты

Активных блокирующих дефектов нет. BUG-4 закрыт в patch 5.

| ID | Файл | Описание | Severity | Статус |
|----|------|----------|----------|--------|
| ~~BUG-4~~ | `tests/test_mfdba_core.py` | ImportError на `ToolError` / несоответствие интерфейсов | HIGH | ✅ закрыт (patch 5) |

---

## 📋 Pending

| ID | Задача | Приоритет |
|----|--------|-----------|
| P-mcp | MCP: реальная реализация `MCPClientExecutorDirect`, sandbox/Wasmtime | medium |
| P-2 | `test_bot.py` — mock env, убрать зависимость от `BOT_TOKEN` | medium |
| P-3 | `handle_photo` — первый проход на `aiohttp` → `httpx` | medium |
| P-4 | Vision-модель в `settings` (захардкожена в `messages.py`) | low |
| P-5 | `asyncio.gather` для параллельных skills в агентах | low |
| P-7 | Персистентность `set_model` через `ProviderConfig` | low |
| P-dsl-4 | DSL v0.4: `$step.output.field`, `$memories[0]` | low |
| P-dsl-5 | DSL v0.5: typed conditions (AST) | low |
| P-dag | MFDBA-DAG: graph runtime + Redis queue | low |
| P-sandbox | Изоляция `vm.py` в песочнице (DinD / WASM) | low |
| P-decouple | Миграция `app/runtime/` в библиотеку MFDBA | low |
| P-volume | Volume mount в `docker-compose.yml` | low |
| P-planner-v2 | Planner v2: `retrieve_memory` перед генерацией | low |
| P-pytest-marks | Зарегистрировать `integration` mark в `pytest.ini` | low |

---

## 🔧 Текущая конфигурация

**LLM:** Groq p1 → OpenRouter p2 → Anthropic p3 → OpenAI p4
**Groq:** `llama-3.1-8b-instant` (default/coder), `llama-3.3-70b-versatile` (planner)
**OpenRouter:** `llama-3.3-70b-instruct:free` (default/planner), `llama-3.1-8b-instruct:free` (coder)

**Runtime VM:** DSL v0.1 · Planner=llama-3.3-70b-versatile · Executor=llama-3.1-8b-instant · persistence через `UserState.context`

**Skills executor:**
- fast-track: `OpenClawExecutor` (allowlist + Pydantic validation) → `ToolRegistry` → `call_tool` VM instruction
- isolated-track: `MCPClientExecutorDirect` (stub)

**Тесты:** `test_runtime.py` 60/60 ✅ · `test_mfdba_core.py` 2/2 ✅ · `test_bot.py` 17/17 ✅
**CI:** 79/79 passed 🟢

**Агенты:** FastBot · PlanBot · SkillBot
**Timezone:** `Asia/Ho_Chi_Minh` (UTC+7)
**Deploy:**
```bash
docker compose build alex-nano-bot && docker compose up -d alex-nano-bot
```

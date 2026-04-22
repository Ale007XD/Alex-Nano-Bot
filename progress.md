# Прогресс разработки Alex-Nano-Bot

## Последнее обновление: 22.04.2026 — v1.5.0 (patch 4: CI + OpenClaw scaffold)

---

## ✅ Выполнено (20 фич)

### patch 4 — CI + OpenClaw scaffold (22.04.2026)

**CI/CD pipeline**

`.github/workflows/python-tests.yml` — GitHub Actions: Python 3.12, ubuntu-latest, push/PR в `main`. Запускает `test_mfdba_core.py` + `test_runtime.py`.

**OpenClaw + MCP архитектура (P-6/P-mcp, scaffold)**

`app/core/skills_loader.py` — новые классы:

| Класс | Трек | Статус |
|-------|------|--------|
| `OpenClawExecutorDirect` | fast-track (system skills) | ✅ реализован |
| `MCPClientExecutorDirect` | isolated-track (external) | ⚙️ заглушка |
| `SkillLoaderFacade` | реестр экзекуторов | ✅ реализован |
| `BaseToolExecutor` (Protocol) | контракт | ✅ |
| `BaseExecutor` (ABC) | контракт | ✅ |

`OpenClawExecutorDirect`: allowlist по публичным функциям (`not name.startswith('_')`), Pydantic-first валидация через `model_json_schema()`, возврат structured error при `ACCESS_DENIED` / `ValidationError`.

`get_all_tool_schemas()` в `SkillLoader` — MCP Tools Primitive (схемы всех навыков).

**⚠️ Дефект BUG-4 (блокирует CI):** `test_mfdba_core.py` импортирует `OpenClawExecutor` и `ToolError` — оба не соответствуют реализации. `ToolError` отсутствует в codebase. CI красный. Fix: P-6-fix.

**P-rename завершён**

Файловый ренейминг агентов завершён: `nanobot.py` → `fastbot.py`, `claudbot.py` → `planbot.py`, `moltbot.py` → `skillbot.py`.

---

### patch 3 — Тесты runtime (21.04.2026)

**P-next-3: 51/51 passed**

`tests/conftest.py`: `sys.modules` patching — `app`/`app.core` остаются реальными пакетами, заглушки для leaf-модулей и внешних зависимостей.

`tests/test_runtime.py` — 7 классов, 51 тест:

| Класс | Тестов |
|-------|--------|
| `TestMockLLMAdapter` | 4 |
| `TestStateContext` | 10 |
| `TestStepResultBuilder` | 7 |
| `TestInstructionRegistry` | 3 |
| `TestExecutionVM` | 7 |
| `TestVMResolve` | 7 |
| `TestPlannerParse` | 13 |

```
python -m pytest tests/test_runtime.py -v --no-header
# 51 passed, 24 warnings in 1.24s
```

---

### patch 2 — StateContext персистентность (21.04.2026)

**P-next-2** — `messages.py` runtime branch: `from_db()` + `to_db_context()` + `flush()`. Верифицировано на VPS.

**P-next-1** — Smoke-тест Planner: два LLM-вызова в логах, Groq p1 стабилен (646–2000ms planner, 730–1400ms executor).

---

### v1.5.0 — Runtime VM + MFDBA (21.04.2026)

- `app/runtime/` — δ(S, Program) → S': StateContext, LLMProtocol, VMContext, ExecutionVM, Planner, DSL v0.1
- `/mode` → ⚙️ Runtime VM; ренейминг агентов (логика); `/providers` UI объединён; MFDBA стратегия утверждена

### v1.5.0 — модели + UI (20.04.2026)

- PR-1: Groq/OR модели исправлены; PR-2: выбор модели через `/providers`

### v1.4.0 — KB + аудит (19.04.2026)

- Knowledge Base скилл; BUG-1/2/3 исправлены

### v1.0.0–v1.3.0 (февраль 2026)

- Initial: FastBot/PlanBot/SkillBot, ChromaDB, навыки, Docker Compose
- v1.2.0: hot-swap, Fernet, access control
- v1.3.0: Whisper, APScheduler

---

## 🐛 Известные дефекты

| ID | Файл | Описание | Severity |
|----|------|----------|----------|
| **BUG-4** | `tests/test_mfdba_core.py` | Импортирует `OpenClawExecutor` + `ToolError` — не соответствуют реализации. `ToolError` не существует. CI падает с `ImportError`. | **HIGH** — блокирует CI |

---

## 📋 Pending

| ID | Задача | Приоритет |
|----|--------|-----------|
| **P-6-fix** | Починить `test_mfdba_core.py`: добавить `ToolError`, унифицировать интерфейс, исправить импорты | **high** — блокер CI |
| **P-6** | OpenClaw: унифицировать `OpenClawExecutor`/`Direct` → один класс, подключить к `call_tool` в VM | **high** |
| P-mcp | MCP: реальная реализация `MCPClientExecutorDirect`, интеграция `SkillLoaderFacade` в startup | medium |
| P-2 | `test_bot.py` — mock env, убрать зависимость от `BOT_TOKEN` | medium |
| P-3 | `handle_photo` — `aiohttp` → `httpx` | medium |
| P-4 | Vision-модель в `settings` | low |
| P-5 | `asyncio.gather` для параллельных skills | low |
| P-7 | Персистентность `set_model` через `ProviderConfig` | low |
| P-dsl-4 | DSL v0.4: `$step.output.field`, `$memories[0]` | low |
| P-dsl-5 | DSL v0.5: typed conditions (AST) | low |
| P-dag | MFDBA-DAG: graph runtime + Redis queue | low |
| P-sandbox | Изоляция `vm.py` в песочнице | low |
| P-decouple | Миграция `app/runtime/` в библиотеку MFDBA | low |
| P-volume | Volume mount в `docker-compose.yml` | low |
| P-planner-v2 | Planner v2: `retrieve_memory` перед генерацией | low |

---

## 🔧 Текущая конфигурация

**LLM:** Groq p1 → OpenRouter p2 → Anthropic p3 → OpenAI p4
**Groq:** `llama-3.1-8b-instant` (default/coder), `llama-3.3-70b-versatile` (planner)
**OpenRouter:** `llama-3.3-70b-instruct:free` (default/planner), `llama-3.1-8b-instruct:free` (coder)

**Runtime VM:** DSL v0.1 · Planner=llama-3.3-70b-versatile · Executor=llama-3.1-8b-instant · persistence через `UserState.context`

**Skills executor:**
- fast-track: `OpenClawExecutorDirect` (allowlist + Pydantic validation)
- isolated-track: `MCPClientExecutorDirect` (stub)

**Тесты:** `test_runtime.py` 51/51 ✅ · `test_mfdba_core.py` BROKEN ❌ (BUG-4)

**CI:** `.github/workflows/python-tests.yml` — красный из-за BUG-4

**Агенты:** FastBot · PlanBot · SkillBot
**Timezone:** `Asia/Ho_Chi_Minh` (UTC+7)
**Deploy:**
```bash
docker compose build alex-nano-bot && docker compose up -d alex-nano-bot
```

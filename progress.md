# Прогресс разработки Alex-Nano-Bot

## Последнее обновление: 25.04.2026 — v1.5.0 (patch 6: Planner JSON fix + RAG pipeline)

---

## ✅ Выполнено (28 фич)

### patch 6 — Planner JSON fix + RAG pipeline (25.04.2026)

**Planner стабилизирован**

`app/runtime/planner.py`:
- Удалён сломанный `re.sub` — ломал JSON структуру на 100% запросов
- `_fix_newlines_in_strings()` — посимвольный парсер, экранирует переносы только внутри строковых значений
- `_ensure_rag_in_system()` — детерминированная страховка контракта: RAG-блок гарантированно попадает в `params.system` первого `call_llm` шага

**RAG pipeline восстановлен**

`app/handlers/messages.py`:
- `n_memories=4` → `n_memories=8`
- `mem_texts` дополнен датой создания записи

**Верифицировано в проде:**
- `Planner failed` — 0 (было 100%)
- `store_memory` пишет в ChromaDB, данные персистируются
- Бот корректно отвечает на «Что я просил запомнить?»

---

### patch 5 — ToolRegistry + P-6 + cleanup (24.04.2026)

**P-6 + P-6-fix закрыты** — `SkillLoader`, `OpenClawExecutor`, `ToolRegistry`, `CallToolInstruction`. 5 DeprecationWarning устранены. Тесты: 51 → 60 → 79/79.

---

### patch 4 — CI + OpenClaw scaffold (22.04.2026)

CI/CD GitHub Actions. Ренейминг агентов завершён.

---

### patch 3 — Тесты runtime (21.04.2026)

51 тест, 7 классов.

---

### patch 2 — StateContext персистентность (21.04.2026)

`from_db()` + `to_db_context()`. Верифицировано на VPS.

---

### v1.5.0 — Runtime VM (21.04.2026)

`app/runtime/`, DSL v0.1, `/mode` → ⚙️ Runtime VM.

### v1.0.0–v1.4.0 (фев–апр 2026)

FastBot/PlanBot/SkillBot, ChromaDB, навыки, Docker, голос, планировщик, KB.

---

## 🐛 Известные дефекты

Активных блокирующих дефектов нет.

| ID | Описание | Severity | Статус |
|----|----------|----------|--------|
| ~~BUG-4~~ | ImportError на ToolError | HIGH | ✅ patch 5 |
| ~~BUG-planner~~ | Planner failed 100% — re.sub ломал JSON | CRITICAL | ✅ patch 6 |
| ~~BUG-rag~~ | RAG контекст не доходил до call_llm | HIGH | ✅ patch 6 |

---

## 📋 Pending

| ID | Задача | Приоритет |
|----|--------|-----------|
| P-mcp | MCP: реальная реализация `MCPClientExecutorDirect` | medium |
| P-2 | `test_bot.py` — mock BOT_TOKEN, убрать зависимость от реального токена | medium |
| P-3 | `handle_photo` — `aiohttp` → `httpx` | medium |
| P-yt | `messages.py`: `yt_skill.run()` → `yt_skill()` — AttributeError при YouTube-запросах | medium |
| P-voice | `handle_voice` игнорирует `agent_mode == "runtime"` | medium |
| P-7 | Персистентность `set_model` через `ProviderConfig` в БД | low |
| P-4 | `VISION_MODEL` в settings (захардкожен в `messages.py`) | low |
| P-5 | `asyncio.gather` для параллельных skills | low |
| P-dsl-4 | DSL v0.4: `$step.output.field`, `$memories[0]` | low |
| P-dsl-5 | DSL v0.5: typed conditions (AST) | low |
| P-dag | MFDBA-DAG: graph runtime + Redis queue | low |
| P-sandbox | Изоляция `vm.py` (DinD / WASM) | low |
| P-decouple | Миграция `app/runtime/` в библиотеку MFDBA | low |
| P-volume | `./app:/app/app` volume mount в `docker-compose.yml` | low |
| P-planner-v2 | Planner v2: `retrieve_memory` перед генерацией программы | low |
| P-pytest-marks | Зарегистрировать `integration` mark в `pytest.ini` | low |
| P-deploy-name | `docker compose build alex-nano-bot` → `bot` (имя сервиса, не контейнера) | low |

---

## 🔧 Текущая конфигурация

**LLM:** Groq p1 → OpenRouter p2 → Anthropic p3 → OpenAI p4  
**Groq:** `llama-3.1-8b-instant` (default/coder), `llama-3.3-70b-versatile` (planner)

**Runtime VM:** DSL v0.1 · Planner стабилен · store_memory работает · RAG: 8 memories + даты

**Skills:** 7 навыков (calculator, echo, reminder, import_chat, knowledge_base, validated_answer, youtube_transcript)

**Тесты:** 79/79 ✅ · CI: 🟢  
**Память:** ChromaDB `./data/vector_store` · 10+ записей · персистентна

**Deploy:**
```bash
docker compose build bot && docker compose up -d bot
```

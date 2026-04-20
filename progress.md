# Прогресс разработки Alex-Nano-Bot

## Последнее обновление: 20.04.2026 — v1.5.0

---

## ✅ Выполнено

### v1.5.0 — Исправление моделей + выбор модели через UI (20.04.2026)

**PR-1 / Сломанные LLM-модели**

- Groq: `mixtral-8x7b-32768` удалена на стороне провайдера (2025-03-20) → 400 Bad Request на каждом запросе. Заменена на `llama-3.3-70b-versatile`.
- OpenRouter: `mistralai/mistral-7b-instruct` удалена → 404 Not Found. Заменена на `meta-llama/llama-3.3-70b-instruct:free`. Убрана платная `anthropic/claude-3-haiku`.
- `_map_model_to_provider`: маппинги `planner`/`default` обновлены.
- `bot.py / _register_kb_refresh_cron`: `ScheduledTask.status` не существует как колонка → `AttributeError` при старте → KB cron не регистрировался. Убран фильтр по `status`.

**PR-2 / Выбор модели через интерфейс бота**

- `/providers` — новое меню: статус провайдеров, текущие модели по ролям.
- Навигация: `providers:show` → `providers:models` → `providers:set` (выбор по индексу).
- `providers:refresh` — health check из UI.
- `llm_client_v2.set_model()` — in-memory оверрайд с приоритетом над статическим маппингом.
- `llm_client_v2.get_models_info()` — данные для UI.

**Известное ограничение:** оверрайды моделей не персистентны (сбрасываются при рестарте).

---

### v1.4.0 — Knowledge Base + аудит хендлеров (19.04.2026)

**Knowledge Base скилл:**
- Автосбор статей из Telegram-канала через `channel_post`
- SQLite `knowledge_base.db` + ChromaDB, граф связей (jaccard), cron 03:00

**Аудит — критические баги:**
- BUG-1: `scheduler.py` — `AttributeError` при каждом срабатывании задачи
- BUG-2: `skills.py` — `callback.answer()` без await, вечный spinner
- BUG-3: два независимых `MultiProviderLLMClient` — hot-swap не работал

**Аудит — хендлеры:**
- `settings:*` callbacks, `sanitize_html`, `parse_time_input`, дубль `check_callback_access`, `action:cancel` FSM-роутинг, `memory.py` access guard, `reminders.py` reminder_type

---

### v1.3.0 — Multi-provider + Scheduler + Voice (08.02.2026)
- Groq Whisper, APScheduler, `/remind` /daily` /weekly`

### v1.2.0 — Hot-swap + Security (февраль 2026)
- `/providers` FSM, Fernet, ProviderConfig, BOT_TIMEZONE, access control

### v1.1.0 — Русификация (07.02.2026)

### v1.0.0 — Initial (февраль 2026)
- 3 агента, ChromaDB, навыки, Docker Compose

---

## 📋 Pending

| ID | Задача | Приоритет |
|----|--------|-----------|
| P-2 | `tests/test_bot.py` — patch consumers, conftest с mock env | medium |
| P-3 | `handle_photo` — `aiohttp` → `httpx` | medium |
| P-4 | Vision-модель в `settings` (захардкожена в `messages.py`) | low |
| P-5 | `asyncio.gather` для параллельных skills в агентах | low |
| P-6 | OpenClaw `ToolExecutor` как протокол для `skills_loader` | low |
| P-7 | Персистентность оверрайдов `set_model` через `ProviderConfig` | low |

---

## 🔧 Текущая конфигурация

**LLM singleton:** `app.core.llm_client_v2.llm_client` (`MultiProviderLLMClient`)
**Провайдеры:** Groq p1 → OpenRouter p2 → Anthropic p3 → OpenAI p4
**Groq модели:** `llama-3.1-8b-instant` (default/coder), `llama-3.3-70b-versatile` (planner)
**OpenRouter модели:** `llama-3.3-70b-instruct:free` (default/planner), `llama-3.1-8b-instruct:free` (coder)
**Timezone:** `settings.BOT_TIMEZONE` (рекомендуется `Asia/Irkutsk`)
**Access control:** `get_allowed_users()` → `settings.ADMIN_IDS`
**FSM-состояния:** `app/utils/states.py`
**Ключи провайдеров:** Fernet-encrypted в `provider_configs`, загружаются при старте

**Деплой (важно — COPY в образ, не volume mount):**
```bash
docker compose build alex-nano-bot && docker compose up -d alex-nano-bot
```

# Прогресс разработки Alex-Nano-Bot

## Последнее обновление: 19.04.2026 — v1.4.0

---

## ✅ Выполнено

### v1.4.0 — Аудит и патч критических багов (19.04.2026)

**BUG-1 / `scheduler.py` — `AttributeError` при выполнении задач**

Дефект: `select(get_or_create_user.__self__)` — функция `__self__` не имеет, `AttributeError` при каждом срабатывании любого запланированного задания.

Фикс: удалён битый блок, остался только рабочий `select(User).where(User.id == task.user_id)`.

**BUG-2 / `handlers/skills.py` — `callback.answer()` без `await`**

Дефект: `check_callback_access()` — синхронная функция, внутри `callback.answer(...)` вызывался без `await`. Coroutine создавалась и немедленно уничтожалась, пользователь получал вечный spinner на кнопке.

Фикс: `async def check_callback_access()`, `await callback.answer(...)`, все вызовы обёрнуты в `await`.

**BUG-3 / Два независимых `MultiProviderLLMClient`**

Дефект: `llm_client.py` (v1 wrapper) создавал `self._client = MultiProviderLLMClient()` — **новый экземпляр**, независимый от глобального `llm_client_v2.llm_client`. Итого в процессе жили два объекта. `_load_provider_configs_from_db()` и `/providers` hot-swap меняли ключи в одном, агенты читали из другого — hot-swap фактически не работал.

Фикс: `llm_client.py` **удалён**. Все 9 точек импорта переведены на `from app.core.llm_client_v2 import llm_client`. Добавлены методы в v2: `chat_with_fallback()` (алиас), `stream_chat()` (stub), `check_health()` (публичный).

**Попутно:**
- `create_interval_task` — добавлен пропущенный `timezone=settings.BOT_TIMEZONE`
- `ReminderStates` перенесён из `reminders.py` в `states.py`
- `providers.py`: `_check_providers_health()` → `check_health()`
- `bot.py`: убран вызов несуществующего `llm_client.close()`

Изменено файлов: 13. Удалено: 1 (`app/core/llm_client.py`).

---

### v1.3.0 — Multi-provider + Scheduler + Voice (08.02.2026)

- Голосовые сообщения через Groq Whisper API
- `llm_client_v2.py`: Groq→OpenRouter→Anthropic→OpenAI, health-monitor, pending tasks
- APScheduler: `/remind`, `/daily`, `/weekly`, `/tasks`, `/cancel_task`, `/scheduler_stats`
- Восстановление задач после перезапуска из БД

### v1.2.0 — Hot-swap + Security (февраль 2026)

- `/providers` FSM: 3 стейта, Fernet-шифрование, DB-persistence
- `crypto.py`: `encrypt_key()` / `decrypt_key()` / `mask_key()`
- `ProviderConfig` таблица, `_load_provider_configs_from_db()` при старте
- `BOT_TIMEZONE` в settings — единый источник для scheduler и reminders
- `get_allowed_users()` во всех 5 хендлерах, хардкод ID удалён
- Anthropic API fix: `/v1/messages`, `x-api-key`, `system` как top-level param

### v1.1.0 — Русификация (07.02.2026)

- Все хендлеры, клавиатуры, system prompts агентов на русском
- Прямое подключение к Groq API
- Логирование кнопок меню

### v1.0.0 — Initial (февраль 2026)

- 3 агента: Nanobot / Claudbot / Moltbot
- ChromaDB + fastembed, коллекции memories/skills/conversations
- Динамические навыки, SQLite + SQLAlchemy async, Docker Compose

---

## 📋 Pending

| ID | Задача | Приоритет |
|----|--------|-----------|
| P-2 | `tests/test_bot.py` — patch consumers, не sources; conftest с mock env | medium |
| P-3 | `handle_photo` — `aiohttp` → `httpx` | medium |
| P-4 | Vision-модель в `settings` | low |
| P-5 | `asyncio.gather` для параллельных skills в агентах | low |
| P-6 | OpenClaw `ToolExecutor` как протокол для `skills_loader` | low |

---

## 🔧 Текущая конфигурация

**LLM singleton:** `app.core.llm_client_v2.llm_client` (`MultiProviderLLMClient`)  
**Провайдеры:** Groq p1 → OpenRouter p2 → Anthropic p3 → OpenAI p4  
**Timezone:** `settings.BOT_TIMEZONE` (рекомендуется `Asia/Irkutsk`)  
**Access control:** `get_allowed_users()` → `settings.ADMIN_IDS` (не кэшируется)  
**FSM-состояния:** все в `app/utils/states.py`  
**Ключи провайдеров:** Fernet-encrypted в `provider_configs`, загружаются при старте  

**Деплой:**
```bash
docker compose down && docker compose up -d --build
docker compose logs -f bot
```

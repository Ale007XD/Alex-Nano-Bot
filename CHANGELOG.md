# Changelog

All notable changes to Alex-Nano-Bot will be documented in this file.

## [1.4.0] - 2026-04-19

### Fixed — критические баги
- **`scheduler.py`**: удалён битый блок `select(get_or_create_user.__self__)`, который
  бросал `AttributeError` при каждом выполнении запланированной задачи. Остался
  только рабочий `select(User).where(User.id == task.user_id)`.
- **`handlers/skills.py`**: `check_callback_access()` переведена в `async def`;
  `callback.answer()` теперь корректно awaited — ранее coroutine игнорировалась
  и пользователь получал вечный spinner на кнопке.
- **Два экземпляра `MultiProviderLLMClient`**: `llm_client.py` (v1 wrapper) удалён.
  Все агенты, хендлеры и `bot.py` теперь импортируют единственный singleton из
  `app/core/llm_client_v2.py`. До этого `_load_provider_configs_from_db()` и
  `/providers` hot-swap применяли ключи к одному экземпляру, а агенты
  использовали другой — независимый, всегда с ключами из `.env`.

### Added — `llm_client_v2.py`
- `chat_with_fallback()` — семантический алиас `chat()` для обратной совместимости
  с агентами, мигрировавшими с v1 wrapper.
- `stream_chat()` — async-generator stub с корректным интерфейсом; реальный
  стриминг подключается без смены API у агентов.
- `check_health()` — публичный метод вместо `_check_providers_health()`;
  `providers.py` теперь не обращается к приватному методу.

### Fixed — мелкие
- `scheduler.py` → `create_interval_task()`: добавлен `timezone=settings.BOT_TIMEZONE`
  (был пропущен в отличие от `create_reminder` и `create_recurring_task`).
- `handlers/providers.py`: `_check_providers_health()` → `check_health()`.
- `bot.py`: убран вызов несуществующего `llm_client.close()` в `on_shutdown`.

### Refactored
- `app/utils/states.py`: `ReminderStates` перенесён из `reminders.py` —
  единственный источник истины для всех FSM-состояний.
- `reminders.py`: удалён локальный `class ReminderStates(StatesGroup)` и
  мёртвый импорт `from aiogram.fsm.state import State, StatesGroup`.

---

## [1.3.0] - 2026-02-08

### Added
- Голосовые сообщения: транскрибация через Groq Whisper API, работа в группах,
  автоочистка временных файлов, лимит 300 сек.
- Multi-provider LLM v2 (`llm_client_v2.py`): Groq→OpenRouter→Anthropic→OpenAI,
  health-monitor, pending tasks, статистика провайдеров.
- APScheduler: `/remind`, `/daily`, `/weekly`, `/tasks`, `/cancel_task`,
  `/scheduler_stats`, восстановление задач после рестарта.

---

## [1.2.0] - 2026-02

### Added
- Hot-swap провайдеров через `/providers` (FSM, Fernet-шифрование, DB persistence).
- `app/core/crypto.py`: `encrypt_key()`, `decrypt_key()`, `mask_key()`.
- `ProviderConfig` таблица в БД; `_load_provider_configs_from_db()` при старте.
- `BOT_TIMEZONE` в `settings` — единый источник для scheduler и reminders.
- `get_allowed_users()` во всех 5 handler-файлах, хардкод ID удалён.
- Исправлен Anthropic-провайдер: `/v1/messages`, `x-api-key`, `system` top-level.

---

## [1.1.0] - 2026-02-07

### Added
- Перевод интерфейса на русский язык (хендлеры, клавиатуры, агенты).
- Прямое подключение к Groq API вместо OpenRouter-прокси.
- Логирование кнопок меню для отладки.

---

## [1.0.0] - 2026-02

### Added
- Три агента: Nanobot, Claudbot, Moltbot.
- Векторная память: ChromaDB + fastembed, коллекции memories/skills/conversations.
- Динамические навыки: system/custom/external, создание из чата.
- SQLite + SQLAlchemy async.
- Docker Compose, GitHub Actions.

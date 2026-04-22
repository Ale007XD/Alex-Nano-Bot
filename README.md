# Alex-Nano-Bot

Приватный self-hosted Telegram AI-бот с детерминированным Program-driven рантаймом, векторной памятью, базой знаний и multi-provider LLM.

**Версия:** 1.5.0 · **Готовность к релизу:** ~88%

---

## Возможности

🤖 **Три агента (white-label):**
- ⚡ **FastBot** *(ex-Nanobot)* — быстрый помощник для повседневных задач, веб-поиск, RAG из переписки
- 🧩 **PlanBot** *(ex-Claudbot)* — умный планировщик с многошаговым рассуждением и верификацией
- 🔧 **SkillBot** *(ex-Moltbot)* — менеджер навыков, генерация кода, поиск по каталогу

⚙️ **Runtime VM (новое):**
- Детерминированная Program-driven система δ(S, Program) → S'
- Planner генерирует JSON-программу через LLM (llama-3.3-70b-versatile)
- VM исполняет программу по шагам: `call_llm`, `respond`, `store_memory`, `call_tool`
- Персистентный `StateContext` через `UserState.context` (JSON Column)
- Fallback-программа при невалидном JSON от Planner
- Персистентный `StateContext`: `from_db()` / `to_db_context()` ↔ `UserState.context` (JSON Column) — верифицировано в проде
- Переключение: `/mode` → ⚙️ Runtime VM

🧠 **Векторная память (RAG):**
- Хранение заметок, поездок, бюджетов, планов
- Семантический поиск через ChromaDB + fastembed
- Импорт и поиск по истории Telegram-чатов

📚 **База знаний:**
- Автосбор статей из Telegram-канала через `channel_post`
- SQLite (articles + граф связей) + ChromaDB
- Команды `kb search`, `kb related`, `kb stats` и другие
- Ежедневный cron-refresh устаревших статей

🔌 **Multi-provider LLM с hot-swap:**
- Groq (p1) → OpenRouter (p2) → Anthropic (p3) → OpenAI (p4)
- Автоматический fallback при ошибках
- Смена моделей без рестарта через `/providers`
- Ключи хранятся Fernet-зашифрованными в БД

🎙 **Голосовые сообщения:**
- Транскрибация через Groq Whisper API
- Работа в личных чатах и группах

⏰ **Планировщик задач (APScheduler):**
- Одноразовые напоминания, ежедневные и еженедельные задачи
- Cron-выражения, восстановление после перезапуска

📷 **Обработка изображений:**
- Vision через Groq (llama-4-scout)
- Self-check для идентификационных запросов

---

## Быстрый старт

### Требования
- Docker & Docker Compose
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))
- Groq API Key (первичный провайдер, бесплатно)
- OpenRouter API Key (fallback, бесплатные модели)

### Установка

```bash
git clone https://github.com/Ale007XD/Alex-Nano-Bot.git
cd Alex-Nano-Bot
cp .env.example .env
```

Заполнить `.env`:

```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=your_telegram_id
GROQ_API_KEY=your_groq_key
OPENROUTER_API_KEY=your_openrouter_key

# Обязательно для /providers:
ENCRYPTION_KEY=  # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Временная зона (IANA):
BOT_TIMEZONE=Asia/Irkutsk

# Опционально — база знаний:
KB_CHANNEL_IDS=-100xxxxxxxxxx   # ID канала(ов) через запятую
KB_STALE_DAYS=30
```

```bash
docker compose build && docker compose up -d
docker compose logs -f
```

> ⚠️ **Важно:** бот использует `COPY` в Docker-образ. При изменении кода всегда выполняй `docker compose build` перед `up`.

---

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Запуск бота |
| `/help` | Справка |
| `/mode` | Смена агента (FastBot / PlanBot / SkillBot / Runtime VM) |
| `/skills` | Менеджер навыков |
| `/memory` | Управление памятью |
| `/clear` | Очистить историю разговора |
| `/remind` | Создать напоминание |
| `/daily` | Ежедневная задача |
| `/weekly` | Еженедельная задача |
| `/tasks` | Список активных задач |
| `/cancel_task <id>` | Отменить задачу |
| `/scheduler_stats` | Статистика планировщика |
| `/providers` | Управление LLM-провайдерами и моделями (admin) |

---

## CI/CD

GitHub Actions: 
- Python 3.12, ubuntu-latest
- Запускается при push/PR в 
- Команда: ============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /
plugins: asyncio-1.3.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 0 items

============================ no tests ran in 0.00s =============================
- ⚠️ Статус: **красный** (BUG-4:  сломан —  не реализован)

---

## Управление провайдерами (`/providers`)

Без рестарта:
- просмотр статуса провайдеров (🟢/🟡/🔴) и текущих моделей
- смена модели для роли `default / coder / planner` через инлайн-меню
- обновление API-ключа любого провайдера
- включение/отключение провайдера
- запуск health check

Текущие модели:

| Провайдер | default | coder | planner |
|-----------|---------|-------|---------|
| groq | llama-3.1-8b-instant | llama-3.1-8b-instant | llama-3.3-70b-versatile |
| openrouter | llama-3.3-70b-instruct:free | llama-3.1-8b-instruct:free | llama-3.3-70b-instruct:free |
| anthropic | claude-3-5-sonnet-20241022 | — | — |
| openai | gpt-3.5-turbo | — | gpt-4o-mini |

> Оверрайды моделей хранятся in-memory — сбрасываются при рестарте (P-7).

---

## Runtime VM

Детерминированная система поверх LLM. Переключается через `/mode` → ⚙️ Runtime VM.

```
User input → Planner (70b) → Program (JSON) → VM → StepResult[] → Response
                                                ↓
                                         StateContext (персистентный)
```

**DSL v0.1 — поддерживаемые инструкции:**

| Инструкция | Описание |
|------------|----------|
| `call_llm` | Вызов LLM с заданной ролью и промптом |
| `respond` | Отправка сообщения пользователю |
| `store_memory` | Запись в ChromaDB через VectorMemory |
| `call_tool` | Вызов зарегистрированного навыка |

**on_error:** `abort` (дефолт) или `continue` на каждом шаге.
**$ref:** `$step_id` — ссылка на `output` предыдущего шага, рекурсивный resolve (dict + list).

Компоненты (`app/runtime/`):

| Файл | Ответственность |
|------|----------------|
| `state_context.py` | `StateContext` (frozen Pydantic), `MemorySnapshot`, `OutboxEntry` |
| `llm_adapter.py` | `LLMProtocol`, `MultiProviderLLMAdapter`, `MockLLMAdapter` |
| `context.py` | `VMContext`: state, llm, memory, tools, variables |
| `vm.py` | `ExecutionVM`, `VMRunResult` — on_error, recursive resolve |
| `planner.py` | `Planner.generate(user_input, history)` → Program |
| `step_result.py` | `StepResult` (frozen), `StepMeta` |
| `builder.py` | `StepResultBuilder` |
| `registry.py` | `InstructionRegistry` |
| `instructions/` | `call_llm`, `call_tool`, `respond`, `store_memory` |

---

## Структура проекта

```
Alex-Nano-Bot/
├── app/
│   ├── agents/               # Агенты (FastBot, PlanBot, SkillBot)
│   │   ├── fastbot.py        # ex-nanobot
│   │   ├── planbot.py        # ex-claudbot
│   │   ├── skillbot.py       # ex-moltbot
│   │   └── router.py
│   ├── core/                 # Ядро
│   │   ├── config.py
│   │   ├── crypto.py
│   │   ├── database.py
│   │   ├── llm_client_v2.py
│   │   ├── memory.py
│   │   ├── scheduler.py
│   │   ├── skills_loader.py
│   │   └── web_search.py
│   ├── runtime/              # Program-driven VM (MFDBA-Lite)
│   │   ├── __init__.py
│   │   ├── state_context.py
│   │   ├── llm_adapter.py
│   │   ├── context.py
│   │   ├── vm.py
│   │   ├── planner.py
│   │   ├── step_result.py
│   │   ├── builder.py
│   │   ├── registry.py
│   │   └── instructions/
│   │       ├── base.py
│   │       ├── call_llm.py
│   │       ├── call_tool.py
│   │       ├── respond.py
│   │       └── store_memory.py
│   ├── handlers/
│   │   ├── commands.py
│   │   ├── messages.py       # runtime branch: if agent_mode == 'runtime'
│   │   ├── channel.py
│   │   ├── providers.py
│   │   ├── reminders.py
│   │   ├── skills.py
│   │   └── memory.py
│   ├── utils/
│   │   ├── keyboards.py
│   │   ├── states.py
│   │   └── helpers.py
│   ├── bot.py
│   └── __init__.py
├── skills/
│   ├── system/
│   ├── custom/
│   └── external/
├── data/
├── logs/
├── tests/
│   ├── conftest.py           # sys.modules patching, fixtures
│   ├── test_runtime.py       # 51 тест runtime VM (passed)
│   ├── test_mfdba_core.py    # тесты OpenClaw (BROKEN — BUG-4)
│   └── test_bot.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Архитектура LLM

Единственный `MultiProviderLLMClient` singleton в `app/core/llm_client_v2.py`:

```python
from app.core.llm_client_v2 import llm_client, Message
```

Порядок fallback: Groq → OpenRouter → Anthropic → OpenAI.
Health-monitor стартует лениво при первом `chat()`.
Оверрайды моделей: `llm_client.set_model(provider, role, idx)`.

VM зависит от `LLMProtocol` (structural typing), не от `MultiProviderLLMClient` напрямую — `MockLLMAdapter` для тестов.

---

## Переменные окружения

| Переменная | Обязательная | По умолчанию | Описание |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | — | Telegram Bot Token |
| `ADMIN_IDS` | ✅ | — | ID администраторов (через запятую) |
| `GROQ_API_KEY` | ✅ | — | Groq API (primary LLM + Whisper) |
| `OPENROUTER_API_KEY` | ✅ | — | OpenRouter (fallback, free models) |
| `ANTHROPIC_API_KEY` | — | — | Anthropic Claude (опционально) |
| `OPENAI_API_KEY` | — | — | OpenAI (опционально) |
| `ENCRYPTION_KEY` | ✅ для /providers | — | Fernet key |
| `BOT_TIMEZONE` | — | `Europe/Moscow` | IANA timezone |
| `KB_CHANNEL_IDS` | — | — | ID каналов для базы знаний |
| `KB_STALE_DAYS` | — | `30` | Дней до устаревания статьи |
| `DATABASE_URL` | — | `sqlite+aiosqlite:///data/bot.db` | |
| `VECTOR_STORE_PATH` | — | `data/vector_store` | |
| `ENABLE_WEB_SEARCH` | — | `true` | |
| `LOG_LEVEL` | — | `INFO` | |

---

## Деплой на VPS

```bash
rsync -av --exclude='data/' --exclude='logs/' --exclude='.env' \
  ./ user@host:~/my-bots/Alex-Nano-Bot/

cd ~/my-bots/Alex-Nano-Bot
docker compose build alex-nano-bot && docker compose up -d alex-nano-bot
docker compose logs -f alex-nano-bot
```

---

## Безопасность

- Бот приватный: доступ только для `ADMIN_IDS`
- API-ключи хранятся Fernet-зашифрованными в БД
- Сообщение с ключом удаляется сразу после считывания
- В чате показываются только последние 4 символа ключа
- `ENCRYPTION_KEY` не попадает в логи pydantic
- PII не в логах — только `user_id` (152-ФЗ)

---

## Стратегическая дорожная карта (MFDBA)

```
Telegram Gateway
      ↓
  Bot Core (aiogram)
      ↓
 Agent Router
  ├── FastBot  ──→  MFDBA-Lite  (low latency, sequential)
  ├── PlanBot  ──→  MFDBA-DAG   (graph, reflection, Redis queue)
  └── SkillBot ──→  OpenClaw ToolExecutor (strict JSON schemas)
```

Цель: декаплинг ядра от Telegram-монолита → омниканальная архитектура (Telegram как один из Gateway).

---

## Поддержать проект

- **Telegram:** [@Ale007XD](https://t.me/Ale007XD)
- **TON:** `UQD...` *(добавить адрес)*
- **СБП / Тинькофф:** *(добавить)*

---

## Лицензия

MIT — см. файл LICENSE.

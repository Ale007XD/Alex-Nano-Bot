# Alex-Nano-Bot

Приватный self-hosted Telegram AI-бот с динамическими навыками, векторной памятью, базой знаний и multi-provider LLM.

**Версия:** 1.5.0 · **Готовность к релизу:** ~72%

---

## Возможности

🤖 **Три агента:**
- ⚡ **Nanobot** — быстрый помощник для повседневных задач, веб-поиск, RAG из переписки
- 🧩 **Claudbot** — умный планировщик с многошаговым рассуждением и верификацией
- 🔧 **Moltbot** — менеджер навыков, генерация кода, поиск по каталогу

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
| `/mode` | Смена агента |
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

> Оверрайды моделей хранятся in-memory — сбрасываются при рестарте.

---

## Структура проекта

```
Alex-Nano-Bot/
├── app/
│   ├── agents/               # Агенты
│   │   ├── nanobot.py
│   │   ├── claudbot.py
│   │   ├── moltbot.py
│   │   └── router.py
│   ├── core/                 # Ядро
│   │   ├── config.py         # Settings (pydantic-settings)
│   │   ├── crypto.py         # Fernet-шифрование ключей
│   │   ├── database.py       # SQLAlchemy async + модели
│   │   ├── llm_client_v2.py  # MultiProviderLLMClient (singleton)
│   │   ├── memory.py         # ChromaDB RAG
│   │   ├── scheduler.py      # APScheduler
│   │   ├── skills_loader.py  # Динамическая загрузка навыков
│   │   └── web_search.py     # Поиск в интернете
│   ├── handlers/             # Telegram-хендлеры
│   │   ├── commands.py       # /start, /help, /mode, /providers ...
│   │   ├── messages.py       # Текст, фото, документы, голос
│   │   ├── channel.py        # channel_post → knowledge_base
│   │   ├── providers.py      # /providers FSM (ключи)
│   │   ├── reminders.py      # /remind, /daily, /weekly ...
│   │   ├── skills.py         # Управление навыками
│   │   └── memory.py         # Управление памятью
│   ├── utils/
│   │   ├── keyboards.py      # Все клавиатуры
│   │   ├── states.py         # Все FSM StatesGroup
│   │   └── helpers.py        # sanitize_html, parse_time_input, format_memory
│   ├── bot.py                # Точка входа
│   └── __init__.py
├── skills/
│   ├── system/               # calculator, echo, reminder
│   ├── custom/               # knowledge_base, import_chat, youtube_transcript, validated_answer
│   └── external/
├── data/                     # bot.db, knowledge_base.db, vector_store/
├── logs/
├── tests/
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
| `KB_CHANNEL_IDS` | — | — | ID каналов для базы знаний (через запятую) |
| `KB_STALE_DAYS` | — | `30` | Дней до устаревания статьи |
| `DATABASE_URL` | — | `sqlite+aiosqlite:///data/bot.db` | |
| `VECTOR_STORE_PATH` | — | `data/vector_store` | |
| `ENABLE_WEB_SEARCH` | — | `true` | |
| `LOG_LEVEL` | — | `INFO` | |

---

## Деплой на VPS

```bash
# Копировать изменённые файлы:
rsync -av --exclude='data/' --exclude='logs/' --exclude='.env' \
  ./ user@host:~/Alex-Nano-Bot/

# Пересборка и запуск (ОБЯЗАТЕЛЬНО build — код в образе):
cd ~/Alex-Nano-Bot
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

---

## Поддержать проект

Если бот оказался полезным — можно угостить разработчика ☕🍩🍺

- **Telegram:** [@Ale007XD](https://t.me/Ale007XD)
- **TON:** `UQD...` *(добавить адрес)*
- **СБП / Тинькофф:** *(добавить)*

Любая поддержка мотивирует продолжать разработку.

---

## Лицензия

MIT — см. файл LICENSE.

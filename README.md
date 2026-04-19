# Alex-Nano-Bot

Приватный self-hosted Telegram AI-бот с динамическими навыками, векторной памятью и multi-provider LLM.

## Возможности

🤖 **Три агента:**
- ⚡ **Nanobot** — быстрый помощник для повседневных задач, веб-поиск, RAG из переписки
- 🧩 **Claudbot** — умный планировщик с многошаговым рассуждением и верификацией
- 🔧 **Moltbot** — менеджер навыков, генерация кода, поиск по каталогу

🧠 **Векторная память (RAG):**
- Хранение заметок, поездок, бюджетов, планов
- Семантический поиск через ChromaDB + fastembed
- Импорт и поиск по истории Telegram-чатов
- Контекстно-зависимые ответы

🛠 **Динамические навыки:**
- Создание навыков из чата
- Системные навыки (calculator, echo, reminder)
- Пользовательские и внешние навыки
- Автодетект YouTube-ссылок → транскрипт

🔌 **Multi-provider LLM с hot-swap:**
- Провайдеры: Groq (p1) → OpenRouter (p2) → Anthropic (p3) → OpenAI (p4)
- Автоматический fallback при ошибках
- Смена ключей без рестарта через `/providers`
- Ключи хранятся Fernet-зашифрованными в БД

🎙 **Голосовые сообщения:**
- Транскрибация через Groq Whisper API
- Работа в личных чатах и группах
- Ответ агента на расшифрованный текст

⏰ **Планировщик задач (APScheduler):**
- Одноразовые напоминания (`/remind`)
- Ежедневные и еженедельные задачи
- Cron-выражения
- Восстановление задач после перезапуска

📷 **Обработка изображений:**
- Vision через Groq (llama-4-scout)
- Self-check для идентификационных запросов

## Быстрый старт

### Требования

- Docker & Docker Compose
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))
- Groq API Key (первичный провайдер, бесплатно)
- OpenRouter API Key (fallback)

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
```

```bash
docker compose up -d --build
docker compose logs -f
```

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
| `/providers` | Управление LLM-провайдерами (admin) |

## Управление провайдерами (`/providers`)

Позволяет без рестарта:
- обновить API-ключ любого провайдера
- включить/отключить провайдера
- сменить основной провайдер (Set Primary)

Ключи хранятся зашифрованными (Fernet) в таблице `provider_configs`. При старте бот автоматически подтягивает сохранённые ключи из БД.

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
│   │   ├── commands.py       # /start, /help, /mode, ...
│   │   ├── messages.py       # Текст, фото, документы, голос
│   │   ├── providers.py      # /providers FSM
│   │   ├── reminders.py      # /remind, /daily, /weekly, ...
│   │   ├── skills.py         # Управление навыками
│   │   └── memory.py         # Управление памятью
│   ├── utils/
│   │   ├── keyboards.py
│   │   ├── states.py         # Все FSM StatesGroup
│   │   └── helpers.py
│   ├── bot.py                # Точка входа
│   └── __init__.py
├── skills/
│   ├── system/               # Системные навыки
│   ├── custom/               # Пользовательские
│   └── external/             # Внешние
├── data/                     # БД + векторное хранилище
├── logs/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Архитектура LLM

Единственный `MultiProviderLLMClient` singleton живёт в `app/core/llm_client_v2.py`.
Все агенты и хендлеры импортируют его напрямую:

```python
from app.core.llm_client_v2 import llm_client, Message
```

Порядок fallback: Groq → OpenRouter → Anthropic → OpenAI.
Health-monitor стартует лениво при первом `chat()` вызове.

## Переменные окружения

| Переменная | Обязательная | По умолчанию | Описание |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | — | Telegram Bot Token |
| `ADMIN_IDS` | ✅ | — | ID администраторов (через запятую) |
| `GROQ_API_KEY` | ✅ | — | Groq API (primary LLM + Whisper) |
| `OPENROUTER_API_KEY` | ✅ | — | OpenRouter (fallback) |
| `ANTHROPIC_API_KEY` | — | — | Anthropic Claude (опционально) |
| `OPENAI_API_KEY` | — | — | OpenAI (опционально) |
| `ENCRYPTION_KEY` | ✅ для /providers | — | Fernet key для шифрования ключей в БД |
| `BOT_TIMEZONE` | — | `Europe/Moscow` | IANA timezone |
| `DATABASE_URL` | — | `sqlite+aiosqlite:///data/bot.db` | |
| `VECTOR_STORE_PATH` | — | `data/vector_store` | |
| `DEFAULT_MODEL` | — | `llama-3.1-8b-instant` | |
| `PLANNER_MODEL` | — | `mixtral-8x7b-32768` | |
| `ENABLE_WEB_SEARCH` | — | `true` | |
| `LOG_LEVEL` | — | `INFO` | |

## Деплой на VPS

```bash
# Обновление кода:
rsync -av --exclude='data/' --exclude='logs/' --exclude='.env' \
  ./ user@host:~/Alex-Nano-Bot/

# Перезапуск:
docker compose down && docker compose up -d --build
docker compose logs -f bot
```

## Разработка

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # заполнить
python -m app.bot
```

```bash
pytest tests/ -v
```

## Безопасность

- Бот приватный: доступ только для `ADMIN_IDS`
- API-ключи в БД хранятся Fernet-зашифрованными
- Сообщение с ключом удаляется немедленно после считывания
- В чате показываются только последние 4 символа ключа
- `ENCRYPTION_KEY` не попадает в логи pydantic

## Лицензия

MIT — см. файл LICENSE.

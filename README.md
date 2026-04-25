# Alex-Nano-Bot

Приватный self-hosted Telegram AI-бот с детерминированным Program-driven рантаймом, векторной памятью, базой знаний и multi-provider LLM.

**Версия:** 1.5.0 (patch 6) · **Готовность к релизу:** ~88%

---

## Возможности

🤖 **Три агента:**
- ⚡ **FastBot** — быстрый помощник, RAG из переписки
- 🧩 **PlanBot** — многошаговое рассуждение с верификацией
- 🔧 **SkillBot** — менеджер навыков, генерация кода

⚙️ **Runtime VM:**
- Детерминированная Program-driven система δ(S, Program) → S'
- Planner (llama-3.3-70b) генерирует JSON-программу
- VM исполняет: `call_llm`, `respond`, `store_memory`, `call_tool`
- Векторная память (ChromaDB): сохранение и RAG-поиск работают
- Персистентный `StateContext` через `UserState.context`

🧠 **Векторная память (RAG):**
- ChromaDB + fastembed, 8 релевантных записей с датами в контексте
- `store_memory` через Runtime VM: верифицировано

📚 **База знаний, голос, планировщик, vision** — без изменений.

🔌 **Multi-provider LLM:** Groq → OpenRouter → Anthropic → OpenAI

---

## Быстрый старт

```bash
git clone https://github.com/Ale007XD/Alex-Nano-Bot.git
cd Alex-Nano-Bot
cp .env.example .env
# заполнить .env
docker compose build && docker compose up -d
docker compose logs -f
```

> ⚠️ Имя сервиса в docker-compose: `bot`. Команды: `docker compose build bot && docker compose up -d bot`

---

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Запуск |
| `/mode` | Смена агента (FastBot / PlanBot / SkillBot / Runtime VM) |
| `/skills` | Менеджер навыков |
| `/memory` | Управление памятью |
| `/providers` | Управление LLM (admin) |
| `/remind`, `/daily`, `/weekly`, `/tasks` | Планировщик |
| `/clear` | Очистить историю |

---

## Runtime VM

```
User input → Planner (70b) → Program (JSON) → VM → StepResult[] → Response
                                                ↓
                                         StateContext (персистентный)
                                                ↓
                                    store_memory → ChromaDB
```

**DSL v0.1:** `call_llm`, `respond`, `store_memory`, `call_tool`  
**RAG:** 8 memories + даты → `_ensure_rag_in_system` → `call_llm.params.system`

---

## Структура проекта

```
Alex-Nano-Bot/
├── app/
│   ├── agents/               # FastBot, PlanBot, SkillBot, router
│   ├── core/                 # config, database, llm_client_v2, memory, scheduler, skills_loader
│   ├── runtime/              # VM, Planner, StateContext, instructions/
│   │   └── instructions/     # call_llm, call_tool, respond, store_memory
│   ├── handlers/             # commands, messages, providers, skills, memory, channel, reminders
│   ├── utils/                # keyboards, states, helpers
│   └── bot.py
├── skills/system/ custom/ external/
├── data/                     # bot.db, vector_store/ (volume-mounted)
├── logs/                     # (volume-mounted)
├── tests/                    # conftest, test_runtime (60), test_mfdba_core (2), test_bot (17)
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## CI/CD

GitHub Actions · Python 3.12 · `python -m pytest tests/ -q` · **79/79 passed 🟢**

---

## Переменные окружения

| Переменная | Обязательная | По умолчанию |
|---|---|---|
| `BOT_TOKEN` | ✅ | — |
| `ADMIN_IDS` | ✅ | — |
| `GROQ_API_KEY` | ✅ | — |
| `OPENROUTER_API_KEY` | ✅ | — |
| `ANTHROPIC_API_KEY` | — | — |
| `OPENAI_API_KEY` | — | — |
| `ENCRYPTION_KEY` | ✅ для /providers | — |
| `BOT_TIMEZONE` | — | `Europe/Moscow` |
| `DATABASE_URL` | — | `sqlite+aiosqlite:///data/bot.db` |
| `VECTOR_STORE_PATH` | — | `data/vector_store` |

---

## Деплой на VPS

```bash
rsync -av --exclude='data/' --exclude='logs/' --exclude='.env' \
  ./ user@host:~/my-bots/Alex-Nano-Bot/

cd ~/my-bots/Alex-Nano-Bot
docker compose build bot && docker compose up -d bot
docker compose logs -f
```

---

## Безопасность

- Приватный бот: только `ADMIN_IDS`
- API-ключи Fernet-зашифрованы в БД
- PII не в логах — только `user_id`

---

## Лицензия

MIT

# Alex-Nano-Bot 

Advanced self-hosted Telegram AI bot with dynamic skills and vector memory.

## Features

🤖 **Three Agent Modes:**
- ⚡ **Nanobot** - Quick universal assistant for everyday tasks
- 🧩 **Claudbot** - Smart planner with multi-step reasoning
- 🔧 **Moltbot** - Skills manager and catalog

🧠 **Vector Memory (RAG):**
- Store notes, trips, budgets, plans
- Semantic search through memories
- Context-aware responses

🛠 **Dynamic Skills System:**
- Create skills from chat
- Load skills dynamically
- Support for system, custom, and external skills

🐳 **Production Ready:**
- Docker & Docker Compose
- SQLite database
- Local vector storage
- Comprehensive logging

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Telegram Bot Token (get from [@BotFather](https://t.me/BotFather))
- OpenRouter API Key (get from [openrouter.ai](https://openrouter.ai/))

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/alex-nano-bot.git
cd alex-nano-bot
```

2. **Create environment file:**
```bash
cp .env.example .env
```

3. **Edit `.env` file with your credentials:**
```env
BOT_TOKEN=your_telegram_bot_token_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
ADMIN_IDS=your_telegram_id_here
```

4. **Start the bot:**
```bash
docker compose up -d --build
```

5. **View logs:**
```bash
docker compose logs -f
```

## Usage

### Commands

- `/start` - Start the bot
- `/help` - Show help message
- `/mode` - Switch agent mode
- `/skills` - Manage skills
- `/memory` - Memory operations
- `/clear` - Clear conversation history
- `/settings` - Bot settings

### Agent Modes

**Nanobot** (⚡ Default)
- Quick responses
- General knowledge
- Everyday tasks
- Fast and efficient

**Claudbot** (🧩)
- Multi-step planning
- Complex problem solving
- Analysis and verification
- Detailed explanations

**Moltbot** (🔧)
- Skills management
- Create custom skills
- Catalog and search
- Code generation

### Creating Skills

1. Switch to 🔧 Moltbot mode or use `/skills`
2. Select "Create Skill"
3. Follow the prompts to name and describe your skill
4. Provide the Python code
5. The skill is immediately available!

Example skill code:
```python
SKILL_NAME = "weather_checker"
SKILL_DESCRIPTION = "Checks weather for a city"
SKILL_CATEGORY = "utility"
SKILL_VERSION = "1.0.0"
SKILL_AUTHOR = "Your Name"
SKILL_COMMANDS = ["/weather"]

import httpx

async def handle_command(command, args, message, bot):
    if command == "weather":
        city = " ".join(args) if args else "London"
        # Your weather API logic here
        await message.reply(f"Weather for {city}: ...")

def setup_handlers():
    return {"weather": handle_command}
```

### Managing Memories

Use the `/memory` command to:
- 📝 Add notes
- ✈️ Record trip details
- 💰 Track budgets
- 📅 Create plans

The bot automatically retrieves relevant memories during conversations.

## Project Structure

```
Alex-Nano-Bot/
├── app/
│   ├── agents/          # Agent implementations
│   │   ├── nanobot.py
│   │   ├── claudbot.py
│   │   ├── moltbot.py
│   │   └── router.py
│   ├── core/            # Core components
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── memory.py
│   │   ├── llm_client.py
│   │   └── skills_loader.py
│   ├── handlers/        # Telegram handlers
│   │   ├── commands.py
│   │   ├── messages.py
│   │   ├── skills.py
│   │   └── memory.py
│   ├── utils/           # Utilities
│   │   ├── keyboards.py
│   │   ├── states.py
│   │   └── helpers.py
│   ├── bot.py          # Main entry point
│   └── __init__.py
├── skills/              # Skills directory
│   ├── system/         # System skills
│   ├── custom/         # User-created skills
│   └── external/       # External skills
├── data/               # Database & vector store
├── logs/               # Application logs
├── tests/              # Test files
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Architecture

### Data Flow

1. **User Message** → Telegram → Bot Handler
2. **Handler** → Route to appropriate Agent
3. **Agent** → Query Vector Memory (RAG)
4. **Agent** → Call LLM via OpenRouter
5. **Response** → Save to Database → User

### Components

- **aiogram 3.x**: Modern async Telegram bot framework
- **SQLAlchemy + aiosqlite**: Async ORM with SQLite
- **ChromaDB + sentence-transformers**: Local vector storage
- **OpenRouter**: Multi-model LLM API access
- **Docker**: Containerized deployment

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | - | Telegram Bot Token |
| `OPENROUTER_API_KEY` | Yes | - | OpenRouter API Key |
| `ADMIN_IDS` | No | - | Admin Telegram IDs |
| `DEFAULT_MODEL` | No | mistralai/mistral-7b-instruct | Default LLM |
| `CODER_MODEL` | No | codellama/codellama-70b-instruct | Code LLM |
| `PLANNER_MODEL` | No | anthropic/claude-3-sonnet | Planning LLM |
| `DATABASE_URL` | No | sqlite+aiosqlite:///data/bot.db | Database URL |
| `LOG_LEVEL` | No | INFO | Logging level |

### Models

The bot uses OpenRouter's free tier models by default:
- **Mistral 7B Instruct**: General conversations
- **CodeLlama 70B**: Code generation
- **Claude 3 Sonnet**: Complex planning

You can configure custom models in `.env`.

## Development

### Local Development

1. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set environment variables:**
```bash
export BOT_TOKEN=your_token
export OPENROUTER_API_KEY=your_key
```

4. **Run the bot:**
```bash
python -m app.bot
```

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
black app/
flake8 app/
mypy app/
```

## Backup & Restore

### Backup

```bash
# Backup data directory
tar -czf backup-$(date +%Y%m%d).tar.gz data/ skills/
```

### Restore

```bash
# Restore from backup
tar -xzf backup-YYYYMMDD.tar.gz
```

## Troubleshooting

### Bot not responding

1. Check logs: `docker compose logs -f`
2. Verify BOT_TOKEN is correct
3. Ensure bot is not blocked by user

### Database errors

1. Check permissions: `ls -la data/`
2. Ensure directory is writable
3. Try removing and recreating: `rm -rf data/*.db`

### LLM errors

1. Verify OPENROUTER_API_KEY
2. Check OpenRouter status
3. Review rate limits

## Security

- Store `.env` file securely
- Don't commit sensitive data
- Use strong API keys
- Keep dependencies updated
- Run with minimal privileges

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- GitHub Issues: [Report bugs](https://github.com/yourusername/alex-nano-bot/issues)
- Telegram: Contact the bot admin

## Acknowledgments

- [aiogram](https://github.com/aiogram/aiogram) - Telegram Bot Framework
- [OpenRouter](https://openrouter.ai/) - LLM API Gateway
- [ChromaDB](https://www.trychroma.com/) - Vector Database
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM

---

Made with ❤️ by the Alex-Nano-Bot Team

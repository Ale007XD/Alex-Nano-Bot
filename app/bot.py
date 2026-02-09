"""
Main bot initialization
"""
import asyncio
import signal
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import settings
from app.core.database import init_db
from app.core.memory import vector_memory
from app.core.skills_loader import skill_loader
from app.core.scheduler import task_scheduler
from app.core.logger import setup_logging
from app.handlers import register_handlers

import logging

logger = setup_logging()


async def on_startup(bot: Bot):
    """Startup handler"""
    logger.info("Starting Alex-Nano-Bot...")
    
    # Initialize database
    logger.info("Initializing database...")
    await init_db()
    
    # Initialize vector memory
    logger.info("Initializing vector memory...")
    await vector_memory.initialize()
    
    # Load skills
    logger.info("Loading skills...")
    await skill_loader.load_all_skills()
    
    # Start scheduler
    logger.info("Starting task scheduler...")
    task_scheduler.set_bot(bot)
    task_scheduler.start()
    
    # Set bot commands
    commands = [
        ("start", "Start the bot"),
        ("help", "Show help message"),
        ("mode", "Switch agent mode"),
        ("skills", "Manage skills"),
        ("memory", "Memory operations"),
        ("clear", "Clear conversation history"),
        ("remind", "Create reminder"),
        ("tasks", "List scheduled tasks"),
        ("daily", "Create daily task"),
        ("weekly", "Create weekly task"),
    ]
    
    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command=cmd, description=desc)
        for cmd, desc in commands
    ])
    
    logger.info("Bot started successfully!")


async def on_shutdown(bot: Bot):
    """Shutdown handler"""
    logger.info("Shutting down...")
    
    # Shutdown scheduler
    logger.info("Shutting down scheduler...")
    task_scheduler.shutdown()
    
    # Close LLM client
    from app.core.llm_client import llm_client
    await llm_client.close()
    
    logger.info("Bot stopped")


async def main():
    """Main entry point"""
    # Initialize bot and dispatcher
    bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register handlers
    register_handlers(dp)
    
    # Register startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Start polling
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

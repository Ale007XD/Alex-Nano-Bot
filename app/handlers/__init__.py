"""
Handler registration
"""
from aiogram import Dispatcher

from app.handlers import commands, messages, skills, memory, reminders


def register_handlers(dp: Dispatcher):
    """Register all handlers"""
    # Include routers
    dp.include_router(commands.router)
    dp.include_router(skills.router)
    dp.include_router(memory.router)
    dp.include_router(reminders.router)  # Reminders and scheduled tasks
    dp.include_router(messages.router)  # Must be last to catch all text

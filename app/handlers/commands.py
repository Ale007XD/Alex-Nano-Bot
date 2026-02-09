"""
Main command handlers
"""
from aiogram import Router, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from app.core.database import async_session_maker, get_or_create_user, save_message
from app.core.config import settings
from app.utils.keyboards import (
    get_main_menu, get_agent_mode_keyboard, get_skills_menu_keyboard,
    get_memory_menu_keyboard, get_settings_keyboard
)
from app.utils.states import AgentMode
from app.agents.router import agent_router
import logging

logger = logging.getLogger(__name__)

router = Router()

# WHITELIST: Only these Telegram IDs can use the bot
ALLOWED_USERS = {195351142}  # <-- Ваш Telegram ID здесь

async def check_access(message: Message) -> bool:
    """Check if user is in whitelist"""
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer(
            "⛔ <b>Доступ запрещен</b>\n\n"
            "Этот бот является приватным. У вас нет прав на использование."
        )
        return False
    return True


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command"""
    # Check whitelist
    if not await check_access(message):
        return
    
    user = message.from_user
    
    async with async_session_maker() as session:
        db_user = await get_or_create_user(
            session,
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code
        )
        
        welcome_text = f"""👋 <b>Добро пожаловать в {settings.APP_NAME}!</b>

Привет, {user.first_name or 'друг'}! Я ваш AI-ассистент с несколькими режимами:

⚡ <b>Nanobot</b> - Быстрый помощник для повседневных задач
🧩 <b>Claudbot</b> - Умный планировщик с логическим мышлением
🔧 <b>Moltbot</b> - Менеджер навыков и каталог

Я могу:
• Хранить и вспоминать ваши воспоминания и заметки
• Создавать и управлять пользовательскими навыками
• Помогать с планированием и анализом
• Запоминать наши разговоры

Используйте меню ниже или введите /help для получения справки!"""
        
        await message.answer(welcome_text, reply_markup=get_main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    if not await check_access(message):
        return
    
    help_text = f"""📖 <b>Справка по {settings.APP_NAME}</b>

<b>🤖 Режимы агентов:</b>
/mode - Переключение между агентами
• <b>Nanobot</b>: Быстрые, повседневные задачи
• <b>Claudbot</b>: Планирование, анализ, логика
• <b>Moltbot</b>: Управление навыками

<b>🛠 Навыки:</b>
/skills - Открыть менеджер навыков
• Просмотр, создание, редактирование навыков
• Импорт внешних навыков
• Запуск команд навыков

<b>🧠 Память:</b>
/memory - Операции с памятью
• Добавление заметок, поездок, бюджетов, планов
• Поиск по воспоминаниям
• Просмотр статистики

<b>⚡ Быстрые команды:</b>
/clear - Очистить историю разговора
/settings - Настройки бота

<b>💬 Чат:</b>
Просто отправьте мне сообщение, и я отвечу в соответствии с активным режимом агента!

<b>📝 Советы:</b>
• Я запоминаю наши разговоры
• У меня есть доступ к вашим сохраненным воспоминаниям
• Переключайте агентов для разных типов задач
• Создавайте пользовательские навыки для повторяющихся задач"""
    
    await message.answer(help_text)


@router.message(Command("mode"))
async def cmd_mode(message: Message, state: FSMContext):
    """Handle /mode command"""
    if not await check_access(message):
        return
    
    await message.answer(
        "🤖 <b>Выберите режим агента:</b>",
        reply_markup=get_agent_mode_keyboard()
    )


@router.callback_query(F.data.startswith("mode:"))
async def process_mode_selection(callback: CallbackQuery, state: FSMContext):
    """Handle agent mode selection"""
    # Check whitelist for callback
    if callback.from_user.id not in ALLOWED_USERS:
        await callback.answer("⛔ Access denied", show_alert=True)
        return
    
    mode = callback.data.split(":")[1]
    
    # Store user mode in database
    async with async_session_maker() as session:
        from sqlalchemy import select
        from app.core.database import UserState
        
        result = await session.execute(
            select(UserState).where(UserState.user_id == callback.from_user.id)
        )
        user_state = result.scalar_one_or_none()
        
        if not user_state:
            user_state = UserState(
                user_id=callback.from_user.id,
                current_agent=mode
            )
            session.add(user_state)
        else:
            user_state.current_agent = mode
        
        await session.commit()
    
    mode_names = {
        "nanobot": "⚡ Nanobot",
        "claudbot": "🧩 Claudbot",
        "moltbot": "🔧 Moltbot"
    }
    
    await callback.message.edit_text(
        f"✅ <b>Режим изменен на:</b> {mode_names.get(mode, mode)}\n\n"
        f"Отправьте мне сообщение, чтобы начать общение!"
    )
    await callback.answer()


@router.message(Command("skills"))
async def cmd_skills(message: Message):
    """Handle /skills command"""
    if not await check_access(message):
        return
    
    await message.answer(
        "🛠 <b>Менеджер навыков</b>\n\n"
        "Управляйте возможностями бота и создавайте новые навыки:",
        reply_markup=get_skills_menu_keyboard()
    )


@router.message(Command("memory"))
async def cmd_memory(message: Message):
    """Handle /memory command"""
    if not await check_access(message):
        return
    
    await message.answer(
        "🧠 <b>Менеджер памяти</b>\n\n"
        "Храните и управляйте вашими воспоминаниями, заметками и информацией:",
        reply_markup=get_memory_menu_keyboard()
    )


@router.message(Command("clear"))
async def cmd_clear(message: Message):
    """Handle /clear command"""
    if not await check_access(message):
        return
    
    # Clear conversation history from memory
    await message.answer(
        "🧹 <b>История разговора очищена!</b>\n\n"
        "Я забыл наш недавний разговор. Давайте начнем сначала!"
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Handle /settings command"""
    if not await check_access(message):
        return
    
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Настройте параметры бота:",
        reply_markup=get_settings_keyboard()
    )


@router.message(F.text.in_(["💬 Чат", "🤖 Режим", "🛠 Навыки", "🧠 Память", "❓ Помощь", "⚙️ Настройки"]))
async def handle_menu_buttons(message: Message, state: FSMContext):
    """Handle menu button presses"""
    logger.info(f"Menu button pressed: {message.text} by user {message.from_user.id}")
    if not await check_access(message):
        logger.warning(f"Access denied for user {message.from_user.id}")
        return
    logger.info(f"Access granted, processing: {message.text}")
    
    text = message.text
    
    if text == "💬 Чат":
        await message.answer(
            "💬 <b>Режим чата</b>\n\n"
            "Просто отправьте мне любое сообщение, и я отвечу!\n"
            "Я могу отвечать на вопросы, помогать с задачами или просто общаться.",
            reply_markup=get_main_menu()
        )
    elif text == "🤖 Режим":
        await cmd_mode(message, state)
    elif text == "🛠 Навыки":
        await cmd_skills(message)
    elif text == "🧠 Память":
        await cmd_memory(message)
    elif text == "❓ Помощь":
        await cmd_help(message)
    elif text == "⚙️ Настройки":
        await cmd_settings(message)


@router.callback_query(F.data == "main:menu")
async def back_to_main(callback: CallbackQuery):
    """Handle back to main menu"""
    # Check whitelist
    if callback.from_user.id not in ALLOWED_USERS:
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\nЧто бы вы хотели сделать?"
    )
    await callback.answer()


async def get_user_agent_mode(user_id: int) -> str:
    """Get user's current agent mode"""
    async with async_session_maker() as session:
        from sqlalchemy import select
        from app.core.database import UserState
        
        result = await session.execute(
            select(UserState).where(UserState.user_id == user_id)
        )
        user_state = result.scalar_one_or_none()
        
        return user_state.current_agent if user_state else "nanobot"

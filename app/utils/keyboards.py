"""
Keyboards and UI components
"""
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.core.skills_loader import SkillInfo


def get_main_menu() -> ReplyKeyboardMarkup:
    """Main menu keyboard"""
    keyboard = [
        [KeyboardButton(text="💬 Чат"), KeyboardButton(text="🤖 Режим")],
        [KeyboardButton(text="🛠 Навыки"), KeyboardButton(text="🧠 Память")],
        [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="⚙️ Настройки")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите опцию..."
    )


def get_agent_mode_keyboard() -> InlineKeyboardMarkup:
    """Agent mode selection keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="⚡ Nanobot - Быстрый помощник",
        callback_data="mode:nanobot"
    )
    builder.button(
        text="🧩 Claudbot - Умный планировщик",
        callback_data="mode:claudbot"
    )
    builder.button(
        text="🔧 Moltbot - Менеджер навыков",
        callback_data="mode:moltbot"
    )
    
    builder.adjust(1)
    return builder.as_markup()


def get_skills_menu_keyboard() -> InlineKeyboardMarkup:
    """Skills menu keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📋 Список навыков", callback_data="skills:list")
    builder.button(text="➕ Создать навык", callback_data="skills:create")
    builder.button(text="🔍 Поиск навыков", callback_data="skills:search")
    builder.button(text="📥 Импорт навыка", callback_data="skills:import")
    builder.button(text="🔙 Назад", callback_data="main:menu")
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_skills_list_keyboard(
    skills: list[SkillInfo],
    page: int = 0,
    per_page: int = 5
) -> InlineKeyboardMarkup:
    """Skills list with pagination"""
    builder = InlineKeyboardBuilder()
    
    start = page * per_page
    end = start + per_page
    page_skills = skills[start:end]
    
    for skill in page_skills:
        status = "✅" if skill.is_active else "❌"
        builder.button(
            text=f"{status} {skill.name} ({skill.category})",
            callback_data=f"skill:view:{skill.name}"
        )
    
    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"skills:page:{page-1}"
            )
        )
    if end < len(skills):
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"skills:page:{page+1}"
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.button(text="🔙 Назад", callback_data="skills:menu")
    
    builder.adjust(1)
    return builder.as_markup()


def get_skill_detail_keyboard(skill_name: str, source: str) -> InlineKeyboardMarkup:
    """Skill detail actions"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="▶️ Запустить", callback_data=f"skill:run:{skill_name}")
    builder.button(text="📄 Код", callback_data=f"skill:code:{skill_name}")
    builder.button(text="✏️ Изменить", callback_data=f"skill:edit:{skill_name}")
    
    if source != "system":
        builder.button(
            text="🗑 Удалить",
            callback_data=f"skill:delete:{skill_name}"
        )
    
    builder.button(text="🔙 Назад", callback_data="skills:list")
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_memory_menu_keyboard() -> InlineKeyboardMarkup:
    """Memory operations menu"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📝 Добавить заметку", callback_data="memory:add:note")
    builder.button(text="✈️ Добавить поездку", callback_data="memory:add:trip")
    builder.button(text="💰 Добавить бюджет", callback_data="memory:add:budget")
    builder.button(text="📅 Добавить план", callback_data="memory:add:plan")
    builder.button(text="🔍 Поиск", callback_data="memory:search")
    builder.button(text="📊 Статистика", callback_data="memory:stats")
    builder.button(text="🔙 Назад", callback_data="main:menu")
    
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def get_confirmation_keyboard(confirm_data: str, cancel_data: str) -> InlineKeyboardMarkup:
    """Yes/No confirmation"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✅ Да", callback_data=confirm_data)
    builder.button(text="❌ Нет", callback_data=cancel_data)
    
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel operation keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="action:cancel")
    return builder.as_markup()


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Settings menu"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="🤖 Сменить агента", callback_data="settings:agent")
    builder.button(text="🎨 Интерфейс", callback_data="settings:interface")
    builder.button(text="🔔 Уведомления", callback_data="settings:notifications")
    builder.button(text="🔙 Назад", callback_data="main:menu")
    
    builder.adjust(1)
    return builder.as_markup()

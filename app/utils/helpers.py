"""
Utility functions
"""
import re
from typing import Optional
from datetime import datetime


def escape_markdown(text: str) -> str:
    """Escape Markdown special characters"""
    chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in chars:
        text = text.replace(char, f'\\{char}')
    return text


def truncate_text(text: str, max_length: int = 4000) -> str:
    """Truncate text to max length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def format_datetime(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M")


def parse_code_from_message(text: str) -> Optional[str]:
    """Extract code from markdown code blocks"""
    # Match ```python ... ``` or ``` ... ```
    pattern = r'```(?:python)?\n(.*?)\n```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def is_valid_skill_name(name: str) -> bool:
    """Check if skill name is valid"""
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))


def format_skill_info(skill_info) -> str:
    """Format skill info for display"""
    text = f"📦 <b>{skill_info.name}</b>\n"
    text += f"📝 {skill_info.description}\n"
    text += f"🏷 Категория: {skill_info.category}\n"
    text += f"📂 Источник: {skill_info.source}\n"
    text += f"🔢 Версия: {skill_info.version}\n"
    text += f"👤 Автор: {skill_info.author}\n"
    
    if skill_info.commands:
        text += f"⌨️ Команды: {', '.join(skill_info.commands)}\n"
    
    status = "✅ Активен" if skill_info.is_active else "❌ Неактивен"
    text += f"📊 Статус: {status}\n"
    
    return text


def format_memory(memory) -> str:
    """Format memory for display"""
    emoji_map = {
        'note': '📝',
        'trip': '✈️',
        'budget': '💰',
        'plan': '📅',
        'dialog': '💬'
    }
    
    emoji = emoji_map.get(memory.memory_type, '📄')
    text = f"{emoji} <b>{memory.memory_type.upper()}</b>\n"
    text += f"🕐 {format_datetime(memory.created_at)}\n\n"
    text += escape_markdown(memory.content[:500])
    
    if len(memory.content) > 500:
        text += "..."
    
    return text

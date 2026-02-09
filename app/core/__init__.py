"""
Core module initialization
"""
from app.core.config import settings
from app.core.database import init_db, get_db, get_or_create_user, save_message
from app.core.memory import vector_memory
from app.core.llm_client import llm_client, Message, LLMResponse
from app.core.skills_loader import skill_loader, SkillInfo

__all__ = [
    'settings',
    'init_db',
    'get_db',
    'get_or_create_user',
    'save_message',
    'vector_memory',
    'llm_client',
    'Message',
    'LLMResponse',
    'skill_loader',
    'SkillInfo'
]

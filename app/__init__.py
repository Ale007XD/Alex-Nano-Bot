"""
App module initialization
"""
from app.core.config import settings
from app.core.database import init_db, get_db
from app.core.memory import vector_memory
from app.core.llm_client import llm_client
from app.core.skills_loader import skill_loader

__version__ = settings.APP_VERSION

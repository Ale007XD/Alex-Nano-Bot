"""
FSM States for conversation management
"""
from aiogram.fsm.state import State, StatesGroup


class AgentMode(StatesGroup):
    """Agent mode selection"""
    selecting = State()


class SkillCreation(StatesGroup):
    """Skill creation states"""
    waiting_name = State()
    waiting_description = State()
    waiting_code = State()
    waiting_confirmation = State()


class SkillEdit(StatesGroup):
    """Skill editing states"""
    editing_code = State()
    waiting_confirmation = State()


class MemoryAdd(StatesGroup):
    """Memory addition states"""
    waiting_content = State()
    waiting_type = State()


class MemorySearch(StatesGroup):
    """Memory search states"""
    waiting_query = State()


class ChatState(StatesGroup):
    """Chat conversation states"""
    chatting = State()
    waiting_skill_input = State()

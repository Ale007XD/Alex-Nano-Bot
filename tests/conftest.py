"""
conftest.py — изоляция runtime-тестов от внешних зависимостей.

Проблема: app/__init__.py и app/core/__init__.py делают eager import
chromadb, sqlalchemy, aiogram и т.д. Runtime-модули (app/runtime/*)
не требуют этих зависимостей — они зависят только от LLMProtocol.

Решение: регистрируем заглушки тяжёлых пакетов в sys.modules ДО того,
как Python попытается их импортировать при загрузке app.core.*.
app и app.core оставляем реальными пакетами — не перекрываем их,
чтобы app.runtime.* нормально резолвилось.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stub(name: str) -> types.ModuleType:
    """Зарегистрировать пустой модуль-заглушку если ещё не в sys.modules."""
    if name not in sys.modules:
        m = types.ModuleType(name)
        sys.modules[name] = m
    return sys.modules[name]


def _install_stubs() -> None:
    """
    Устанавливает заглушки для внешних зависимостей.

    ВАЖНО: app и app.core НЕ перекрываем — они реальные пакеты.
    Перекрываем только leaf-модули которые они импортируют.
    """
    # --- тяжёлые C-расширения / внешние пакеты ---
    for name in [
        "chromadb", "chromadb.config", "chromadb.api", "chromadb.api.types",
        "fastembed",
        "aiogram", "aiogram.types", "aiogram.filters",
        "aiogram.fsm", "aiogram.fsm.context",
        "aiogram.fsm.storage", "aiogram.fsm.storage.memory",
        "apscheduler", "apscheduler.schedulers",
        "apscheduler.schedulers.asyncio",
        "apscheduler.triggers", "apscheduler.triggers.cron",
        "cryptography", "cryptography.fernet",
        "httpx", "aiohttp", "aiofiles",
        "sqlalchemy", "sqlalchemy.orm", "sqlalchemy.ext",
        "sqlalchemy.ext.asyncio", "sqlalchemy.future",
        "sqlalchemy.orm.decl_api",
        "aiosqlite",
    ]:
        _stub(name)

    # sqlalchemy.orm нужны Column, String, Integer, etc. как MagicMock
    sa_orm = sys.modules["sqlalchemy.orm"]
    sa_orm.DeclarativeBase = MagicMock
    sa_orm.Mapped = MagicMock
    sa_orm.mapped_column = MagicMock(return_value=MagicMock())
    sa_orm.relationship = MagicMock(return_value=MagicMock())

    sa = _stub("sqlalchemy")
    for attr in ["Column", "Integer", "String", "Boolean", "DateTime",
                 "Text", "JSON", "ForeignKey", "create_engine",
                 "event", "inspect", "select", "func"]:
        setattr(sa, attr, MagicMock())
    sa.orm = sa_orm

    sa_ext_async = sys.modules["sqlalchemy.ext.asyncio"]
    sa_ext_async.AsyncSession = MagicMock
    sa_ext_async.create_async_engine = MagicMock(return_value=MagicMock())
    sa_ext_async.async_sessionmaker = MagicMock(return_value=MagicMock())

    # pydantic_settings — нужен BaseSettings
    if "pydantic_settings" not in sys.modules:
        ps = _stub("pydantic_settings")

        class _FakeBaseSettings:
            class Config:
                env_file = ".env"
                extra = "ignore"

        ps.BaseSettings = _FakeBaseSettings

    # --- заглушки leaf-модулей app.core.* ---
    # (app и app.core остаются реальными пакетами)

    fake_settings = MagicMock()
    fake_settings.APP_NAME = "Alex-Nano-Bot"
    fake_settings.APP_VERSION = "1.5.0"
    fake_settings.DEFAULT_MODEL = "llama-3.1-8b-instant"
    fake_settings.CODER_MODEL = "llama-3.1-8b-instant"
    fake_settings.PLANNER_MODEL = "llama-3.3-70b-versatile"
    fake_settings.BOT_TIMEZONE = "Asia/Ho_Chi_Minh"

    cfg = types.ModuleType("app.core.config")
    cfg.settings = fake_settings
    sys.modules["app.core.config"] = cfg

    db_mod = types.ModuleType("app.core.database")
    db_mod.init_db = AsyncMock()
    db_mod.get_db = MagicMock()
    db_mod.get_or_create_user = AsyncMock()
    db_mod.save_message = AsyncMock()
    db_mod.User = MagicMock()
    db_mod.Message = MagicMock()
    db_mod.UserState = MagicMock()
    sys.modules["app.core.database"] = db_mod

    mem_mod = types.ModuleType("app.core.memory")
    mem_mod.vector_memory = MagicMock()
    mem_mod.VectorMemory = MagicMock()
    sys.modules["app.core.memory"] = mem_mod

    llm_mod = types.ModuleType("app.core.llm_client_v2")
    llm_mod.llm_client = MagicMock()
    llm_mod.Message = MagicMock()
    llm_mod.LLMResponse = MagicMock()
    sys.modules["app.core.llm_client_v2"] = llm_mod

    # legacy llm_client (test_bot.py импортирует его)
    llm_v1 = types.ModuleType("app.core.llm_client")
    llm_v1.Message = MagicMock()
    llm_v1.LLMResponse = MagicMock()
    sys.modules["app.core.llm_client"] = llm_v1

    skills_mod = types.ModuleType("app.core.skills_loader")
    skills_mod.skill_loader = MagicMock()
    skills_mod.SkillLoader = MagicMock()
    skills_mod.SkillInfo = MagicMock()
    skills_mod.is_valid_skill_name = lambda name: bool(
        __import__("re").match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name)
    )
    sys.modules["app.core.skills_loader"] = skills_mod

    scheduler_mod = types.ModuleType("app.core.scheduler")
    scheduler_mod.scheduler = MagicMock()
    sys.modules["app.core.scheduler"] = scheduler_mod

    logger_mod = types.ModuleType("app.core.logger")
    logger_mod.setup_logging = MagicMock()
    sys.modules["app.core.logger"] = logger_mod

    crypto_mod = types.ModuleType("app.core.crypto")
    crypto_mod.encrypt = MagicMock(return_value=b"encrypted")
    crypto_mod.decrypt = MagicMock(return_value="decrypted")
    sys.modules["app.core.crypto"] = crypto_mod

    web_search_mod = types.ModuleType("app.core.web_search")
    web_search_mod.web_search = AsyncMock(return_value=[])
    sys.modules["app.core.web_search"] = web_search_mod


# Устанавливаем заглушки ДО любого импорта из app.*
_install_stubs()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm():
    """MockLLMAdapter с фиксированным ответом."""
    from app.runtime.llm_adapter import MockLLMAdapter
    return MockLLMAdapter(fixed_response="тестовый ответ LLM")


@pytest.fixture
def registry():
    """InstructionRegistry с зарегистрированными базовыми инструкциями."""
    from app.runtime.registry import InstructionRegistry
    from app.runtime.instructions.call_llm import CallLLMInstruction
    from app.runtime.instructions.respond import RespondInstruction
    from app.runtime.instructions.store_memory import StoreMemoryInstruction
    from app.runtime.instructions.call_tool import CallToolInstruction

    reg = InstructionRegistry()
    reg.register("call_llm", CallLLMInstruction)
    reg.register("respond", RespondInstruction)
    reg.register("store_memory", StoreMemoryInstruction)
    reg.register("call_tool", CallToolInstruction)
    return reg


@pytest.fixture
def state():
    """Базовый StateContext для user_id=42."""
    from app.runtime.state_context import StateContext
    return StateContext.from_defaults(user_id=42, agent_mode="runtime")


@pytest.fixture
def mock_memory():
    """Заглушка VectorMemory."""
    m = MagicMock()
    m.add_memory = AsyncMock(return_value="doc-id-123")
    return m


@pytest.fixture
def mock_tools():
    """Заглушка ToolRegistry."""
    t = MagicMock()
    t.execute = AsyncMock(return_value={"result": "tool_output"})
    return t


@pytest.fixture
def vm_ctx(state, mock_llm, mock_memory, mock_tools):
    """Готовый VMContext для e2e-тестов VM."""
    from app.runtime.context import VMContext
    return VMContext(
        state=state,
        llm=mock_llm,
        memory=mock_memory,
        tools=mock_tools,
    )


@pytest.fixture
def vm(registry):
    """ExecutionVM с базовым registry."""
    from app.runtime.vm import ExecutionVM
    return ExecutionVM(registry)

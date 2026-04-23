"""
conftest.py — изоляция runtime-тестов от внешних зависимостей.

Стратегия:
  - Тяжёлые C-расширения (chromadb, fastembed, aiogram, sqlalchemy, …)
    заглушаются через sys.modules.
  - app.core.memory и app.core.skills_loader — реальные модули,
    т.к. test_bot.py проверяет реальные классы (VectorMemory, SkillLoader).
  - app.core.llm_client — реальный модуль (Message, LLMResponse — dataclass'ы).
  - app.core.database — заглушка с добавленным `engine` (нужен test_bot.py).
  - app.core.config — заглушка с fake settings (нет реальных env-переменных в CI).
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
import types
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stub(name: str) -> types.ModuleType:
    if name not in sys.modules:
        m = types.ModuleType(name)
        sys.modules[name] = m
    return sys.modules[name]


def _load_real_module(dotted_name: str, file_path: str) -> types.ModuleType:
    """Загрузить реальный .py файл через importlib, минуя __init__ cascade."""
    spec = importlib.util.spec_from_file_location(dotted_name, pathlib.Path(file_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[dotted_name] = module
    return module


def _install_stubs() -> None:
    # ── Внешние тяжёлые пакеты ──────────────────────────────────────────────
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

    # chromadb нужны конкретные атрибуты для memory.py
    chromadb_config = sys.modules["chromadb.config"]
    chromadb_config.Settings = MagicMock()
    chromadb_mod = sys.modules["chromadb"]
    chromadb_mod.PersistentClient = MagicMock(return_value=MagicMock())

    fastembed_mod = sys.modules["fastembed"]
    fastembed_mod.TextEmbedding = MagicMock()

    sa_orm = sys.modules["sqlalchemy.orm"]
    sa_orm.DeclarativeBase = MagicMock
    sa_orm.Mapped = MagicMock
    sa_orm.mapped_column = MagicMock(return_value=MagicMock())
    sa_orm.relationship = MagicMock(return_value=MagicMock())
    sa_orm.declarative_base = MagicMock(return_value=MagicMock())

    sa = sys.modules["sqlalchemy"]
    for attr in ["Column", "Integer", "String", "Boolean", "DateTime",
                 "Text", "JSON", "ForeignKey", "create_engine",
                 "event", "inspect", "select", "func"]:
        setattr(sa, attr, MagicMock())
    sa.orm = sa_orm

    sa_ext = sys.modules["sqlalchemy.ext.asyncio"]
    sa_ext.AsyncSession = MagicMock
    sa_ext.create_async_engine = MagicMock(return_value=MagicMock())
    sa_ext.async_sessionmaker = MagicMock(return_value=MagicMock())

    # pydantic_settings stub (если не установлен)
    if "pydantic_settings" not in sys.modules:
        ps = _stub("pydantic_settings")

        class _FakeBaseSettings:
            class Config:
                env_file = ".env"
                extra = "ignore"

        ps.BaseSettings = _FakeBaseSettings

    # ── env-заглушки — Settings() не упадёт ─────────────────────────────────
    os.environ.setdefault("BOT_TOKEN", "fake-ci-token")
    os.environ.setdefault("OPENROUTER_API_KEY", "fake-ci-key")

    # ── app.core.config — fake settings ─────────────────────────────────────
    fake_settings = MagicMock()
    fake_settings.APP_NAME = "Alex-Nano-Bot"
    fake_settings.APP_VERSION = "1.5.0"
    fake_settings.DEFAULT_MODEL = "llama-3.1-8b-instant"
    fake_settings.CODER_MODEL = "llama-3.1-8b-instant"
    fake_settings.PLANNER_MODEL = "llama-3.3-70b-versatile"
    fake_settings.BOT_TIMEZONE = "Asia/Ho_Chi_Minh"
    fake_settings.BOT_TOKEN = "fake-ci-token"
    fake_settings.OPENROUTER_API_KEY = "fake-ci-key"

    cfg = types.ModuleType("app.core.config")
    cfg.settings = fake_settings
    cfg.Settings = MagicMock(return_value=fake_settings)
    sys.modules["app.core.config"] = cfg

    # ── app.core.database — заглушка с engine ───────────────────────────────
    # test_bot.py::TestIntegration::test_database_initialization импортирует engine
    db_mod = types.ModuleType("app.core.database")
    db_mod.init_db = AsyncMock()
    db_mod.get_db = MagicMock()
    db_mod.get_or_create_user = AsyncMock()
    db_mod.save_message = AsyncMock()
    db_mod.User = MagicMock()
    db_mod.Message = MagicMock()
    db_mod.UserState = MagicMock()
    db_mod.engine = MagicMock()          # ← test_bot.py ожидает engine
    db_mod.async_session_maker = MagicMock()
    sys.modules["app.core.database"] = db_mod

    # ── app.core.memory — РЕАЛЬНЫЙ модуль ───────────────────────────────────
    # test_bot.py проверяет vm._initialized is False и vm._generate_id()
    # Нужен реальный VectorMemory, но без chromadb/fastembed (уже заглушены).
    _load_real_module("app.core.memory", "app/core/memory.py")

    # ── app.core.llm_client_v2 — заглушка ───────────────────────────────────
    llm_mod = types.ModuleType("app.core.llm_client_v2")
    llm_mod.llm_client = MagicMock()
    llm_mod.Message = MagicMock()
    llm_mod.LLMResponse = MagicMock()
    sys.modules["app.core.llm_client_v2"] = llm_mod

    # ── app.core.llm_client (legacy) — РЕАЛЬНЫЙ dataclass ───────────────────
    # test_bot.py: Message(role="user", content="Hello"); assert msg.role == "user"
    # Нужен настоящий dataclass, а не MagicMock.
    _install_legacy_llm_client()

    # ── app.core.skills_loader — РЕАЛЬНЫЙ модуль ────────────────────────────
    # test_bot.py: SkillLoader(), loader.skills, loader.skill_info, is_valid_skill_name
    _load_real_module("app.core.skills_loader", "app/core/skills_loader.py")

    # ── Остальные leaf-модули ────────────────────────────────────────────────
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

    # ── app / app.core пакеты — заглушки чтобы __init__.py не выполнялся ───
    app_mod = types.ModuleType("app")
    app_mod.__path__ = []
    app_mod.__version__ = "1.5.0"
    app_mod.settings = fake_settings
    sys.modules["app"] = app_mod

    app_core_mod = types.ModuleType("app.core")
    app_core_mod.__path__ = []
    app_core_mod.settings = fake_settings
    sys.modules["app.core"] = app_core_mod


def _install_legacy_llm_client() -> None:
    """
    Создаём реальные dataclass'ы Message и LLMResponse для app.core.llm_client.
    test_bot.py проверяет msg.role == "user" и resp.content == "Hi" — MagicMock не годится.
    """
    from dataclasses import dataclass as dc
    from typing import Optional, Dict

    @dc
    class Message:
        role: str
        content: str

    @dc
    class LLMResponse:
        content: str
        model: str
        provider: str = "mock"
        usage: Optional[Dict] = None
        finish_reason: Optional[str] = None
        response_time_ms: float = 0.0

    llm_v1 = types.ModuleType("app.core.llm_client")
    llm_v1.Message = Message
    llm_v1.LLMResponse = LLMResponse
    sys.modules["app.core.llm_client"] = llm_v1


# Устанавливаем ДО любого импорта из app.*
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

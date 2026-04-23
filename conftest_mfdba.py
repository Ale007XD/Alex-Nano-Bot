"""
conftest_mfdba.py — минимальная изоляция для test_mfdba_core.py.

Проблема: app/__init__.py и app/core/__init__.py делают eager-импорт
settings, database, memory и т.д. при любом обращении к пакету app.
Это рушит тесты, которым нужен только app.core.skills_loader.

Решение: до любого импорта из app.* регистрируем в sys.modules:
  - заглушку app.core.config (без реального Settings и env-переменных)
  - заглушки тяжёлых пакетов (chromadb, aiogram, sqlalchemy, …)
  - заглушки остальных app.core.* модулей

app.core.skills_loader НЕ перекрываем — тесты проверяют реальный класс.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock


def _stub(name: str) -> types.ModuleType:
    if name not in sys.modules:
        m = types.ModuleType(name)
        sys.modules[name] = m
    return sys.modules[name]


def _install_stubs() -> None:
    # --- внешние тяжёлые пакеты ---
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

    # sqlalchemy нужны атрибуты-заглушки
    sa_orm = sys.modules["sqlalchemy.orm"]
    sa_orm.DeclarativeBase = MagicMock
    sa_orm.Mapped = MagicMock
    sa_orm.mapped_column = MagicMock(return_value=MagicMock())
    sa_orm.relationship = MagicMock(return_value=MagicMock())

    sa = sys.modules["sqlalchemy"]
    for attr in ["Column", "Integer", "String", "Boolean", "DateTime",
                 "Text", "JSON", "ForeignKey", "create_engine",
                 "event", "inspect", "select", "func"]:
        setattr(sa, attr, MagicMock())
    sa.orm = sa_orm

    sa_ext_async = sys.modules["sqlalchemy.ext.asyncio"]
    sa_ext_async.AsyncSession = MagicMock
    sa_ext_async.create_async_engine = MagicMock(return_value=MagicMock())
    sa_ext_async.async_sessionmaker = MagicMock(return_value=MagicMock())

    # pydantic_settings — нужен BaseSettings (для config.py)
    if "pydantic_settings" not in sys.modules:
        ps = _stub("pydantic_settings")

        class _FakeBaseSettings:
            class Config:
                env_file = ".env"
                extra = "ignore"

        ps.BaseSettings = _FakeBaseSettings

    # --- app.core.config — главная причина падения ---
    # Settings() требует BOT_TOKEN и OPENROUTER_API_KEY из env.
    # Подменяем весь модуль фейковым объектом settings.
    fake_settings = MagicMock()
    fake_settings.APP_NAME = "Alex-Nano-Bot"
    fake_settings.APP_VERSION = "1.5.0"
    fake_settings.DEFAULT_MODEL = "llama-3.1-8b-instant"
    fake_settings.CODER_MODEL = "llama-3.1-8b-instant"
    fake_settings.PLANNER_MODEL = "llama-3.3-70b-versatile"
    fake_settings.BOT_TIMEZONE = "Asia/Ho_Chi_Minh"
    fake_settings.BOT_TOKEN = "fake-token"
    fake_settings.OPENROUTER_API_KEY = "fake-key"

    cfg = types.ModuleType("app.core.config")
    cfg.settings = fake_settings
    cfg.Settings = MagicMock(return_value=fake_settings)
    sys.modules["app.core.config"] = cfg

    # --- остальные app.core.* модули ---
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

    llm_v1 = types.ModuleType("app.core.llm_client")
    llm_v1.Message = MagicMock()
    llm_v1.LLMResponse = MagicMock()
    sys.modules["app.core.llm_client"] = llm_v1

    # ВНИМАНИЕ: app.core.skills_loader НЕ заглушаем —
    # test_mfdba_core.py тестирует реальный OpenClawExecutor и ToolError.

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

    # Заглушки для app и app.core пакетов —
    # без них Python всё равно выполнит реальные __init__.py
    app_mod = types.ModuleType("app")
    app_mod.__path__ = []  # помечаем как пакет
    app_mod.__version__ = "1.5.0"
    app_mod.settings = fake_settings
    sys.modules["app"] = app_mod

    app_core_mod = types.ModuleType("app.core")
    app_core_mod.__path__ = []
    app_core_mod.settings = fake_settings
    sys.modules["app.core"] = app_core_mod


# Устанавливаем заглушки ДО любого импорта из app.*
_install_stubs()

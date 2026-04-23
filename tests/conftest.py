import sys
import os
import importlib.util
from unittest.mock import MagicMock
from dataclasses import dataclass

# 1. Заглушки тяжелых внешних зависимостей (ChromaDB, FastEmbed)
mock_chroma = MagicMock()
mock_chroma_config = MagicMock()
mock_chroma_config.Settings = MagicMock()
mock_fastembed = MagicMock()
mock_fastembed.TextEmbedding = MagicMock()

sys.modules["chromadb"] = mock_chroma
sys.modules["chromadb.config"] = mock_chroma_config
sys.modules["fastembed"] = mock_fastembed

# 2. Окружение (обязательно до инициализации любых компонентов app)
os.environ["BOT_TOKEN"] = "123:mock"
os.environ["OPENROUTER_API_KEY"] = "mock_key"

# 3. Точечные заглушки внутренних модулей, вызывающих побочные эффекты при загрузке
mock_config = MagicMock()
mock_config.Settings.return_value = MagicMock()
sys.modules["app.core.config"] = mock_config

mock_db = MagicMock()
mock_db.engine = MagicMock()
mock_db.declarative_base.return_value = MagicMock()
sys.modules["app.core.database"] = mock_db

mock_client = MagicMock()
@dataclass
class Message:
    role: str
    content: str
@dataclass
class LLMResponse:
    content: str
    tool_calls: list = None
mock_client.Message = Message
mock_client.LLMResponse = LLMResponse
sys.modules["app.core.llm_client"] = mock_client

# 4. Изолированная загрузка критичных модулей с сохранением оригинального поведения
def _load_real_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

_load_real_module("app.core.memory", "app/core/memory.py")
_load_real_module("app.core.skills_loader", "app/core/skills_loader.py")

# Мы НЕ глушим пакеты "app" и "app.core" целиком. 
# Стандартный механизм импорта теперь свободно найдет app.agents и app.runtime на диске, 
# а все опасные импорты (config, database) будут перехвачены словарем sys.modules выше.

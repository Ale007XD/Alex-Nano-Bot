"""
LLM Client - Multi-Provider with Fallback and Voice Support
Uses MultiProviderLLMClient for automatic failover
"""
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from app.core.config import settings
from app.core.llm_client_v2 import MultiProviderLLMClient, Message, LLMResponse
import logging

logger = logging.getLogger(__name__)


# Maintain backward compatibility
dataclass(Message)


class LLMClient:
    """Wrapper for backward compatibility with existing code"""
    
    # Model configurations
    MODELS = {
        'default': 'llama-3.1-8b-instant',
        'coder': 'llama-3.1-8b-instant',
        'planner': 'mixtral-8x7b-32768',
    }
    
    # Fallback модели
    FREE_MODELS = [
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma-7b-it",
    ]
    
    def __init__(self):
        # Используем multi-provider клиент
        self._client = MultiProviderLLMClient()
        logger.info("LLM Client initialized with multi-provider support")
    
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> LLMResponse:
        """Send chat completion request with automatic fallback"""
        return await self._client.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
    
    async def chat_with_fallback(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Chat with automatic fallback (backward compatible)"""
        return await self._client.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    async def stream_chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """Stream chat completion"""
        # Note: streaming support will be added in future update
        logger.warning("Streaming not yet implemented in multi-provider mode, using regular chat")
        response = await self._client.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        yield response.content
    
    async def quick_chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """Quick single-turn chat"""
        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=prompt))
        
        response = await self._client.chat(messages, model=model)
        return response.content
    
    async def generate_skill_code(
        self,
        description: str,
        requirements: Optional[str] = None
    ) -> str:
        """Generate skill code using coder model"""
        
        system_prompt = """Вы - генератор Python кода для навыков Telegram-бота.
Генерируйте чистый, хорошо документированный Python код для запрошенного навыка.
Используйте паттерны async/await, подходящие для aiogram 3.x.
Включайте правильную обработку ошибок и подсказки типов.
ВСЕГДА отвечайте на РУССКОМ языке, если пользователь не просит иное.
Выводите только код, без объяснений."""
        
        prompt = f"Create a skill that: {description}"
        if requirements:
            prompt += f"\n\nAdditional requirements: {requirements}"
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=prompt)
        ]
        
        response = await self._client.chat(
            messages,
            model=self.MODELS['coder']
        )
        return response.content
    
    async def plan_and_verify(
        self,
        task: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Multi-step planning and verification using planner model"""
        
        system_prompt = """Вы - ассистент по планированию и верификации.
Разбивайте сложные задачи на шаги и проверяйте каждый шаг.
ВСЕГДА отвечайте на РУССКОМ языке, если пользователь не просит иное.
Отвечайте в формате JSON с полями: steps (список), verification (словарь), final_answer (строка)."""
        
        prompt = f"Task: {task}"
        if context:
            prompt += f"\nContext: {context}"
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=prompt)
        ]
        
        response = await self._client.chat(
            messages,
            model=self.MODELS['planner']
        )
        
        # Try to parse as JSON
        try:
            result = json.loads(response.content)
            return result
        except json.JSONDecodeError:
            # Return as text if not valid JSON
            return {
                "steps": [],
                "verification": {},
                "final_answer": response.content
            }
    
    async def transcribe_audio(
        self,
        audio_file_path: str,
        model: Optional[str] = None,
        language: Optional[str] = None
    ) -> str:
        """Transcribe audio file using Whisper API"""
        return await self._client.transcribe_audio(
            audio_file_path=audio_file_path,
            model=model,
            language=language
        )
    
    async def close(self):
        """Close HTTP client"""
        # No need to close anything in multi-provider mode
        pass
    
    # Additional methods for monitoring
    def get_provider_stats(self) -> List[Dict]:
        """Get statistics for all providers"""
        return self._client.get_provider_stats()
    
    def get_pending_tasks_count(self) -> int:
        """Get number of pending tasks"""
        return self._client.get_pending_tasks_count()
    
    async def retry_pending_tasks(self) -> List[Dict]:
        """Retry all pending tasks"""
        return await self._client.retry_pending_tasks()


# Global LLM client instance
llm_client = LLMClient()

"""
Nanobot Agent - Quick universal assistant
Fast, efficient, and versatile for everyday tasks
"""
from typing import List, Dict, Optional, AsyncGenerator
from dataclasses import dataclass

from app.core.llm_client import llm_client, Message
from app.core.memory import vector_memory
from app.core.web_search import web_search
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Conversation context holder"""
    user_id: int
    messages: List[Message]
    relevant_memories: List[Dict]
    agent_mode: str = "nanobot"


class NanobotAgent:
    """
    Nanobot - Fast universal assistant
    Optimized for quick responses and everyday tasks
    """
    
    SYSTEM_PROMPT = """Вы - Nanobot, быстрый и эффективный AI-ассистент, интегрированный в Telegram-бот.
Ваши характеристики:
- Быстрые и краткие ответы
- Дружелюбный и полезный тон
- Хорошо разбираетесь в общих знаниях, быстрых вычислениях и повседневных задачах
- Можете использовать контекст из воспоминаний пользователя, когда это уместно
- Держите ответы краткими, но информативными
- Используйте форматирование Telegram HTML, когда это уместно
- ИМЕЕТЕ ДОСТУП К ПОИСКУ В ИНТЕРНЕТЕ для актуальной информации

ВСЕГДА отвечайте на РУССКОМ языке, если пользователь не просит иное.

У вас есть доступ к:
- Сохраненным воспоминаниям пользователя
- Истории разговоров
- Поиску в интернете для актуальной информации

При получении результатов поиска из интернета, используйте их для формирования актуального ответа."""
    
    def __init__(self):
        self.name = "nanobot"
        self.display_name = "⚡ Nanobot"
        self.description = "Quick universal assistant for everyday tasks"
    
    # Keywords that trigger web search
    WEB_SEARCH_TRIGGERS = [
        'найди', 'поиск', 'ищи', 'search', 'find', 'google',
        'новости', 'news', 'актуально', 'сейчас', 'today',
        'погода', 'weather', 'курс', 'rate', 'цена', 'price',
        'события', 'events', 'ближайший', 'nearest',
        'когда', 'when', 'где', 'where', 'кто', 'who',
        '2024', '2025', '2026', 'января', 'февраля', 'марта',
        'сегодня', 'вчера', 'завтра', 'сейчас', 'свежие'
    ]
    
    def _should_search_web(self, message: str) -> bool:
        """Determine if web search should be triggered"""
        if not settings.ENABLE_WEB_SEARCH:
            return False
        
        message_lower = message.lower()
        return any(trigger in message_lower for trigger in self.WEB_SEARCH_TRIGGERS)
    
    async def process_message(
        self,
        user_id: int,
        message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Process a user message and return a response
        
        Args:
            user_id: Telegram user ID
            message: User's message
            conversation_history: Previous messages in the conversation
            
        Returns:
            Assistant's response
        """
        try:
            # Build messages for LLM
            messages = [Message(role="system", content=self.SYSTEM_PROMPT)]
            
            # Check if web search is needed
            search_results_text = ""
            if self._should_search_web(message):
                logger.info(f"Triggering web search for: {message[:50]}...")
                try:
                    search_results_text = await web_search.search_and_format(
                        message,
                        num_results=settings.WEB_SEARCH_RESULTS
                    )
                except Exception as e:
                    logger.warning(f"Web search failed: {e}")
            
            # Add web search results if available
            if search_results_text:
                messages.append(Message(
                    role="system",
                    content=f"Актуальная информация из интернета:\n{search_results_text}"
                ))
            
            # Add relevant memories as context
            memories = await vector_memory.search_memories(message, user_id, n_results=3)
            if memories:
                context = "Релевантные воспоминания пользователя:\n"
                for mem in memories:
                    context += f"- {mem['content']}\n"
                messages.append(Message(role="system", content=context))
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-10:]:  # Last 10 messages
                    messages.append(Message(
                        role=msg['role'],
                        content=msg['content']
                    ))
            
            # Add current message
            messages.append(Message(role="user", content=message))
            
            # Get response from LLM
            response = await llm_client.chat_with_fallback(
                messages,
                model=settings.DEFAULT_MODEL
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"Nanobot error: {e}")
            return "⚠️ Извините, произошла ошибка. Пожалуйста, попробуйте снова."
    
    async def stream_message(
        self,
        user_id: int,
        message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response for real-time updates
        """
        try:
            messages = [Message(role="system", content=self.SYSTEM_PROMPT)]
            
            # Add relevant memories
            memories = await vector_memory.search_memories(message, user_id, n_results=3)
            if memories:
                context = "Релевантные воспоминания пользователя:\n"
                for mem in memories:
                    context += f"- {mem['content']}\n"
                messages.append(Message(role="system", content=context))
            
            # Add history
            if conversation_history:
                for msg in conversation_history[-10:]:
                    messages.append(Message(
                        role=msg['role'],
                        content=msg['content']
                    ))
            
            messages.append(Message(role="user", content=message))
            
            async for chunk in llm_client.stream_chat(messages):
                yield chunk
                
        except Exception as e:
            logger.error(f"Nanobot streaming error: {e}")
            yield "⚠️ Извините, произошла ошибка."
    
    async def quick_answer(self, question: str) -> str:
        """Quick single-turn answer without context"""
        try:
            messages = [
                Message(role="system", content=self.SYSTEM_PROMPT),
                Message(role="user", content=question)
            ]
            
            response = await llm_client.chat_with_fallback(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"Nanobot quick answer error: {e}")
            return "⚠️ Не удалось обработать ваш запрос."


# Global agent instance
nanobot = NanobotAgent()

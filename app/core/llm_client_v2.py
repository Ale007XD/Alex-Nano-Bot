"""
Multi-Provider LLM Client with automatic fallback and task recovery
Supports: Groq, OpenRouter, Anthropic, OpenAI
"""
import json
import httpx
import asyncio
import time
from typing import List, Dict, Optional, AsyncGenerator, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """Provider health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class Provider:
    """LLM Provider configuration"""
    name: str
    base_url: str
    api_key: str
    models: List[str]
    priority: int = 0
    status: ProviderStatus = ProviderStatus.HEALTHY
    last_error: Optional[str] = None
    error_count: int = 0
    last_used: Optional[datetime] = None
    response_time_ms: float = 0.0


@dataclass
class Message:
    """LLM message structure"""
    role: str
    content: str


@dataclass
class LLMResponse:
    """LLM response structure"""
    content: str
    model: str
    provider: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    response_time_ms: float = 0.0


@dataclass
class PendingTask:
    """Task waiting to be processed"""
    id: str
    messages: List[Message]
    model: Optional[str]
    temperature: Optional[float]
    max_tokens: Optional[int]
    created_at: datetime
    attempts: int = 0
    last_error: Optional[str] = None
    callback: Optional[Callable] = None


class MultiProviderLLMClient:
    """Multi-provider LLM client with automatic fallback"""
    
    def __init__(self):
        self.providers: List[Provider] = []
        self.pending_tasks: Dict[str, PendingTask] = {}
        self.max_retries = 3
        self.retry_delay = 2.0
        self.health_check_interval = 60  # seconds
        self._health_monitor_started = False
        self._setup_providers()
        # Don't start health monitor here - will start lazily on first use
    
    def _setup_providers(self):
        """Initialize providers from settings"""
        # Provider 1: Groq (primary)
        if settings.OPENROUTER_API_KEY:
            self.providers.append(Provider(
                name="groq",
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.OPENROUTER_API_KEY,
                models=[
                    "llama-3.1-8b-instant",
                    "mixtral-8x7b-32768",
                    "gemma-7b-it",
                    "whisper-large-v3"
                ],
                priority=1
            ))
        
        # Provider 2: OpenRouter (fallback)
        if settings.OPENROUTER_API_KEY:
            self.providers.append(Provider(
                name="openrouter",
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
                models=[
                    "mistralai/mistral-7b-instruct",
                    "anthropic/claude-3-sonnet",
                    "openai/gpt-3.5-turbo"
                ],
                priority=2
            ))
        
        # Provider 3: Anthropic (if key available)
        if hasattr(settings, 'ANTHROPIC_API_KEY') and settings.ANTHROPIC_API_KEY:
            self.providers.append(Provider(
                name="anthropic",
                base_url="https://api.anthropic.com/v1",
                api_key=settings.ANTHROPIC_API_KEY,
                models=[
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307"
                ],
                priority=3
            ))
        
        # Provider 4: OpenAI (if key available)
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            self.providers.append(Provider(
                name="openai",
                base_url="https://api.openai.com/v1",
                api_key=settings.OPENAI_API_KEY,
                models=[
                    "gpt-3.5-turbo",
                    "gpt-4"
                ],
                priority=4
            ))
        
        # Sort by priority
        self.providers.sort(key=lambda p: p.priority)
        logger.info(f"Initialized {len(self.providers)} providers: {[p.name for p in self.providers]}")
    
    def _start_health_monitor(self):
        """Start background health monitoring (lazy initialization)"""
        if self._health_monitor_started:
            return
        
        async def health_check_loop():
            while True:
                await asyncio.sleep(self.health_check_interval)
                await self._check_providers_health()
        
        # Start in background only if event loop is running
        try:
            asyncio.get_running_loop()
            asyncio.create_task(health_check_loop())
            self._health_monitor_started = True
            logger.info("Health monitoring started")
        except RuntimeError:
            # No event loop running yet, will retry on next call
            logger.debug("Health monitor: no event loop yet, deferring")
    
    async def _check_providers_health(self):
        """Check health of all providers"""
        for provider in self.providers:
            try:
                start_time = time.time()
                
                # Simple health check - try to list models or make a test request
                headers = {
                    "Authorization": f"Bearer {provider.api_key}",
                    "Content-Type": "application/json"
                }
                
                async with httpx.AsyncClient() as client:
                    # Try a simple models list or just check connectivity
                    response = await client.get(
                        f"{provider.base_url}/models",
                        headers=headers,
                        timeout=10.0
                    )
                    
                    response_time = (time.time() - start_time) * 1000
                    provider.response_time_ms = response_time
                    
                    if response.status_code == 200:
                        if provider.status == ProviderStatus.DOWN:
                            logger.info(f"Provider {provider.name} is back online!")
                        provider.status = ProviderStatus.HEALTHY
                        provider.error_count = 0
                        provider.last_error = None
                    else:
                        provider.error_count += 1
                        if provider.error_count >= 3:
                            provider.status = ProviderStatus.DOWN
                            
            except Exception as e:
                provider.error_count += 1
                provider.last_error = str(e)
                if provider.error_count >= 3:
                    provider.status = ProviderStatus.DOWN
                    logger.warning(f"Provider {provider.name} marked as DOWN: {e}")
    
    def _get_healthy_providers(self) -> List[Provider]:
        """Get list of healthy providers sorted by priority"""
        healthy = [p for p in self.providers if p.status != ProviderStatus.DOWN]
        return sorted(healthy, key=lambda p: p.priority)
    
    def _map_model_to_provider(self, model: str, provider: Provider) -> str:
        """Map generic model name to provider-specific model"""
        # Model mapping
        model_mappings = {
            "groq": {
                "default": "llama-3.1-8b-instant",
                "coder": "llama-3.1-8b-instant",
                "planner": "mixtral-8x7b-32768"
            },
            "openrouter": {
                "default": "mistralai/mistral-7b-instruct",
                "coder": "codellama/codellama-70b-instruct",
                "planner": "anthropic/claude-3-sonnet"
            },
            "anthropic": {
                "default": "claude-3-sonnet-20240229",
                "coder": "claude-3-sonnet-20240229",
                "planner": "claude-3-sonnet-20240229"
            },
            "openai": {
                "default": "gpt-3.5-turbo",
                "coder": "gpt-3.5-turbo",
                "planner": "gpt-4"
            }
        }
        
        # Get mapping for provider
        provider_mappings = model_mappings.get(provider.name, {})
        
        # Map special model names
        if model in provider_mappings:
            return provider_mappings[model]
        
        # If model is already valid for this provider, use it
        if model in provider.models:
            return model
        
        # Otherwise return default
        return provider_mappings.get("default", provider.models[0] if provider.models else "")
    
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        max_attempts: int = 3
    ) -> LLMResponse:
        """Send chat request with automatic fallback"""
        
        # Start health monitor on first use (lazy initialization)
        self._start_health_monitor()
        
        temperature = temperature or settings.TEMPERATURE
        max_tokens = max_tokens or settings.MAX_TOKENS
        
        last_error = None
        healthy_providers = self._get_healthy_providers()
        
        if not healthy_providers:
            # Try to recover any provider
            logger.warning("No healthy providers, attempting recovery...")
            for provider in self.providers:
                provider.status = ProviderStatus.HEALTHY
                provider.error_count = 0
            healthy_providers = self.providers
        
        for provider in healthy_providers:
            for attempt in range(max_attempts):
                try:
                    start_time = time.time()
                    
                    # Map model to provider-specific
                    provider_model = self._map_model_to_provider(model or "default", provider)
                    
                    logger.info(f"Trying {provider.name} with model {provider_model} (attempt {attempt + 1})")
                    
                    response = await self._make_request(
                        provider=provider,
                        messages=messages,
                        model=provider_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=stream
                    )
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    # Update provider stats
                    provider.last_used = datetime.now()
                    provider.response_time_ms = response_time
                    provider.status = ProviderStatus.HEALTHY
                    provider.error_count = 0
                    
                    logger.info(f"Success with {provider.name} in {response_time:.0f}ms")
                    
                    return LLMResponse(
                        content=response['content'],
                        model=response['model'],
                        provider=provider.name,
                        usage=response.get('usage'),
                        finish_reason=response.get('finish_reason'),
                        response_time_ms=response_time
                    )
                    
                except Exception as e:
                    last_error = e
                    logger.warning(f"{provider.name} attempt {attempt + 1} failed: {e}")
                    
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    else:
                        provider.error_count += 1
                        if provider.error_count >= 3:
                            provider.status = ProviderStatus.DEGRADED
                            logger.error(f"Provider {provider.name} degraded after {provider.error_count} errors")
        
        # All providers failed
        error_msg = f"All providers failed. Last error: {last_error}"
        logger.error(error_msg)
        
        # Store task for later retry
        task_id = self._store_pending_task(messages, model, temperature, max_tokens)
        
        raise Exception(f"{error_msg}. Task stored as pending: {task_id}")
    
    async def _make_request(
        self,
        provider: Provider,
        messages: List[Message],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool = False
    ) -> Dict:
        """Make request to specific provider"""
        
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json"
        }
        
        # Format messages based on provider
        if provider.name == "anthropic":
            # Anthropic uses different format
            formatted_messages = self._format_for_anthropic(messages)
        else:
            formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        
        payload = {
            "model": model,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{provider.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'error' in data:
                raise Exception(f"API error: {data['error']}")
            
            choice = data['choices'][0]
            return {
                'content': choice['message']['content'],
                'model': data.get('model', model),
                'usage': data.get('usage'),
                'finish_reason': choice.get('finish_reason')
            }
    
    def _format_for_anthropic(self, messages: List[Message]) -> List[Dict]:
        """Format messages for Anthropic API"""
        formatted = []
        for msg in messages:
            if msg.role == "system":
                # Anthropic handles system messages differently
                formatted.append({"role": "user", "content": f"System: {msg.content}"})
            else:
                formatted.append({"role": msg.role, "content": msg.content})
        return formatted
    
    def _store_pending_task(
        self,
        messages: List[Message],
        model: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int]
    ) -> str:
        """Store failed task for later retry"""
        import hashlib
        
        task_id = hashlib.md5(
            f"{datetime.now().isoformat()}{messages[0].content[:50]}".encode()
        ).hexdigest()[:12]
        
        self.pending_tasks[task_id] = PendingTask(
            id=task_id,
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            created_at=datetime.now(),
            attempts=1
        )
        
        logger.info(f"Stored pending task: {task_id}")
        return task_id
    
    async def retry_pending_tasks(self) -> List[Dict]:
        """Retry all pending tasks"""
        results = []
        tasks_to_remove = []
        
        for task_id, task in list(self.pending_tasks.items()):
            if task.attempts >= self.max_retries:
                logger.warning(f"Task {task_id} exceeded max retries, removing")
                tasks_to_remove.append(task_id)
                continue
            
            try:
                logger.info(f"Retrying pending task {task_id} (attempt {task.attempts + 1})")
                
                response = await self.chat(
                    messages=task.messages,
                    model=task.model,
                    temperature=task.temperature,
                    max_tokens=task.max_tokens
                )
                
                results.append({
                    'task_id': task_id,
                    'status': 'success',
                    'response': response
                })
                
                tasks_to_remove.append(task_id)
                
                # Call callback if provided
                if task.callback:
                    await task.callback(response)
                    
            except Exception as e:
                task.attempts += 1
                task.last_error = str(e)
                results.append({
                    'task_id': task_id,
                    'status': 'failed',
                    'error': str(e),
                    'attempts': task.attempts
                })
        
        # Remove completed tasks
        for task_id in tasks_to_remove:
            del self.pending_tasks[task_id]
        
        return results
    
    def get_provider_stats(self) -> List[Dict]:
        """Get statistics for all providers"""
        return [
            {
                'name': p.name,
                'status': p.status.value,
                'priority': p.priority,
                'models': len(p.models),
                'error_count': p.error_count,
                'last_error': p.last_error,
                'last_used': p.last_used.isoformat() if p.last_used else None,
                'response_time_ms': p.response_time_ms
            }
            for p in self.providers
        ]
    
    def get_pending_tasks_count(self) -> int:
        """Get number of pending tasks"""
        return len(self.pending_tasks)
    
    async def transcribe_audio(
        self,
        audio_file_path: str,
        model: Optional[str] = None,
        language: Optional[str] = None
    ) -> str:
        """Transcribe audio using available provider"""
        import aiofiles
        import os
        import mimetypes
        
        # Find provider with Whisper support (Groq)
        whisper_providers = [p for p in self.providers if 'whisper' in p.models]
        
        if not whisper_providers:
            raise Exception("No provider with Whisper support available")
        
        provider = whisper_providers[0]  # Use first available
        model = model or "whisper-large-v3"
        
        async with aiofiles.open(audio_file_path, 'rb') as f:
            audio_data = await f.read()
        
        # Build multipart request
        boundary = '----VoiceFormBoundary7MA4YWxkTrZu0gW'
        body_parts = []
        
        body_parts.append(f'--{boundary}\r\n'.encode())
        body_parts.append(b'Content-Disposition: form-data; name="model"\r\n\r\n')
        body_parts.append(f'{model}\r\n'.encode())
        
        if language:
            body_parts.append(f'--{boundary}\r\n'.encode())
            body_parts.append(b'Content-Disposition: form-data; name="language"\r\n\r\n')
            body_parts.append(f'{language}\r\n'.encode())
        
        filename = os.path.basename(audio_file_path)
        content_type, _ = mimetypes.guess_type(audio_file_path)
        if not content_type:
            content_type = 'audio/ogg'
        
        body_parts.append(f'--{boundary}\r\n'.encode())
        body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
        body_parts.append(f'Content-Type: {content_type}\r\n\r\n'.encode())
        body_parts.append(audio_data)
        body_parts.append(b'\r\n')
        body_parts.append(f'--{boundary}--\r\n'.encode())
        
        body = b''.join(body_parts)
        
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{provider.base_url}/audio/transcriptions",
                content=body,
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('text', '').strip()


# Global multi-provider client instance
llm_client = MultiProviderLLMClient()

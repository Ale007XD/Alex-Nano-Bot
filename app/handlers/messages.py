"""
Message handler for chat conversations
"""
import os

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.core.database import async_session_maker, get_or_create_user, save_message
from app.core.config import settings
from app.agents.router import agent_router
from app.handlers.commands import get_user_agent_mode, ALLOWED_USERS
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text)
async def handle_message(message: Message, state: FSMContext):
    """Handle incoming text messages"""
    user = message.from_user
    user_message = message.text
    
    logger.info(f"Message handler triggered: '{user_message}' from user {user.id}")
    
    # Check whitelist
    if user.id not in ALLOWED_USERS:
        logger.warning(f"Access denied for user {user.id}")
        await message.answer(
            "⛔ <b>Доступ запрещен</b>\n\n"
            "Этот бот является приватным. У вас нет прав на использование."
        )
        return
    
    # Skip commands and menu buttons
    if user_message.startswith('/') or user_message in [
        "💬 Чат", "🤖 Режим", "🛠 Навыки", "🧠 Память", "❓ Помощь", "⚙️ Настройки"
    ]:
        logger.info(f"Skipping menu button: {user_message}")
        return
    
    try:
        # Get or create user
        async with async_session_maker() as session:
            db_user = await get_or_create_user(
                session,
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code
            )
            
            # Get user's agent mode
            agent_mode = await get_user_agent_mode(user.id)
            
            # Get conversation history
            from app.core.database import get_user_messages
            history = await get_user_messages(session, db_user.id, limit=20)
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in reversed(history)
            ]
            
            # Show typing indicator
            await message.bot.send_chat_action(message.chat.id, "typing")
            
            # Route to appropriate agent
            response = await agent_router.route_message(
                user_id=user.id,
                message=user_message,
                agent_mode=agent_mode,
                conversation_history=conversation_history
            )
            
            # Save messages to database
            await save_message(
                session,
                user_id=db_user.id,
                role="user",
                content=user_message,
                agent_mode=agent_mode
            )
            
            await save_message(
                session,
                user_id=db_user.id,
                role="assistant",
                content=response,
                agent_mode=agent_mode
            )
        
        # Send response
        # Split long messages if needed
        if len(response) > 4096:
            # Split into chunks
            chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await message.answer(chunk)
                else:
                    await message.answer(f"<i>(continued {i+1}/{len(chunks)})</i>\n\n{chunk}")
        else:
            await message.answer(response)
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await message.answer(
            "⚠️ <b>Извините, произошла ошибка при обработке вашего сообщения.</b>\n\n"
            "Пожалуйста, попробуйте снова или используйте /help для помощи."
        )


@router.message(F.photo)
async def handle_photo(message: Message):
    """Handle photo messages — analyze with vision model"""
    user = message.from_user

    if user.id not in ALLOWED_USERS:
        await message.answer("⛔ Доступ запрещен")
        return

    processing_msg = await message.answer("🔍 Анализирую изображение...")

    try:
        # Скачиваем фото (берём максимальное качество)
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)

        import aiohttp
        import base64

        photo_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"

        async with aiohttp.ClientSession() as session:
            async with session.get(photo_url) as resp:
                image_data = await resp.read()

        image_b64 = base64.b64encode(image_data).decode("utf-8")

        # Текст запроса от пользователя (если фото отправлено с подписью)
        user_prompt = message.caption or "Подробно опиши что изображено на фото. Отвечай на русском языке."

        # Запрос к vision модели через Groq
        import httpx
        from app.core.config import settings

        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": user_prompt
                        }
                    ]
                }
            ],
            "max_tokens": 1024,
            "temperature": 0.7
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

        result = data["choices"][0]["message"]["content"]
        await processing_msg.edit_text(f"🖼 <b>Анализ изображения:</b>\n\n{result}")

    except Exception as e:
        logger.error(f"Error analyzing photo: {e}")
        await processing_msg.edit_text(
            f"❌ <b>Не удалось проанализировать изображение</b>\n\n<code>{e}</code>"
        )


@router.message(F.document)
async def handle_document(message: Message):
    """Handle document messages — import Telegram JSON chat export"""
    user = message.from_user

    if user.id not in ALLOWED_USERS:
        await message.answer("⛔ Доступ запрещен")
        return

    doc = message.document

    if not doc.file_name or not doc.file_name.endswith(".json"):
        await message.answer(
            "📄 <b>Документ получен</b>\n\n"
            "Поддерживается импорт JSON-экспорта Telegram.\n"
            "Экспортируйте чат: <b>Telegram Desktop → чат → ⋮ → Экспорт истории → JSON</b>\n"
            "и отправьте файл <code>result.json</code>"
        )
        return

    if doc.file_size and doc.file_size > 50 * 1024 * 1024:
        await message.answer("❌ Файл слишком большой. Максимум 50 МБ.")
        return

    processing_msg = await message.answer("⏳ Загружаю и обрабатываю файл...")
    temp_path = f"/tmp/import_{user.id}_{doc.file_id}.json"

    try:
        file = await message.bot.get_file(doc.file_id)
        await message.bot.download_file(file.file_path, temp_path)
        await processing_msg.edit_text("🔍 Анализирую историю чата...")

        from app.core.skills_loader import skill_loader
        skill = skill_loader.get_skill("import_chat")

        if not skill:
            await processing_msg.edit_text(
                "❌ Скилл import_chat не загружен.\n"
                "Убедитесь что файл <code>skills/custom/import_chat.py</code> существует."
            )
            return

        context = {
            "user_id": user.id,
            "file_path": temp_path,
            "args": {"file_path": temp_path}
        }

        result = await skill.run(context)
        await processing_msg.edit_text(result)

    except Exception as e:
        logger.error(f"Error processing document from user {user.id}: {e}")
        await processing_msg.edit_text(
            f"❌ <b>Ошибка обработки файла:</b>\n<code>{e}</code>"
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.message(F.voice)
async def handle_voice(message: Message, state: FSMContext):
    """Handle voice messages with transcription"""
    user = message.from_user
    file_path = None
    
    logger.info(f"Voice message received from user {user.id}")
    
    # Check whitelist
    if user.id not in ALLOWED_USERS:
        logger.warning(f"Access denied for user {user.id}")
        await message.answer("⛔ Доступ запрещен")
        return
    
    # Check if it's a group chat and voice is enabled for groups
    chat_type = message.chat.type
    is_group = chat_type in ['group', 'supergroup']
    
    if is_group and not settings.ENABLE_VOICE_IN_GROUPS:
        logger.info(f"Voice processing disabled for groups")
        return
    
    # Create temp directory if not exists
    temp_dir = settings.TEMP_DIR
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        voice = message.voice
        
        # Check duration
        if voice.duration > settings.MAX_VOICE_DURATION:
            await message.answer(
                f"⚠️ <b>Слишком длинное голосовое сообщение</b>\n\n"
                f"Максимальная длительность: {settings.MAX_VOICE_DURATION} секунд\n"
                f"Ваше сообщение: {voice.duration} секунд\n\n"
                f"Пожалуйста, разбейте на части или отправьте текстом."
            )
            return
        
        # Show "typing" indicator
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # Download voice file
        voice_file = await message.bot.get_file(voice.file_id)
        file_path = os.path.join(temp_dir, f"voice_{user.id}_{voice.file_id}.ogg")
        
        logger.info(f"Downloading voice file to {file_path}")
        await message.bot.download_file(voice_file.file_path, file_path)
        
        # Show transcription indicator
        processing_msg = await message.answer(
            "🎤 <i>Распознаю голосовое сообщение...</i>"
        )
        
        # Transcribe
        from app.core.llm_client import llm_client
        transcribed_text = await llm_client.transcribe_audio(
            audio_file_path=file_path,
            language=None  # Auto-detect
        )
        
        # Delete processing message
        await processing_msg.delete()
        
        if not transcribed_text or transcribed_text.strip() == "":
            await message.answer(
                "🎤 <b>Не удалось распознать речь</b>\n\n"
                "Попробуйте:\n"
                "• Говорить четче\n"
                "• Уменьшить фоновый шум\n"
                "• Отправить текстовое сообщение"
            )
            return
        
        # Show transcribed text with attribution
        if is_group:
            # In groups, show user's name
            user_name = user.first_name or "Пользователь"
            if user.username:
                user_name = f"@{user.username}"
            await message.reply(
                f"🎤 <b>Распознано ({user_name}):</b>\n"
                f"<i>{transcribed_text}</i>\n\n"
                f"⏳ Обрабатываю...",
                quote=True
            )
        else:
            # In private chats, just show transcription
            await message.answer(
                f"🎤 <b>Распознано:</b>\n<i>{transcribed_text}</i>"
            )
        
        logger.info(f"Transcribed voice for user {user.id}: {transcribed_text[:100]}...")
        
        # Now process the transcribed text as a regular message
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # Get or create user in database
        async with async_session_maker() as session:
            db_user = await get_or_create_user(
                session,
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code
            )
            
            # Get user's agent mode
            agent_mode = await get_user_agent_mode(user.id)
            
            # Get conversation history
            from app.core.database import get_user_messages
            history = await get_user_messages(session, db_user.id, limit=20)
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in reversed(history)
            ]
            
            # Route to appropriate agent
            response = await agent_router.route_message(
                user_id=user.id,
                message=transcribed_text,
                agent_mode=agent_mode,
                conversation_history=conversation_history
            )
            
            # Save messages to database (both transcription and response)
            await save_message(
                session,
                user_id=db_user.id,
                role="user",
                content=f"[Голосовое] {transcribed_text}",
                agent_mode=agent_mode
            )
            
            await save_message(
                session,
                user_id=db_user.id,
                role="assistant",
                content=response,
                agent_mode=agent_mode
            )
        
        # Send response
        if len(response) > 4096:
            chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await message.answer(chunk)
                else:
                    await message.answer(f"<i>(продолжение {i+1}/{len(chunks)})</i>\n\n{chunk}")
        else:
            await message.answer(response)
            
    except Exception as e:
        logger.error(f"Error handling voice message: {e}")
        await message.answer(
            "⚠️ <b>Ошибка обработки голосового сообщения</b>\n\n"
            "Возможные причины:\n"
            "• Проблемы с API распознавания\n"
            "• Файл слишком большой\n"
            "• Неподдерживаемый формат\n\n"
            "Попробуйте отправить текстовое сообщение."
        )
    finally:
        # Cleanup temp file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up temp file: {file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file: {cleanup_error}")


@router.message(F.audio)
async def handle_audio(message: Message):
    """Handle audio files (mp3, etc.)"""
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    # Audio files can be processed same as voice if needed
    await message.answer(
        "🎵 <b>Аудиофайл получен</b>\n\n"
        "Для распознавания речи используйте голосовые сообщения Telegram.\n"
        "Аудиофайлы пока не поддерживаются."
    )

"""
Memory management handlers
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app.core.database import async_session_maker, get_or_create_user
from app.core.memory import vector_memory
from app.utils.keyboards import get_memory_menu_keyboard, get_cancel_keyboard
from app.utils.states import MemoryAdd, MemorySearch
from app.utils.helpers import format_memory, truncate_text
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "memory:menu")
async def memory_menu(callback: CallbackQuery):
    """Show memory menu"""
    await callback.message.edit_text(
        "🧠 <b>Менеджер памяти</b>\n\n"
        "Храните и управляйте вашими воспоминаниями:",
        reply_markup=get_memory_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("memory:add:"))
async def memory_add_start(callback: CallbackQuery, state: FSMContext):
    """Start adding a memory"""
    memory_type = callback.data.split(":")[2]
    
    type_names = {
        "note": "📝 Заметка",
        "trip": "✈️ Поездка",
        "budget": "💰 Бюджет",
        "plan": "📅 План"
    }
    
    type_hints = {
        "note": "Любая информация, которую вы хотите запомнить",
        "trip": "Детали поездки: пункт назначения, даты, планы",
        "budget": "Информация о бюджете: суммы, категории",
        "plan": "Будущие планы и цели"
    }
    
    await state.update_data(memory_type=memory_type)
    await state.set_state(MemoryAdd.waiting_content)
    
    await callback.message.edit_text(
        f"{type_names.get(memory_type, '📝')} <b>Добавить {memory_type.title()}</b>\n\n"
        f"Введите содержимое:\n\n"
        f"<i>Подсказка: {type_hints.get(memory_type, 'Введите детали')}</i>",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(MemoryAdd.waiting_content)
async def memory_add_content(message: Message, state: FSMContext):
    """Process memory content"""
    content = message.text
    data = await state.get_data()
    memory_type = data['memory_type']
    
    try:
        # Get user
        async with async_session_maker() as session:
            db_user = await get_or_create_user(
                session,
                telegram_id=message.from_user.id
            )
            
            # Add to vector memory
            vector_id = await vector_memory.add_memory(
                content=content,
                user_id=message.from_user.id,
                memory_type=memory_type,
                metadata={
                    "source": "manual",
                    "username": message.from_user.username
                }
            )
            
            # Also save to database
            from app.core.database import Memory
            memory = Memory(
                user_id=db_user.id,
                content=content,
                memory_type=memory_type,
                vector_id=vector_id
            )
            session.add(memory)
            await session.commit()
        
        await message.answer(
            f"✅ <b>{memory_type.title()} успешно сохранено!</b>\n\n"
            f"Я запомню это и смогу вспомнить, когда это будет актуально.",
            reply_markup=get_memory_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        await message.answer(
            f"❌ <b>Ошибка сохранения памяти:</b> {str(e)}",
            reply_markup=get_memory_menu_keyboard()
        )
    
    await state.clear()


@router.callback_query(F.data == "memory:search")
async def memory_search_start(callback: CallbackQuery, state: FSMContext):
    """Start memory search"""
    await state.set_state(MemorySearch.waiting_query)
    await callback.message.edit_text(
        "🔍 <b>Поиск воспоминаний</b>\n\n"
        "Введите поисковый запрос:\n\n"
        "<i>Я найду релевантные воспоминания по смыслу,\n"
        "не только точные совпадения.</i>",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(MemorySearch.waiting_query)
async def memory_search_query(message: Message, state: FSMContext):
    """Process search query"""
    query = message.text
    
    try:
        # Search memories
        memories = await vector_memory.search_memories(
            query=query,
            user_id=message.from_user.id,
            n_results=10
        )
        
        if not memories:
            await message.answer(
                "🔍 <b>Воспоминания не найдены</b>\n\n"
                "Попробуйте другой поисковый запрос или добавьте новые воспоминания!",
                reply_markup=get_memory_menu_keyboard()
            )
        else:
            response = f"🔍 <b>Найдено {len(memories)} воспоминаний:</b>\n\n"
            
            for i, mem in enumerate(memories, 1):
                response += f"{i}. <b>{mem['metadata'].get('memory_type', 'note').upper()}</b>\n"
                content = mem['content'][:200]
                if len(mem['content']) > 200:
                    content += "..."
                response += f"   {content}\n"
                response += f"   <i>Релевантность: {1 - mem['distance']:.2%}</i>\n\n"
            
            await message.answer(
                truncate_text(response),
                reply_markup=get_memory_menu_keyboard()
            )
        
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        await message.answer(
            f"❌ <b>Ошибка поиска воспоминаний:</b> {str(e)}",
            reply_markup=get_memory_menu_keyboard()
        )
    
    await state.clear()


@router.callback_query(F.data == "memory:stats")
async def memory_stats(callback: CallbackQuery):
    """Show memory statistics"""
    try:
        stats = await vector_memory.get_stats()
        
        # Get database stats
        async with async_session_maker() as session:
            from sqlalchemy import select, func
            from app.core.database import Memory
            
            result = await session.execute(select(func.count()).select_from(Memory))
            db_count = result.scalar()
            
            # Get by type
            result = await session.execute(
                select(Memory.memory_type, func.count())
                .group_by(Memory.memory_type)
            )
            by_type = result.all()
        
        response = "📊 <b>Статистика памяти</b>\n\n"
        response += f"<b>Векторное хранилище:</b>\n"
        for collection, count in stats.items():
            response += f"  • {collection.title()}: {count} элементов\n"
        
        response += f"\n<b>База данных:</b>\n"
        response += f"  • Всего воспоминаний: {db_count}\n"
        
        if by_type:
            response += f"\n<b>По типам:</b>\n"
            for mem_type, count in by_type:
                emoji = {
                    'note': '📝',
                    'trip': '✈️',
                    'budget': '💰',
                    'plan': '📅',
                    'dialog': '💬'
                }.get(mem_type, '📄')
                response += f"  {emoji} {mem_type.title()}: {count}\n"
        
        await callback.message.edit_text(
            response,
            reply_markup=get_memory_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка получения статистики:</b> {str(e)}",
            reply_markup=get_memory_menu_keyboard()
        )
    
    await callback.answer()

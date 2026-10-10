from datetime import datetime

from fastapi import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatHistory, ChatSession
from app.models.users import User
from app.db.db_config import AsyncSessionLocal
from app.crud.papers import get_paper_titles
from app.schemas.chat import ChatAskRequest

    
async def create_chat_session(db: AsyncSession, **values) -> ChatSession:
    chat_session = ChatSession(**values)
    db.add(chat_session)
    await db.flush()
    await db.refresh(chat_session)
    return chat_session

async def _create_session(user: User, question: str) -> int:
    """新建一个会话窗口，返回 session_id"""
    async with AsyncSessionLocal() as session:
        chat_session = await create_chat_session(
            session,
            user_id=user.id,
            title=question[:200],
            created_at=datetime.now(),
        )
        await session.commit()
        return chat_session.id

async def get_user_chat_sessions(db: AsyncSession, user_id: int, limit: int = 50) -> list[ChatSession]:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_session_messages(
    db: AsyncSession, session_id: int, user_id: int | None = None
) -> list[ChatHistory]:
    query = select(ChatHistory).where(ChatHistory.session_id == session_id)
    if user_id is not None:
        query = query.where(ChatHistory.user_id == user_id)
    result = await db.execute(
        query.order_by(ChatHistory.created_at.asc(), ChatHistory.id.asc())
    )
    return list(result.scalars().all())


async def create_chat_history(db: AsyncSession, **values) -> ChatHistory:
    history = ChatHistory(**values)
    db.add(history)
    await db.flush()
    await db.refresh(history)
    return history

# 喂给模型的历史消息最多取最近多少轮问答
CONTEXT_MAX_ROUNDS = 10

async def _build_context_messages(session_id: int, user_id: int) -> list[dict]:
    """读取该会话窗口最近的问答，拼成模型上下文消息列表（多轮记忆）"""

    async with AsyncSessionLocal() as session:
        rows = await get_session_messages(session, session_id, user_id=user_id)

    messages: list[dict] = []
    # - 是代表从最后开始取内容
    for row in rows[-CONTEXT_MAX_ROUNDS:]:
        messages.append({"role": "user", "content": row.question})
        if row.answer:
            messages.append({"role": "assistant", "content": row.answer})
    return messages

async def _get_selected_paper_titles(user: User, paper_ids: list[int]) -> dict[int, str]:
    """查询选中文献的标题，用于告知模型用户选择了哪些文献"""
    if not paper_ids:
        return {}

    try:
        async with AsyncSessionLocal() as session:
            return await get_paper_titles(session, user.id, paper_ids)
    except Exception as error:
        logger.error(f"[❌ AI问答]查询选中文献标题失败：{error}", exc_info=True)
        return {}


async def _save_chat_history(req: ChatAskRequest, user: User, session_id: int, answer_parts: list[str]) -> None:
    """问答结束后把本轮问答写入 chat_history 表（归属当前会话窗口），失败只记录日志"""
    answer = "".join(answer_parts).strip()
    if not answer:
        return

    try:
        from app.db.db_config import AsyncSessionLocal
        from app.crud.chat import create_chat_history

        async with AsyncSessionLocal() as session:
            await create_chat_history(
                session,
                user_id=user.id,
                session_id=session_id,
                question=req.question.strip(),
                answer=answer,
                paper_ids=",".join(map(str, req.paper_ids)) or None,
                created_at=datetime.now(),
            )
            await session.commit()
    except Exception as error:
        logger.error(f"[❌ AI问答]保存历史会话失败：{error}", exc_info=True)
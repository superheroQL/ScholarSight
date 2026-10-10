import asyncio
import json
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_config import get_db
from app.models.users import User
from app.utils.auth import get_current_user
from app.utils.logger_handler import logger
from app.schemas.chat import ChatAskRequest
from app.crud.chat import _build_context_messages, _create_session, _get_selected_paper_titles, _save_chat_history
from app.agent.agent_manager import _get_agent


router = APIRouter(prefix='/api/v1/chat', tags=['chat'])


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/ask")
async def ask_chat(req: ChatAskRequest, user: User = Depends(get_current_user)):
    """
    AI 问答：问题 -> ReactAgent（内含 RAG 检索等工具）-> SSE 流式返回
    返回 OpenAI 兼容的增量格式，前端已有的 SSE 解析器可直接使用
    未指定 session_id 时自动新建会话窗口；指定则在原窗口内继续提问
    问答结束后自动把本轮记录保存到 chat_history 表
    """
    if not req.question.strip():
        return StreamingResponse(
            iter([_sse_event({"error": {"message": "问题不能为空"}})]),
            media_type="text/event-stream",
        )

    # 确定会话窗口：未指定则新建
    session_id = req.session_id
    if session_id is None:
        try:
            session_id = await _create_session(user, req.question.strip())
        except Exception as error:
            logger.error(f"[❌ AI问答]创建会话窗口失败：{error}", exc_info=True)
            return StreamingResponse(
                iter([_sse_event({"error": {"message": f"创建会话失败：{error}"}})]),
                media_type="text/event-stream",
            )

    # 读取该会话窗口的历史问答作为多轮上下文
    history_messages = await _build_context_messages(session_id, user.id)

    # 用户选择了文献时，把文献标题注入提问，让模型明确知道选中了哪些文献
    question = req.question.strip()
    paper_titles = await _get_selected_paper_titles(user, req.paper_ids)
    if paper_titles:
        title_lines = []
        for index, paper_id in enumerate(req.paper_ids, 1):
            title = paper_titles.get(paper_id)
            if title:
                title_lines.append(f"{index}. {title}")
        if title_lines:
            question = (
                f"用户本次提问选择的文献如下：\n"
                + "\n".join(title_lines)
                + "\n\n回答时请优先基于这些文献的内容。\n\n用户问题："
                + req.question.strip()
            )

    agent = _get_agent()

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()
        answer_parts: list[str] = []

        def produce():
            try:
                # 设置本次请求的 RAG 检索范围：用户选中文献时只在选中文献中检索
                from app.agent.tools.agent_tools import set_rag_context
                set_rag_context(req.paper_ids or None)

                for chunk in agent.execute_stream(
                    question,
                    context={"paper_ids": req.paper_ids, "user_id": user.id},
                    history_messages=history_messages,
                ):
                    queue.put_nowait(("data", chunk))
            except Exception as error:
                logger.error(f"[❌ AI问答]问题「{req.question[:30]}」处理失败：{error}", exc_info=True)
                queue.put_nowait(("error", str(error)))
            queue.put_nowait(("done", None))

        # Agent 内部是同步阻塞调用（模型接口 + 工具），放到线程执行，主线程只做流式转发
        thread = threading.Thread(target=produce, daemon=True)
        thread.start()

        # 首个事件携带 session_id，前端据此知道当前会话窗口
        yield _sse_event({"session_id": session_id, "choices": []})

        while True:
            kind, payload = await queue.get()
            if kind == "data":
                answer_parts.append(payload)
                # OpenAI 兼容增量格式：choices[0].delta.content
                yield _sse_event({"choices": [{"delta": {"content": payload}}]})
            elif kind == "error":
                yield _sse_event({"error": {"message": payload}})
                return
            elif kind == "done":
                # 流式结束后保存本轮问答记录
                await _save_chat_history(req, user, session_id, answer_parts)
                yield _sse_event({"choices": [{"delta": {"content": ""}}]}) + "data: [DONE]\n\n"
                return

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/history")
async def get_chat_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    获取当前用户的会话窗口列表（按创建时间倒序）
    """
    from app.crud.chat import get_user_chat_sessions

    sessions = await get_user_chat_sessions(db, user.id)
    return {
        'code': 200,
        'message': '获取历史会话成功',
        'data': [
            {
                'id': chat_session.id,
                'title': chat_session.title,
                'created_at': chat_session.created_at.isoformat() if chat_session.created_at else None,
            }
            for chat_session in sessions
        ],
    }


@router.get("/history/{session_id}")
async def get_chat_session_messages(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    获取某个会话窗口内的全部问答记录（按时间正序）
    """
    from app.crud.chat import get_session_messages

    messages = await get_session_messages(db, session_id, user_id=user.id)
    if not messages:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {
        'code': 200,
        'message': '获取会话记录成功',
        'data': [
            {
                'id': history.id,
                'question': history.question,
                'answer': history.answer,
                'paper_ids': [int(x) for x in history.paper_ids.split(',')] if history.paper_ids else [],
                'created_at': history.created_at.isoformat() if history.created_at else None,
            }
            for history in messages
        ],
    }

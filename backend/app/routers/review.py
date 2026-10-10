import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.papers import get_paper_titles
from app.crud.review import get_paper_review, get_user_paper_reviews, upsert_paper_review
from app.db.db_config import get_db
from app.models.users import User
from app.utils.auth import get_current_user
from app.utils.logger_handler import logger


router = APIRouter(prefix='/api/v1/review', tags=['review'])


class ReviewRequest(BaseModel):
    paper_ids: list[int]
    topic: str


def _serialize(row) -> dict:
    return {
        'id': row.id,
        'topic': row.topic,
        'paper_ids': [int(x) for x in row.paper_ids.split(',')] if row.paper_ids else [],
        'content': row.content,
        'model_name': row.model_name,
        'created_at': row.created_at.isoformat() if row.created_at else None,
        'updated_at': row.updated_at.isoformat() if row.updated_at else None,
    }


@router.post("")
async def generate_review(
    req: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    生成文献综述：
    按主题在每篇选中文献的向量分片中检索 -> 按 review_prompt.txt 提示词由 LLM 生成综述 -> 保存 paper_review 表
    """
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail='请填写综述主题')
    if len(req.paper_ids) < 2 or len(req.paper_ids) > 6:
        raise HTTPException(status_code=400, detail='请选择 2~6 篇参考文献')

    # 校验文献归属并获取标题
    paper_titles = await get_paper_titles(db, user.id, req.paper_ids)
    if len(paper_titles) != len(set(req.paper_ids)):
        raise HTTPException(status_code=404, detail='部分论文不存在或不属于当前用户')

    from app.model.factory import chat_model
    from app.rag.review_service import generate_review

    # 综述生成是同步阻塞调用（检索 + LLM），放到线程池执行
    content = await asyncio.to_thread(generate_review, topic, req.paper_ids, paper_titles)
    if not content:
        raise HTTPException(
            status_code=400,
            detail='所选文献在向量库中暂无可检索的内容，请先确认论文已完成向量化入库',
        )

    model_name = getattr(chat_model, "model_name", "") or "unknown"
    row = await upsert_paper_review(db, user.id, req.paper_ids, topic, content, model_name)
    await db.commit()
    logger.info(f"[✅ 文献综述]用户 {user.id} 综述「{topic}」生成并入库（{len(req.paper_ids)} 篇文献）")
    return {'code': 200, 'message': '文献综述已生成', 'data': _serialize(row)}


@router.get("")
async def list_reviews(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前用户保存的历史综述列表（不含正文）"""
    rows = await get_user_paper_reviews(db, user.id)
    return {
        'code': 200,
        'message': '获取综述列表成功',
        'data': [
            {
                'id': row.id,
                'topic': row.topic,
                'paper_ids': [int(x) for x in row.paper_ids.split(',')] if row.paper_ids else [],
                'model_name': row.model_name,
                'created_at': row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
    }


@router.get("/{review_id}")
async def get_review_detail(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取某篇综述的完整内容"""
    row = await get_paper_review(db, review_id, user.id)
    if not row:
        raise HTTPException(status_code=404, detail='综述不存在')
    return {'code': 200, 'message': '获取综述成功', 'data': _serialize(row)}

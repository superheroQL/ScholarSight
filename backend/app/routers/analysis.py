import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.analysis import get_paper_analysis, upsert_paper_analysis
from app.crud.papers import get_paper_by_id
from app.db.db_config import get_db
from app.models.users import User
from app.utils.auth import get_current_user
from app.utils.logger_handler import logger


router = APIRouter(prefix='/api/v1/analysis', tags=['analysis'])


def _serialize(row) -> dict:
    return {
        'id': row.id,
        'paper_id': row.paper_id,
        'model_name': row.model_name,
        'research_question': row.research_question,
        'core_method': row.core_method,
        'datasets': row.datasets,
        'experimental_results': row.experimental_results,
        'core_conclusion': row.core_conclusion,
        'limitations_and_insights': row.limitations_and_insights,
        'evidence_and_implications': row.evidence_and_implications,
        'further_questions': row.further_questions,
        'created_at': row.created_at.isoformat() if row.created_at else None,
        'updated_at': row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/{paper_id}")
async def get_analysis(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    获取论文已有的分析结果（没有分析过返回 404）
    """
    row = await get_paper_analysis(db, paper_id, user.id)
    if not row:
        raise HTTPException(status_code=404, detail='该论文还没有分析结果')
    return {'code': 200, 'message': '获取分析结果成功', 'data': _serialize(row)}


@router.post("/{paper_id}")
async def run_analysis(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    对论文执行智能分析：
    按 8 个分析任务分别构造 Query -> 向量库检索论文片段 -> LLM 结构化抽取 -> 保存 paper_analysis 表
    分析耗时较长（多次检索 + 模型调用），接口会等待完成后返回结果
    """
    paper = await get_paper_by_id(db, paper_id)
    if not paper or paper.user_id != user.id:
        raise HTTPException(status_code=404, detail='论文不存在')

    from app.model.factory import chat_model
    from app.rag.paper_analysis_service import analyze_paper

    # 分析过程是同步阻塞调用（检索 + LLM），放到线程池执行
    analysis = await asyncio.to_thread(analyze_paper, paper_id, user.id, paper.title)

    model_name = getattr(chat_model, "model_name", "") or "unknown"
    row = await upsert_paper_analysis(db, paper_id, user.id, analysis, model_name)
    await db.commit()
    logger.info(f"[✅ 论文分析]论文 {paper_id} 分析完成并入库")
    return {'code': 200, 'message': '论文分析完成', 'data': _serialize(row)}

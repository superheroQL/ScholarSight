import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.multi_analysis import get_multi_analysis, get_user_multi_analyses, upsert_multi_analysis
from app.crud.papers import get_papers_by_ids
from app.db.db_config import get_db
from app.models.users import User
from app.utils.auth import get_current_user
from app.utils.logger_handler import logger


router = APIRouter(prefix='/api/v1/compare', tags=['compare'])


class CompareRequest(BaseModel):
    paper_ids: list[int]
    topic: str = ""


def _serialize(row) -> dict:
    return {
        'id': row.id,
        'topic': row.topic,
        'paper_ids': [int(x) for x in row.paper_ids.split(',')] if row.paper_ids else [],
        'analysis': row.analysis,
        'matrix': row.matrix,
        'synthesis': row.synthesis,
        'model_name': row.model_name,
        'created_at': row.created_at.isoformat() if row.created_at else None,
        'updated_at': row.updated_at.isoformat() if row.updated_at else None,
    }


@router.post("")
async def compare_papers(
    req: CompareRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    多论文对比分析：
    分别在每篇选中文献的向量分片中检索 -> 按 multi_paper_analysis_prompt.txt
    由 LLM 输出 12 个维度分析 -> 映射为对比矩阵 + 综合分析 -> 保存 paper_multi_analysis 表
    """
    if len(req.paper_ids) < 2 or len(req.paper_ids) > 6:
        raise HTTPException(status_code=400, detail='请选择 2~6 篇论文')

    papers = await get_papers_by_ids(db, user.id, req.paper_ids)
    if len(papers) != len(set(req.paper_ids)):
        raise HTTPException(status_code=404, detail='部分论文不存在或不属于当前用户')

    papers_info = {
        paper.id: {
            "title": paper.title,
            "authors": paper.authors,
            "publish_year": paper.publish_year,
        }
        for paper in papers
    }

    from app.model.factory import chat_model
    from app.rag.multi_analysis_service import analyze_multi_papers

    # 分析过程是同步阻塞调用（检索 + LLM），放到线程池执行
    analysis, matrix, synthesis = await asyncio.to_thread(
        analyze_multi_papers, req.paper_ids, papers_info
    )
    if not matrix and not synthesis.get("points"):
        raise HTTPException(
            status_code=400,
            detail='所选论文在向量库中暂无可检索的内容，请先确认论文已完成向量化入库',
        )

    model_name = getattr(chat_model, "model_name", "") or "unknown"
    row = await upsert_multi_analysis(
        db, user.id, req.paper_ids, req.topic.strip() or "多论文对比分析",
        analysis, matrix, synthesis, model_name,
    )
    await db.commit()
    logger.info(f"[✅ 多论文分析]用户 {user.id} 完成 {len(req.paper_ids)} 篇论文对比分析并入库")
    return {'code': 200, 'message': '多论文分析完成', 'data': _serialize(row)}


@router.get("")
async def list_analyses(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前用户的历史多论文分析列表（不含完整结果）"""
    rows = await get_user_multi_analyses(db, user.id)
    return {
        'code': 200,
        'message': '获取分析列表成功',
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


@router.get("/{analysis_id}")
async def get_analysis_detail(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取某次多论文分析的完整结果"""
    row = await get_multi_analysis(db, analysis_id, user.id)
    if not row:
        raise HTTPException(status_code=404, detail='分析结果不存在')
    return {'code': 200, 'message': '获取分析结果成功', 'data': _serialize(row)}

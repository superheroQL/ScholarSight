from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.multi_analysis import PaperMultiAnalysis


async def upsert_multi_analysis(
    db: AsyncSession, user_id: int, paper_ids: list[int], topic: str,
    analysis: dict, matrix: list, synthesis: dict, model_name: str,
) -> PaperMultiAnalysis:
    """保存分析结果：同一用户 + 同一组文献重新分析时覆盖旧结果"""
    paper_ids_str = ",".join(map(str, paper_ids))
    await db.execute(
        delete(PaperMultiAnalysis).where(
            PaperMultiAnalysis.user_id == user_id,
            PaperMultiAnalysis.paper_ids == paper_ids_str,
        )
    )
    now = datetime.now()
    row = PaperMultiAnalysis(
        user_id=user_id,
        paper_ids=paper_ids_str,
        topic=topic,
        analysis=analysis,
        matrix=matrix,
        synthesis=synthesis,
        model_name=model_name,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def get_multi_analysis(
    db: AsyncSession, analysis_id: int, user_id: int
) -> PaperMultiAnalysis | None:
    result = await db.execute(
        select(PaperMultiAnalysis).where(
            PaperMultiAnalysis.id == analysis_id,
            PaperMultiAnalysis.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_user_multi_analyses(
    db: AsyncSession, user_id: int, limit: int = 20
) -> list[PaperMultiAnalysis]:
    result = await db.execute(
        select(PaperMultiAnalysis)
        .where(PaperMultiAnalysis.user_id == user_id)
        .order_by(PaperMultiAnalysis.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())

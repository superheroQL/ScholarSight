from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import PaperAnalysis


async def upsert_paper_analysis(
    db: AsyncSession, paper_id: int, user_id: int, analysis: dict, model_name: str
) -> PaperAnalysis:
    """保存分析结果：一篇论文只保留最后一次（先删旧记录再插入）"""
    await db.execute(
        delete(PaperAnalysis).where(PaperAnalysis.paper_id == paper_id)
    )
    now = datetime.now()
    row = PaperAnalysis(
        paper_id=paper_id,
        user_id=user_id,
        research_question=analysis.get("research_question"),
        core_method=analysis.get("core_method"),
        datasets=analysis.get("datasets"),
        experimental_results=analysis.get("experimental_results"),
        core_conclusion=analysis.get("core_conclusion"),
        limitations_and_insights=analysis.get("limitations_and_insights"),
        evidence_and_implications=analysis.get("evidence_and_implications"),
        further_questions=analysis.get("further_questions"),
        model_name=model_name,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def get_paper_analysis(
    db: AsyncSession, paper_id: int, user_id: int
) -> PaperAnalysis | None:
    result = await db.execute(
        select(PaperAnalysis).where(
            PaperAnalysis.paper_id == paper_id,
            PaperAnalysis.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()

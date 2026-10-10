from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import PaperReview


async def upsert_paper_review(
    db: AsyncSession, user_id: int, paper_ids: list[int], topic: str,
    content: str, model_name: str,
) -> PaperReview:
    """保存综述：同一用户 + 同一主题 + 同一组文献重新生成时覆盖旧结果"""
    paper_ids_str = ",".join(map(str, paper_ids))
    await db.execute(
        delete(PaperReview).where(
            PaperReview.user_id == user_id,
            PaperReview.topic == topic,
            PaperReview.paper_ids == paper_ids_str,
        )
    )
    now = datetime.now()
    row = PaperReview(
        user_id=user_id,
        paper_ids=paper_ids_str,
        topic=topic,
        content=content,
        model_name=model_name,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def get_paper_review(db: AsyncSession, review_id: int, user_id: int) -> PaperReview | None:
    result = await db.execute(
        select(PaperReview).where(
            PaperReview.id == review_id,
            PaperReview.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_user_paper_reviews(db: AsyncSession, user_id: int, limit: int = 20) -> list[PaperReview]:
    result = await db.execute(
        select(PaperReview)
        .where(PaperReview.user_id == user_id)
        .order_by(PaperReview.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())

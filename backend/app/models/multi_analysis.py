from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.users import Base


class PaperMultiAnalysis(Base):
    """多论文对比分析结果表（同一用户 + 同一组文献重新分析时覆盖旧结果）"""
    __tablename__ = 'paper_multi_analysis'
    __table_args__ = {'mysql_charset': 'utf8mb4'}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    paper_ids: Mapped[str] = mapped_column(String(500), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(500))
    analysis: Mapped[dict | None] = mapped_column(JSON)
    matrix: Mapped[list | None] = mapped_column(JSON)
    synthesis: Mapped[dict | None] = mapped_column(JSON)
    model_name: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

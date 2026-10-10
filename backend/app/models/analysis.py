from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.users import Base


class PaperAnalysis(Base):
    """论文智能分析结果表（一篇论文只保留最后一次分析结果）"""
    __tablename__ = 'paper_analysis'
    __table_args__ = {'mysql_charset': 'utf8mb4'}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    paper_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    research_question: Mapped[dict | None] = mapped_column(JSON)
    core_method: Mapped[dict | None] = mapped_column(JSON)
    datasets: Mapped[list | None] = mapped_column(JSON)
    experimental_results: Mapped[dict | None] = mapped_column(JSON)
    core_conclusion: Mapped[dict | None] = mapped_column(JSON)
    limitations_and_insights: Mapped[dict | None] = mapped_column(JSON)
    evidence_and_implications: Mapped[list | None] = mapped_column(JSON)
    further_questions: Mapped[list | None] = mapped_column(JSON)
    model_name: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

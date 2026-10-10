from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.users import Base


class ChatSession(Base):
    """AI 问答会话窗口表（一个会话窗口包含多轮问答）"""
    __tablename__ = 'chat_session'
    __table_args__ = {'mysql_charset': 'utf8mb4'}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)


class ChatHistory(Base):
    """AI 问答历史记录表（每轮问答一行，归属某个会话窗口）"""
    __tablename__ = 'chat_history'
    __table_args__ = {'mysql_charset': 'utf8mb4'}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    session_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    paper_ids: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime | None] = mapped_column(DateTime)

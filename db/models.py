from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Sentence(Base):
    __tablename__ = "sentences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    original: Mapped[str] = mapped_column(Text, nullable=False)
    corrected: Mapped[str] = mapped_column(Text, nullable=False)
    natural: Mapped[str] = mapped_column(Text, nullable=False)
    has_mistakes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tip: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    mistakes: Mapped[list[SentenceMistake]] = relationship(
        "SentenceMistake", back_populates="sentence", cascade="all, delete-orphan"
    )


class SentenceMistake(Base):
    __tablename__ = "sentence_mistakes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sentence_id: Mapped[int] = mapped_column(
        ForeignKey("sentences.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # grammar | word_choice | fluency
    original: Mapped[str | None] = mapped_column(Text, nullable=True)
    fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    sentence: Mapped[Sentence] = relationship("Sentence", back_populates="mistakes")

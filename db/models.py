import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.session import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    ip: Mapped[str] = mapped_column(String(64), index=True)
    spec: Mapped[dict] = mapped_column(JSONB)
    spec_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    count_qualified: Mapped[int | None] = mapped_column(Integer, nullable=True)
    from_cache: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    results: Mapped[list["JobResult"]] = relationship(
        back_populates="job", cascade="all, delete-orphan")


class JobResult(Base):
    __tablename__ = "job_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict] = mapped_column(JSONB)
    job: Mapped["Job"] = relationship(back_populates="results")


class ValuationCache(Base):
    __tablename__ = "valuations_cache"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

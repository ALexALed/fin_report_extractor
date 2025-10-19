from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all financial report persistence models."""


class ReportRecord(Base):
    """ORM model representing a processed report."""

    __tablename__ = "processed_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metrics: Mapped[List["ReportMetricRecord"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
    )


class ReportMetricRecord(Base):
    """ORM model storing metric values associated with a processed report."""

    __tablename__ = "processed_report_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("processed_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    previous_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    report: Mapped[ReportRecord] = relationship(back_populates="metrics")

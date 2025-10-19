from typing import Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from core.fin_report_processors.db_models import (
    ReportMetricRecord,
    ReportRecord,
)
from core.fin_report_processors.models import MetricValues, ProcessedData
from core.fin_report_processors.repository import ProcessedReportRepository


class SqlAlchemyProcessedReportRepository(ProcessedReportRepository):
    """Async SQLAlchemy implementation of ProcessedReportRepository."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save(self, processed_report: ProcessedData) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                record = await session.get(
                    ReportRecord,
                    str(processed_report.report_id),
                    options=(selectinload(ReportRecord.metrics),),
                )
                if record is None:
                    record = ReportRecord(
                        id=str(processed_report.report_id),
                        processed_at=processed_report.processed_at,
                    )
                    session.add(record)
                else:
                    record.processed_at = processed_report.processed_at

                record.error = processed_report.error
                record.metrics.clear()

                if processed_report.error is None:
                    for name, values in processed_report.data.items():
                        record.metrics.append(
                            ReportMetricRecord(
                                name=name,
                                current_value=values.current,
                                previous_value=values.previous,
                            )
                        )

    async def get(self, report_id: UUID) -> ProcessedData | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ReportRecord)
                .options(selectinload(ReportRecord.metrics))
                .where(ReportRecord.id == str(report_id))
            )
            record = result.scalar_one_or_none()
            if record is None:
                return None

            metrics: Dict[str, MetricValues] = {
                metric.name: MetricValues(
                    current=metric.current_value,
                    previous=metric.previous_value,
                )
                for metric in record.metrics
            }

            return ProcessedData(
                report_id=UUID(record.id),
                data=metrics,
                processed_at=record.processed_at,
                error=record.error,
            )

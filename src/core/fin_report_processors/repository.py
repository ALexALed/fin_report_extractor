import abc
from uuid import UUID

from core.fin_report_processors.models import ProcessedData


class ProcessedReportRepository(abc.ABC):
    """Repository contract for storing and retrieving processed report data."""

    @abc.abstractmethod
    async def save(self, processed_report: ProcessedData) -> None:
        """Persist the provided processed report."""

    @abc.abstractmethod
    async def get(self, report_id: UUID) -> ProcessedData | None:
        """Fetch a processed report by its identifier."""

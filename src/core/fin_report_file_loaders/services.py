import abc
from typing import Any

from core.fin_report_file_loaders.models import ReportFileData


class ReportFileReader(abc.ABC):
    @abc.abstractmethod
    async def read(self, file_path: str) -> ReportFileData:
        """Read the raw report file and return its structured contents."""

    @abc.abstractmethod
    async def structured_output(self, file_path: str) -> dict[str, Any]:
        "Provide structured output for the report file"

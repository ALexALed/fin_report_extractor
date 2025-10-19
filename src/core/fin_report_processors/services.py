import abc
from typing import Callable, Dict, Mapping, Optional

from core.fin_report_file_loaders.models import ReportFileData
from core.fin_report_processors.models import (
    DefaultMetricsModel,
    ProcessedData,
)

ProcessorFactory = Callable[[Mapping[str, Dict[str, object]]], "ReportDataProcessor"]


class ReportDataProcessor(abc.ABC):
    """Abstract base for processors that turn files into ProcessedData instances."""

    def __init__(
        self,
        metrics_config: Mapping[str, Dict[str, object]],
    ) -> None:
        self._metrics_config: Dict[str, Dict[str, object]] = {
            metric_name: dict(config) for metric_name, config in metrics_config.items()
        }

    @property
    def metrics_config(self) -> Mapping[str, Dict[str, object]]:
        return self._metrics_config

    @abc.abstractmethod
    async def process(
        self, report_file_data: ReportFileData
    ) -> ProcessedData | Exception:
        """Normalize the provided report file data."""


class ReportDataBuilder:
    """Builder responsible for configuring and delegating to ReportDataProcessor."""

    DEFAULT_METRICS_MODEL = DefaultMetricsModel()

    def __init__(
        self,
        metrics_config: Optional[
            Mapping[str, Dict[str, object]] | DefaultMetricsModel
        ] = None,
        processor_factory: ProcessorFactory | None = None,
    ) -> None:
        if metrics_config is None:
            self.metrics_config = self.DEFAULT_METRICS_MODEL.model_dump(mode="python")
        elif isinstance(metrics_config, DefaultMetricsModel):
            self.metrics_config = metrics_config.model_dump(mode="python")
        else:
            self.metrics_config = dict(metrics_config)

        self._processor_factory = processor_factory

    def build_processor(self) -> ReportDataProcessor:
        return self._processor_factory(metrics_config=self.metrics_config)

    async def process(
        self, report_file_data: ReportFileData
    ) -> ProcessedData | Exception:
        processor = self.build_processor()
        return await processor.process(report_file_data)

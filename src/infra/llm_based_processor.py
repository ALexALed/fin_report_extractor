import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Mapping, Optional
from uuid import uuid7

from langchain_core.language_models.base import BaseLanguageModel
from pydantic import BaseModel, Field

from core.fin_report_file_loaders.models import ReportFileData
from core.fin_report_processors.models import MetricValues, ProcessedData
from core.fin_report_processors.services import (
    ReportDataProcessor as BaseReportDataProcessor,
)

logger = logging.getLogger(__name__)


class ExtractedMetric(BaseModel):
    """Structured metric data returned by the LLM."""

    name: str = Field(description="Canonical metric name to populate")
    current: Optional[str] = Field(
        default=None, description="Value for the current reporting period"
    )
    previous: Optional[str] = Field(
        default=None, description="Value for the previous reporting period"
    )


class ExtractionResult(BaseModel):
    """Complete LLM response capturing report-level details."""

    report_id: Optional[str] = Field(
        default=None, description="Identifier inferred by the LLM, if any"
    )
    metrics: List[ExtractedMetric] = Field(
        default_factory=list,
        description="List of metrics extracted from the report content",
    )


DEFAULT_PROMPT_TEMPLATE = """You are an assistant that extracts structured financial metrics.

Report metadata (JSON):
{metadata_json}

Report content:
{content}

Extract the metrics listed below. Use the metric names exactly as provided.
Respond using the structured schema supplied to you.
Metrics to extract (JSON):
{metrics_json}
"""


class ReportDataProcessor(BaseReportDataProcessor):
    """LangChain-backed processor that delegates extraction to an LLM."""

    def __init__(
        self,
        llm: BaseLanguageModel,
        metrics_config: Mapping[str, Dict[str, object]],
        prompt_template: str | None = None,
    ) -> None:
        super().__init__(metrics_config=metrics_config)
        self._llm = llm
        self._prompt_template = prompt_template or DEFAULT_PROMPT_TEMPLATE
        self._structured_llm = llm.with_structured_output(ExtractionResult)

    async def process(
        self, report_file_data: ReportFileData
    ) -> ProcessedData | Exception:
        metadata = report_file_data.metadata or {}
        content = report_file_data.content or ""
        prompt = self._prompt_template.format(
            metadata_json=json.dumps(
                metadata, default=str, ensure_ascii=False, indent=2
            ),
            content=content,
            metrics_json=json.dumps(self.metrics_config, ensure_ascii=False, indent=2),
        )

        try:
            extraction: ExtractionResult = await self._structured_llm.ainvoke(prompt)
        except Exception as exc:  # noqa: BLE001
            logger.exception("LLM-based data extraction failed: %s", exc)
            return exc

        processed_metrics = self._build_metrics_from_extraction(extraction)
        report_id = uuid7()

        return ProcessedData(
            report_id=report_id,
            data=processed_metrics,
            processed_at=datetime.now(timezone.utc),
        )

    def _build_metrics_from_extraction(
        self,
        extraction: ExtractionResult,
    ) -> Dict[str, MetricValues]:
        processed: Dict[str, MetricValues] = {
            metric_name: MetricValues() for metric_name in self.metrics_config.keys()
        }

        for metric in extraction.metrics:
            name = metric.name
            if name not in processed:
                continue
            processed[name] = MetricValues(
                current=metric.current, previous=metric.previous
            )

        return processed

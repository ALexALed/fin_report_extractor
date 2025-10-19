from datetime import datetime, timezone
from typing import Dict, Mapping, Optional, Sequence, Tuple, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MetricValues(BaseModel):
    """Container for current and previous period metric values."""

    current: Optional[str] = Field(default=None)
    previous: Optional[str] = Field(default=None)

    model_config = ConfigDict(populate_by_name=True)


class ProcessedData(BaseModel):
    """Structured financial report data produced by the processor layer."""

    report_id: UUID = Field(
        ..., description="Unique identifier for the processed report"
    )
    data: Dict[str, MetricValues] = Field(
        default_factory=dict,
        description="Normalized financial metrics keyed by their canonical names",
    )
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp (UTC) when processing completed",
    )
    error: Optional[str] = Field(
        default=None,
        description="Captured error details when processing fails",
    )

    model_config = ConfigDict(populate_by_name=True)


MetadataKeyConfig = Union[Mapping[str, str], Sequence[str], str, None]


class MetricConfig(BaseModel):
    """Configuration for locating a specific metric in report data."""

    aliases: Tuple[str, ...] = Field(default_factory=tuple)
    metadata_keys: MetadataKeyConfig = Field(default=None)

    model_config = ConfigDict(populate_by_name=True)


class DefaultMetricsModel(BaseModel):
    """Default metric configuration bundled for builders/processors."""

    non_current_assets: MetricConfig = Field(
        default_factory=lambda: MetricConfig(
            aliases=("non current assets", "non-current assets"),
            metadata_keys=("non_current_assets_current", "non_current_assets_previous"),
        )
    )
    current_assets: MetricConfig = Field(
        default_factory=lambda: MetricConfig(
            aliases=("current assets",),
            metadata_keys=("current_assets_current", "current_assets_previous"),
        )
    )
    prepaid_expenses: MetricConfig = Field(
        default_factory=lambda: MetricConfig(
            aliases=("prepaid expenses", "prepaid expense"),
            metadata_keys=("prepaid_expenses_current", "prepaid_expenses_previous"),
        )
    )
    deferred_tax_assets: MetricConfig = Field(
        default_factory=lambda: MetricConfig(
            aliases=("deferred tax assets", "deferred tax asset"),
            metadata_keys=(
                "deferred_tax_assets_current",
                "deferred_tax_assets_previous",
            ),
        )
    )

    model_config = ConfigDict(populate_by_name=True)

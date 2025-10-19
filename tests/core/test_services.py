from uuid import uuid7

import pytest
from dependency_injector import providers

from core.fin_report_file_loaders.models import ReportFileData
from core.fin_report_processors.models import MetricValues, ProcessedData
from core.fin_report_processors.services import ReportDataBuilder, ReportDataProcessor


class StubReportDataProcessor(ReportDataProcessor):
    def __init__(self, metrics_config, *, process_result=None):
        super().__init__(metrics_config=metrics_config)
        self._process_result = process_result
        self.process_calls: list[ReportFileData] = []

    async def process(self, report_file_data: ReportFileData) -> ProcessedData:
        self.process_calls.append(report_file_data)
        return self._process_result


@pytest.mark.asyncio
async def test_report_data_builder_process_delegates_to_factory(
    app_container, anyio_backend
):
    expected_result = ProcessedData(
        report_id=uuid7(),
        data={"metric": MetricValues(current="1", previous="0")},
    )
    factory_calls = {"count": 0, "metrics": None}

    def factory(metrics_config):
        factory_calls["count"] += 1
        factory_calls["metrics"] = metrics_config
        return StubReportDataProcessor(
            metrics_config=metrics_config,
            process_result=expected_result,
        )

    with app_container.override_providers(
        report_data_processor_factory=providers.Factory(factory)
    ):
        builder = app_container.report_data_builder()
        report_file_data = ReportFileData(content="body", metadata={"report_id": "42"})

        result_first = await builder.process(report_file_data)
        result_second = await builder.process(report_file_data)

    assert result_first.data == expected_result.data
    assert result_second.data == expected_result.data
    assert factory_calls["count"] == 2
    assert set(factory_calls["metrics"].keys()) >= {
        "non_current_assets",
        "current_assets",
        "prepaid_expenses",
        "deferred_tax_assets",
    }


@pytest.mark.asyncio
async def test_report_data_builder_uses_custom_metrics_config():
    custom_metrics = {"custom_metric": {"aliases": ("alias",)}}
    expected_result = ProcessedData(
        report_id=uuid7(),
        data={"custom_metric": MetricValues(current="5", previous=None)},
    )
    factory_calls = {"count": 0, "metrics": None}

    def factory(metrics_config):
        factory_calls["count"] += 1
        factory_calls["metrics"] = metrics_config
        return StubReportDataProcessor(
            metrics_config=metrics_config,
            process_result=expected_result,
        )

    builder = ReportDataBuilder(
        metrics_config=custom_metrics,
        processor_factory=factory,
    )
    result = await builder.process(ReportFileData(content="custom", metadata={}))

    assert result.data == expected_result.data
    assert factory_calls["count"] == 1
    assert factory_calls["metrics"] == custom_metrics

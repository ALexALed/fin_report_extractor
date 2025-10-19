from uuid import uuid7

import pytest

from core.fin_report_file_loaders.models import ReportFileData
from infra.llm_based_processor import (
    ExtractedMetric,
    ExtractionResult,
    ReportDataProcessor,
)


class _StructuredLLMStub:
    def __init__(self, response: ExtractionResult):
        self._response = response
        self.invocations: list[str] = []

    def invoke(self, prompt: str) -> ExtractionResult:
        self.invocations.append(prompt)
        return self._response

    async def ainvoke(self, prompt: str) -> ExtractionResult:
        self.invocations.append(prompt)
        return self._response


class _LLMStub:
    def __init__(self, response: ExtractionResult):
        self._structured = _StructuredLLMStub(response)

    def with_structured_output(self, _schema):
        return self._structured


@pytest.mark.asyncio
async def test_llm_processor_generates_uuid7_and_process_data(monkeypatch):
    extraction = ExtractionResult(
        report_id="ignored",
        metrics=[ExtractedMetric(name="metric", current="10", previous="9")],
    )
    llm_stub = _LLMStub(extraction)
    fake_uuid = uuid7()
    monkeypatch.setattr(
        "infra.llm_based_processor.uuid7",
        lambda: fake_uuid,
    )

    processor = ReportDataProcessor(
        llm=llm_stub,
        metrics_config={"metric": {}},
    )
    result = await processor.process(
        ReportFileData(content="body", metadata={"id": "meta"})
    )

    assert result.report_id == fake_uuid
    assert result.data["metric"].current == "10"
    assert result.data["metric"].previous == "9"

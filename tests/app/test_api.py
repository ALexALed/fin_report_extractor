import io
from uuid import UUID, uuid7

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from core.fin_report_file_loaders.models import ReportFileData
from core.fin_report_processors.models import MetricValues, ProcessedData


class StubFileReader:
    def __init__(self) -> None:
        self.read_calls: list[str] = []
        self.structured_calls: list[str] = []

    async def read(self, file_path: str) -> ReportFileData:
        self.read_calls.append(file_path)
        return ReportFileData(content="content", metadata={"source": "test"})

    async def structured_output(self, file_path: str) -> list[dict[str, str]]:
        self.structured_calls.append(file_path)
        return [{"account": "Revenue", "amount": "1000"}]


class StubReportDataBuilder:
    def __init__(self) -> None:
        self.calls: list[ReportFileData] = []

    async def process(self, report_file_data: ReportFileData) -> ProcessedData:
        self.calls.append(report_file_data)
        return ProcessedData(
            report_id=uuid7(),
            data={"metric": MetricValues(current="10", previous="5")},
        )


class InMemoryReportRepository:
    def __init__(self) -> None:
        self.storage: dict[UUID, ProcessedData] = {}

    async def save(self, processed: ProcessedData) -> None:
        self.storage[processed.report_id] = processed

    async def get(self, report_id: UUID) -> ProcessedData | None:
        return self.storage.get(report_id)


@pytest.fixture
def api_client(app_container):
    api_key = "test-key"
    file_reader = StubFileReader()
    builder = StubReportDataBuilder()
    repository = InMemoryReportRepository()

    with app_container.report_file_reader.override(
        file_reader
    ), app_container.report_data_builder.override(
        builder
    ), app_container.processed_report_repository.override(repository):
        app_container.config.api_keys.service.from_value(api_key)
        app = create_app(container=app_container)

        with TestClient(app) as client:
            yield client, repository, builder, file_reader, api_key


def test_upload_report_triggers_processing(api_client):
    client, repository, builder, file_reader, api_key = api_client
    file_content = b"binary-xlsx-data"
    response = client.post(
        "/reports",
        files={
            "file": (
                "report.xlsx",
                io.BytesIO(file_content),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 202
    payload = response.json()
    report_id = UUID(payload["report_id"])

    assert payload["structured_output"] == [{"account": "Revenue", "amount": "1000"}]
    assert builder.calls, "Background processing did not run"
    assert file_reader.read_calls and file_reader.structured_calls
    assert report_id in repository.storage


def test_get_processed_report_returns_data(api_client):
    client, _, _, _, api_key = api_client
    upload_response = client.post(
        "/reports",
        files={
            "file": (
                "report.xlsx",
                io.BytesIO(b"binary-xlsx-data"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers={"X-API-Key": api_key},
    )
    report_id = upload_response.json()["report_id"]

    response = client.get(f"/reports/{report_id}", headers={"X-API-Key": api_key})

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_id"] == report_id
    assert payload["data"]["metric"]["current"] == "10"


def test_get_processed_report_returns_error_when_processing_failed(api_client):
    client, _, _, _, api_key = api_client
    repository = client.app.state.container.processed_report_repository()
    failed_report_id = uuid7()

    repository.storage[failed_report_id] = ProcessedData(
        report_id=failed_report_id,
        data={},
        error="LLM timeout",
    )

    response = client.get(
        f"/reports/{failed_report_id}",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 500
    assert (
        response.json()["detail"] == "Report processing failed. Please try again later."
    )


def test_get_processed_report_returns_404_when_missing(api_client):
    client, _, _, _, api_key = api_client
    missing_id = uuid7()

    response = client.get(f"/reports/{missing_id}", headers={"X-API-Key": api_key})

    assert response.status_code == 404


def test_upload_rejects_files_without_required_extension(api_client):
    client, _, _, _, api_key = api_client

    response = client.post(
        "/reports",
        files={
            "file": (
                "report.txt",
                io.BytesIO(b"text"),
                "text/plain",
            )
        },
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 422


def test_upload_rejects_large_files(api_client):
    client, _, _, _, api_key = api_client

    response = client.post(
        "/reports",
        files={
            "file": (
                "report.xlsx",
                io.BytesIO(b"a" * (2 * 1024 * 1024 + 1)),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 422


def test_health_endpoint_returns_ok(app_container):
    app = create_app(container=app_container)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.text == "OK"

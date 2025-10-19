import logging
import os
import shutil
from tempfile import NamedTemporaryFile
from typing import Any
from uuid import UUID, uuid7

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.params import Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict

from app.container import AppContainer
from core.fin_report_file_loaders.models import ReportFileData
from core.fin_report_processors.models import MetricValues, ProcessedData

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE_BYTES = 2 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
}

api_key_header = APIKeyHeader(name="X-API-Key")


class UploadReportResponse(BaseModel):
    report_id: UUID
    structured_output: list[dict[str, Any]]


class ProcessedReportResponse(BaseModel):
    report_id: UUID
    processed_at: str
    data: dict[str, MetricValues]

    model_config = ConfigDict(from_attributes=True)


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


def create_reports_router(container: AppContainer, api_key: str | None) -> APIRouter:
    async def enforce_api_key(api_key_header: str = Security(api_key_header)) -> None:
        if api_key_header != api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

    router = APIRouter(
        prefix="/reports", tags=["reports"], dependencies=[Depends(enforce_api_key)]
    )

    router.add_api_route(
        "",
        upload_report,
        methods=["POST"],
        status_code=status.HTTP_202_ACCEPTED,
        response_model=UploadReportResponse,
    )
    router.add_api_route(
        "/{report_id}",
        get_processed_report,
        methods=["GET"],
        response_model=ProcessedReportResponse,
        responses={404: {"description": "Report not found"}},
    )

    return router


async def upload_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    container: AppContainer = Depends(get_container),
) -> UploadReportResponse:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File must have .xlsx extension",
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported file content type",
        )

    temp_path = await _persist_upload(file)
    file_reader = container.report_file_reader()
    report_data_builder = container.report_data_builder()
    processed_report_repository = container.processed_report_repository()

    try:
        # This is a tricky part. The 'structured_output' is needed for the user,
        # but it's not the best input for the LLM.
        # I believe it's better to avoid creating the 'structured_output' in the first place
        # and just return the report ID instead.
        structured_output = await file_reader.structured_output(temp_path)
        report_file_data = await file_reader.read(temp_path)
        # This common exception is used to investigate the types of errors that can occur.
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to read uploaded report: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unable to parse the uploaded Excel file",
        ) from exc

    report_id = uuid7()

    async def process_in_background(data: ReportFileData, generated_id: UUID) -> None:
        """
        Task to process the report in the background and clean up the temp file.
        """
        # Ensure the temporary file is cleaned up after processing
        temp_file_path = data.metadata.get("source")

        processed = await report_data_builder.process(data)

        if isinstance(processed, Exception):
            logger.error(
                "Report %s failed during processing: %s",
                generated_id,
                processed,
            )
            processed_with_id = ProcessedData(
                report_id=generated_id,
                data={},
                error=str(processed),
            )
        else:
            processed_with_id = processed.model_copy(update={"report_id": generated_id})

        await processed_report_repository.save(processed_with_id)

        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError as e:
                logger.error("Failed to remove temp file %s: %s", temp_file_path, e)

    background_tasks.add_task(process_in_background, report_file_data, report_id)

    return UploadReportResponse(
        report_id=report_id,
        structured_output=structured_output,
    )


async def get_processed_report(
    report_id: UUID, container: AppContainer = Depends(get_container)
) -> ProcessedReportResponse:
    processed_report_repository = container.processed_report_repository()
    processed = await processed_report_repository.get(report_id)
    if processed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if processed.error:
        logger.error(
            "Processed report %s is unavailable due to an internal error: %s",
            report_id,
            processed.error,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report processing failed. Please try again later.",
        )

    payload = ProcessedReportResponse.model_validate(
        processed.model_dump(mode="json", exclude={"error"})
    )
    return payload


async def _persist_upload(upload: UploadFile) -> str:
    if upload.size is not None:
        size = upload.size
    else:
        contents = await upload.read()
        size = len(contents)
        await upload.seek(0)

    if size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File exceeded 2MB limit",
        )

    if size == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Uploaded file is empty",
        )

    temp_file = NamedTemporaryFile(delete=False, suffix=".xlsx")
    try:
        shutil.copyfileobj(upload.file, temp_file)
    except Exception:  # noqa: BLE001
        temp_file.close()
        os.remove(temp_file.name)
        raise

    temp_file.close()
    return temp_file.name

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from app.api.reports import create_reports_router
from app.container import AppContainer


def create_app(container: AppContainer | None = None) -> FastAPI:
    if container is None:
        container = AppContainer()

        container.config.api_keys.openai.from_env("OPENAI_API_KEY")
        container.config.database.url.from_env(
            "DATABASE_URL",
            default="sqlite+aiosqlite:///./fin_reports.db",
        )
        container.config.api_keys.service.from_env(
            "FIN_REPORT_EXTRACTOR_API_KEY",
            default=None,
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await container.init_resources()
        try:
            yield
        finally:
            container.shutdown_resources()

    app = FastAPI(title="Financial Report Extractor", lifespan=lifespan)
    app.state.container = container

    api_key = container.config.api_keys.service()
    reports_router = create_reports_router(container, api_key)
    app.include_router(reports_router)

    @app.get("/health", include_in_schema=False)
    async def healthcheck() -> PlainTextResponse:
        return PlainTextResponse("OK")

    return app


app = create_app()

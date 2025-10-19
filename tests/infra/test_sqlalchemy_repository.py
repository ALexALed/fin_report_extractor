from uuid import uuid7

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.fin_report_processors.db_models import Base
from core.fin_report_processors.models import MetricValues, ProcessedData
from infra.sqlalchemy_repository import SqlAlchemyProcessedReportRepository


@pytest.mark.asyncio
async def test_repository_persists_and_retrieves_processed_report():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repository = SqlAlchemyProcessedReportRepository(session_factory)

    processed = ProcessedData(
        report_id=uuid7(),
        data={"metric": MetricValues(current="1", previous="0")},
    )

    await repository.save(processed)
    fetched = await repository.get(processed.report_id)

    await engine.dispose()

    assert fetched.report_id == processed.report_id
    assert fetched.data == processed.data
    assert fetched.error is None


@pytest.mark.asyncio
async def test_repository_persists_error_state():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repository = SqlAlchemyProcessedReportRepository(session_factory)

    processed = ProcessedData(
        report_id=uuid7(),
        data={},
        error="LLM failure",
    )

    await repository.save(processed)
    fetched = await repository.get(processed.report_id)

    await engine.dispose()

    assert fetched.error == "LLM failure"
    assert fetched.data == {}


@pytest.mark.asyncio
async def test_repository_returns_none_when_missing():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repository = SqlAlchemyProcessedReportRepository(session_factory)

    fetched = await repository.get(uuid7())

    await engine.dispose()

    assert fetched is None

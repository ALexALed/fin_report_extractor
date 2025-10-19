from dependency_injector import containers, providers
from langchain.chat_models import init_chat_model
from langchain_core.language_models.base import BaseLanguageModel
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from core.fin_report_processors.services import ReportDataBuilder
from infra.database import init_database
from infra.llm_based_processor import ReportDataProcessor as LLMReportDataProcessor
from infra.sqlalchemy_repository import SqlAlchemyProcessedReportRepository
from infra.xlsx_reader import XlsxFileReader


class AppContainer(containers.DeclarativeContainer):
    """Dependency injection container wiring infrastructure and core services."""

    config = providers.Configuration()

    llm: providers.Provider[BaseLanguageModel] = providers.Singleton(
        init_chat_model,
        "gpt-4o-mini",
        model_provider="openai",
        api_key=config.api_keys.openai,
    )

    report_file_reader = providers.Singleton(XlsxFileReader)

    report_data_processor_factory = providers.Factory(
        LLMReportDataProcessor,
        llm=llm,
        prompt_template=config.llm.prompt_template.optional(None),
    )

    report_data_builder = providers.Factory(
        ReportDataBuilder,
        metrics_config=config.processor.metrics.optional(None),
        processor_factory=report_data_processor_factory.provider,
    )

    report_data_processor = providers.DelegatedFactory(
        report_data_builder.provided.build_processor,
    )

    db_engine: providers.Provider[AsyncEngine] = providers.Singleton(
        create_async_engine,
        config.database.url,
        echo=config.database.echo.optional(False),
    )

    session_factory = providers.Singleton(
        async_sessionmaker,
        db_engine,
        expire_on_commit=False,
    )

    processed_report_repository = providers.Factory(
        SqlAlchemyProcessedReportRepository,
        session_factory=session_factory,
    )

    db_initializer = providers.Resource(
        init_database,
        engine=db_engine,
    )

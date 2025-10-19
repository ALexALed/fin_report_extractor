import asyncio
import os

import pytest

from app.container import AppContainer


@pytest.fixture(scope="session", autouse=True)
def app_container() -> AppContainer:
    container = AppContainer()
    db_path = "./test_fin_reports.db"
    container.config.api_keys.openai.from_value("test-api-key")
    container.config.llm.prompt_template.from_value("Prompt {metadata_json}")
    container.config.database.url.from_value(f"sqlite+aiosqlite:///{db_path}")

    async def setup_resources():
        await container.init_resources()

    asyncio.run(setup_resources())

    yield container

    # Teardown
    container.unwire()
    asyncio.run(container.shutdown_resources())
    if os.path.exists(db_path):
        os.remove(db_path)

from sqlalchemy.ext.asyncio import AsyncEngine

from core.fin_report_processors.db_models import Base


async def init_database(engine: AsyncEngine) -> None:
    """Ensure all database tables exist before the application starts."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

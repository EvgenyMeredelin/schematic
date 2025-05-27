# standard library
from collections.abc import AsyncGenerator

# 3rd party libraries
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)

# user modules
from models import Base


url = f"sqlite+aiosqlite:///schematic.db"
engine = create_async_engine(url)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Open a fresh session when the request starts and close it when the
    response is sent.
    """
    async with async_session_maker() as session:
        yield session


async def create_all_tables():
    """Create the table schema inside the database. """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

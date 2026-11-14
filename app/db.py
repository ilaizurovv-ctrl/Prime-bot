from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
Session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def init_db():
    from app.models import User, Deal, BalanceTransaction  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

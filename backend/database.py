from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from models import Base, Settings
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trading_system.db")

# Convert sqlite URL for async
if DATABASE_URL.startswith("sqlite"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Create async engine
engine = create_async_engine(ASYNC_DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Initialize database
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create default settings if not exists
    async with async_session_maker() as session:
        settings = await session.get(Settings, 1)
        if not settings:
            default_settings = Settings(
                id=1,
                auto_trading_enabled=True,
                max_position_size=1000.0,
                risk_percentage=1.0
            )
            session.add(default_settings)
            await session.commit()

# Dependency to get database session
async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
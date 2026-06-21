
#/ =====================================================================================
#/  Database layer
#/  PostgreSQL connection setup (via SQLModel/SQLAlchemy async) and MongoDB
#/  PostgreSQL — main data, MongoDB — user action logging
#/ =====================================================================================

#/ ─── Imports / Импорты ───
import config
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from pymongo import MongoClient
from typing import AsyncGenerator

#* ─── PostgreSQL (SQLModel async engine) ───
engine = create_async_engine(
    config.DATABASE_URL,
    echo=config.DEBUG,
    future=True,
    pool_size=10,
    max_overflow=20,
)

#* ─── Session factory / Фабрика сессий ───
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

#? Generator function to get DB session in FastAPI endpoints via Depends
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


#* ─── MongoDB (for logs) ───
#! MongoDB is used ONLY for logging, not for storing main data
mongo_client: MongoClient | None = None

def get_mongo():
    """Return MongoDB client. Creates on first call."""
    global mongo_client
    if mongo_client is None:
        try:
            mongo_client = MongoClient(config.MONGO_URL, serverSelectionTimeoutMS=3000)
            #* Check connection
            mongo_client.admin.command('ping')
        except Exception as e:
            #! If MongoDB is unavailable — log a warning but don't crash
            print(f"[!] MongoDB connection failed, logging disabled: {e}")
            return None
    return mongo_client

#* ─── init_db — create tables at startup / Создание таблиц при запуске ───
async def init_db():
    """Create all tables on startup (if they don't exist yet)."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

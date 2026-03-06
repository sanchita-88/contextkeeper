from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, Integer
from datetime import datetime
from config import settings
import json

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class SnapshotDB(Base):
    __tablename__ = "context_snapshots"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    project_path: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    data_json: Mapped[str] = mapped_column(Text, nullable=False)

class IndexedProjectDB(Base):
    __tablename__ = "indexed_projects"
    project_path: Mapped[str] = mapped_column(String, primary_key=True)
    last_indexed: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

class InterruptionLogDB(Base):
    __tablename__ = "interruption_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    message: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String)
    priority: Mapped[str] = mapped_column(String)
    auto_reply: Mapped[str] = mapped_column(Text)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

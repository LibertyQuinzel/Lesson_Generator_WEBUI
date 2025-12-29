"""
Database connection and session management.

This module provides SQLAlchemy engine configuration, session management,
and database initialization for the Lesson Generator.
"""

import os
from typing import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base


# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lesson_generator.db")
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL", "sqlite+aiosqlite:///./lesson_generator.db")

# For SQLite, we need special configuration to handle threading
SQLITE_CONFIG = {
    "poolclass": StaticPool,
    "connect_args": {
        "check_same_thread": False,  # Allow SQLite to be used across threads
    },
}

# Create engines
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, **SQLITE_CONFIG)
    async_engine = create_async_engine(ASYNC_DATABASE_URL, **SQLITE_CONFIG)
else:
    # For PostgreSQL and other databases
    engine = create_engine(DATABASE_URL)
    async_engine = create_async_engine(ASYNC_DATABASE_URL)

# Create session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


def init_database():
    """
    Initialize the database by creating all tables.
    
    This function creates all tables defined in the models module.
    It's safe to call multiple times as it only creates missing tables.
    """
    print("🔧 Initializing database...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        raise


async def async_init_database():
    """
    Async version of database initialization.
    
    This is used when running in async context (FastAPI startup).
    """
    print("🔧 Initializing database (async)...")
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database initialized successfully (async)")
    except Exception as e:
        print(f"❌ Failed to initialize database (async): {e}")
        raise


def get_database():
    """
    Dependency function for FastAPI to provide database sessions.
    
    This function provides a database session that automatically
    closes when the request is complete.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_database() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency function for FastAPI to provide async database sessions.
    
    This function provides an async database session that automatically
    closes when the request is complete.
    
    Yields:
        AsyncSession: SQLAlchemy async database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()


def reset_database():
    """
    Reset the database by dropping and recreating all tables.
    
    WARNING: This will delete all data! Only use for development/testing.
    """
    print("⚠️ Resetting database (ALL DATA WILL BE LOST)...")
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("✅ Database reset successfully")
    except Exception as e:
        print(f"❌ Failed to reset database: {e}")
        raise


async def async_reset_database():
    """
    Async version of database reset.
    
    WARNING: This will delete all data! Only use for development/testing.
    """
    print("⚠️ Resetting database (async) (ALL DATA WILL BE LOST)...")
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database reset successfully (async)")
    except Exception as e:
        print(f"❌ Failed to reset database (async): {e}")
        raise


# Database health check
def check_database_health() -> bool:
    """
    Check if the database is accessible and functioning.
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        db = SessionLocal()
        # Simple query to test connection
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database health check failed: {e}")
        return False


async def async_check_database_health() -> bool:
    """
    Async version of database health check.
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            # Simple query to test connection
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ Async database health check failed: {e}")
        return False
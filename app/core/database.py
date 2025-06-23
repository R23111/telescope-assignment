"""
Provides configuration and utilities for managing asynchronous interactions
with a PostgreSQL database using SQLAlchemy and async sessions.

This module sets up the asynchronous database engine using environment
variables, initializes the session factory, and exposes a dependency-compatible
session generator for use in FastAPI endpoints.
"""


import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """Yields a SQLAlchemy asynchronous database session for use in request
    handlers.

    This function manages the lifecycle of the database session, ensuring it
    is closed after use.

    Yields:
        AsyncSession: An asynchronous SQLAlchemy session object.
    """
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()

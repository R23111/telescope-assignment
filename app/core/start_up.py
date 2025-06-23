"""
This module initializes the database models and creates all tables.
"""

from app.core.database import engine
from app.models.company import Base


async def init_models():
    """Initializes the database models and creates all tables.

    This function establishes a connection to the database and creates all
    tables defined in the models.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

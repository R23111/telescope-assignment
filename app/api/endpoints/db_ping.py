from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()


@router.get("/db_ping", tags=["Health"])
async def db_ping(db: AsyncSession = Depends(get_db)):
    """Checks the health of the database connection by executing a simple
    query.

    This endpoint returns whether the database is alive and reachable.

    Args:
        db (AsyncSession): The asynchronous database session dependency.

    Returns:
        dict: A dictionary indicating if the database is alive.
    """
    result = await db.execute(text("SELECT 1;"))
    return {"db_alive": result.scalar() == 1}

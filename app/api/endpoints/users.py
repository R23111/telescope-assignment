"""
This module defines the API endpoints related to user management.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserOut

router = APIRouter()


@router.post(
    "/create_user", response_model=UserOut, status_code=status.HTTP_201_CREATED
)
async def create_user(
    user_data: UserCreate, db: AsyncSession = Depends(get_db)
):
    """
    Creates a new user if the username is not already taken.

    Args:
        user_data (UserCreate): Incoming data containing the user_name.
        db (AsyncSession): Async database session.

    Returns:
        UserOut: The newly created user or the existing one.
    """
    result = await db.execute(
        select(User).where(User.user_name == user_data.user_name)
    )
    if user := result.scalars().first():
        return user

    new_user = User(user_name=user_data.user_name)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

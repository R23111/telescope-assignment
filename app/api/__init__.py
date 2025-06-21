from fastapi import APIRouter

from .endpoints import db_ping

router = APIRouter()

router.include_router(db_ping.router)

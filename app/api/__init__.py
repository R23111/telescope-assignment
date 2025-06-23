"""
API module for the application.
"""

from fastapi import APIRouter

from .endpoints import companies, rules, users

router = APIRouter()

router.include_router(companies.router, tags=["import_data"])
router.include_router(users.router, tags=["users"])
router.include_router(rules.router, tags=["rules"])

"""This script waits for the database to be ready before proceeding."""

import asyncio
import logging
import os

import asyncpg

logger = logging.getLogger(__name__)

DB_URL = os.environ.get("DATABASE_URL", "")
MAX_RETRIES = 10
WAIT_SECONDS = 2

# Strip asyncpg for raw asyncpg compatibility
RAW_DB_URL = DB_URL.replace("postgresql+asyncpg", "postgresql")


async def wait_for_db():
    for i in range(MAX_RETRIES):
        try:
            conn = await asyncpg.connect(RAW_DB_URL)
            await conn.execute("SELECT 1;")
            await conn.close()
            logger.info("✅ Database is up and responding!")
            return
        except Exception as e:
            logger.warning(f"⏳ Attempt {i+1}/{MAX_RETRIES} failed: {e}")
            await asyncio.sleep(WAIT_SECONDS)
    raise Exception("Could not connect to the database after several retries.")


if __name__ == "__main__":
    asyncio.run(wait_for_db())

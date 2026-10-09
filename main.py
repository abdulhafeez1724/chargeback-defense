import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from domain.accounts import hash_api_key
from infrastructure.in_memory_accounts import InMemoryAccountRepository
from infrastructure.in_memory_repository import InMemoryDisputeRepository
from presentation.api.account import router as account_router
from presentation.api.body_limit import BodySizeLimitMiddleware
from presentation.api.disputes import router as disputes_router
from presentation.web.routes import router as web_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def _dev_accounts() -> InMemoryAccountRepository:
    """Sirf local dev: DEV_API_KEYS="key:tenant,..." — production me keys DB se (scripts/admin.py)."""
    accounts = InMemoryAccountRepository()
    credits = int(os.environ.get("DEV_CREDITS", "100"))
    for pair in filter(None, (p.strip() for p in os.environ.get("DEV_API_KEYS", "").split(","))):
        key, sep, tenant = pair.partition(":")
        if not sep or not key or not tenant:
            raise RuntimeError("DEV_API_KEYS entries must be 'key:tenant'")
        await accounts.create(tenant, hash_api_key(key), credits)
    return accounts


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.warning("DATABASE_URL not set — using in-memory storage (lost on restart)")
        app.state.repo = InMemoryDisputeRepository()
        app.state.accounts = await _dev_accounts()
        yield
        return

    # asyncpg sirf tab import ho jab Postgres use ho
    from infrastructure.postgres_accounts import PostgresAccountRepository
    from infrastructure.postgres_repository import PostgresDisputeRepository, create_pool

    pool = await create_pool(database_url)
    app.state.repo = PostgresDisputeRepository(pool)
    app.state.accounts = PostgresAccountRepository(pool)
    try:
        yield
    finally:
        await pool.close()


app = FastAPI(title="Chargeback Defense Pack", lifespan=lifespan)
app.add_middleware(BodySizeLimitMiddleware)
app.include_router(disputes_router)
app.include_router(account_router)
app.include_router(web_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from infrastructure.in_memory_repository import InMemoryDisputeRepository
from presentation.api.body_limit import BodySizeLimitMiddleware
from presentation.api.disputes import router as disputes_router
from presentation.web.routes import router as web_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.warning("DATABASE_URL not set — using in-memory storage (lost on restart)")
        app.state.repo = InMemoryDisputeRepository()
        yield
        return

    # asyncpg sirf tab import ho jab Postgres use ho
    from infrastructure.postgres_repository import PostgresDisputeRepository, create_pool

    pool = await create_pool(database_url)
    app.state.repo = PostgresDisputeRepository(pool)
    try:
        yield
    finally:
        await pool.close()


app = FastAPI(title="Chargeback Defense Pack", lifespan=lifespan)
app.add_middleware(BodySizeLimitMiddleware)
app.include_router(disputes_router)
app.include_router(web_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

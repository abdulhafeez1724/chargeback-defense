"""Real Postgres ke against. Chalane ke liye: TEST_DATABASE_URL=postgresql://... pytest"""

import asyncio
import os
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from domain.entities import Attachment, Dispute, DisputeReason, EvidenceItem, EvidenceType, Order

DSN = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DSN, reason="TEST_DATABASE_URL not set")


def _dispute(tenant_id: str, evidence: list[EvidenceItem]) -> Dispute:
    order = Order(
        order_id="1001",
        amount=Decimal("49.99"),
        currency="usd",
        placed_at=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
        customer_email="jane@example.com",
        billing_address="12 Oak Ave",
        shipping_address="12 Oak Ave",
        customer_ip="73.14.22.9",
    )
    return Dispute("dp_pg", tenant_id, order, DisputeReason.PRODUCT_NOT_RECEIVED, evidence)


async def _scenario() -> None:
    from infrastructure.postgres_repository import PostgresDisputeRepository, create_pool

    assert DSN
    pool = await create_pool(DSN)
    try:
        await pool.execute("TRUNCATE disputes CASCADE")
        repo = PostgresDisputeRepository(pool)
        photo = Attachment("porch.png", "image/png", b"\x89PNG fake bytes")
        original = _dispute("t1", [
            EvidenceItem(EvidenceType.TRACKING, "USPS 9400"),
            EvidenceItem(EvidenceType.DELIVERY_PROOF, "Porch photo", attachment=photo),
        ])
        await repo.save(original)

        # Round-trip: jo save kiya wohi wapas aaye (order, evidence order, bytes)
        assert await repo.get("t1", "dp_pg") == original
        # Tenant isolation
        assert await repo.get("t2", "dp_pg") is None

        # Upsert: evidence replace ho, duplicate na ho
        updated = _dispute("t1", [EvidenceItem(EvidenceType.TRACKING, "UPS 1Z")])
        await repo.save(updated)
        assert await repo.get("t1", "dp_pg") == updated
    finally:
        await pool.close()


def test_postgres_round_trip_upsert_and_isolation() -> None:
    asyncio.run(_scenario())

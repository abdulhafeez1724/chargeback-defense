import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from application.build_evidence_pack import BuildEvidencePackUseCase, DisputeNotFound
from domain.entities import Dispute, DisputeReason, EvidenceItem, EvidenceType, Order
from domain.evidence_policy import EvidenceGap
from infrastructure.in_memory_repository import InMemoryDisputeRepository


class FakeRenderer:
    def __init__(self) -> None:
        self.calls: list[tuple[Dispute, EvidenceGap]] = []

    async def render(self, dispute: Dispute, gap: EvidenceGap) -> bytes:
        self.calls.append((dispute, gap))
        return b"%PDF-fake"


def _dispute(tenant_id: str = "t1") -> Dispute:
    order = Order(
        order_id="o1",
        amount=Decimal("49.99"),
        currency="usd",
        placed_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        customer_email="buyer@example.com",
        billing_address="1 Main St",
        shipping_address="1 Main St",
    )
    d = Dispute("dp_1", tenant_id, order, DisputeReason.PRODUCT_NOT_RECEIVED)
    d.add_evidence(EvidenceItem(EvidenceType.TRACKING, "USPS 9400..."))
    return d


def test_builds_pack_with_gap() -> None:
    repo = InMemoryDisputeRepository()
    renderer = FakeRenderer()
    asyncio.run(repo.save(_dispute()))

    pack = asyncio.run(BuildEvidencePackUseCase(repo, renderer).execute("t1", "dp_1"))

    assert pack.document == b"%PDF-fake"
    assert pack.gap.missing == frozenset({EvidenceType.DELIVERY_PROOF})
    assert pack.gap.strength == 0.5
    assert len(renderer.calls) == 1


def test_other_tenant_cannot_access() -> None:
    repo = InMemoryDisputeRepository()
    asyncio.run(repo.save(_dispute(tenant_id="t1")))

    with pytest.raises(DisputeNotFound):
        asyncio.run(BuildEvidencePackUseCase(repo, FakeRenderer()).execute("t2", "dp_1"))

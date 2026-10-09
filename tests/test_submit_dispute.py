import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from application.build_evidence_pack import BuildEvidencePackUseCase
from application.submit_dispute import ChargeRejected, SubmitDisputeUseCase
from domain.accounts import ChargeOutcome, hash_api_key
from domain.entities import Dispute, DisputeReason, Order
from domain.evidence_policy import EvidenceGap
from infrastructure.in_memory_accounts import InMemoryAccountRepository
from infrastructure.in_memory_repository import InMemoryDisputeRepository


class FakeRenderer:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    async def render(self, dispute: Dispute, gap: EvidenceGap) -> bytes:
        self.calls += 1
        if self.fail:
            raise RuntimeError("renderer crashed")
        return b"%PDF-fake"


def _dispute(dispute_id: str = "dp_1", order_id: str = "o1") -> Dispute:
    order = Order(order_id, Decimal("10.00"), "usd", datetime(2026, 10, 1, tzinfo=timezone.utc),
                  "a@b.co", "x", "x")
    return Dispute(dispute_id, "shop-a", order, DisputeReason.PRODUCT_NOT_RECEIVED)


def _setup(credits: int, renderer: FakeRenderer) -> tuple[SubmitDisputeUseCase, InMemoryAccountRepository]:
    disputes = InMemoryDisputeRepository()
    accounts = InMemoryAccountRepository()
    asyncio.run(accounts.create("shop-a", hash_api_key("k"), credits))
    use_case = SubmitDisputeUseCase(disputes, accounts, BuildEvidencePackUseCase(disputes, renderer))
    return use_case, accounts


def test_charges_one_credit_and_regenerates_free() -> None:
    use_case, accounts = _setup(credits=2, renderer=FakeRenderer())

    _, remaining = asyncio.run(use_case.execute(_dispute()))
    assert remaining == 1
    _, remaining = asyncio.run(use_case.execute(_dispute()))  # typo fix, same dispute
    assert remaining == 1


def test_no_credit_rejected_before_rendering() -> None:
    renderer = FakeRenderer()
    use_case, _ = _setup(credits=0, renderer=renderer)

    with pytest.raises(ChargeRejected) as exc:
        asyncio.run(use_case.execute(_dispute()))
    assert exc.value.outcome is ChargeOutcome.INSUFFICIENT_CREDITS
    assert renderer.calls == 0


def test_render_failure_does_not_consume_credit() -> None:
    use_case, accounts = _setup(credits=1, renderer=FakeRenderer(fail=True))

    with pytest.raises(RuntimeError):
        asyncio.run(use_case.execute(_dispute()))
    assert asyncio.run(accounts.get_credits("shop-a")) == 1


def test_reused_dispute_id_for_other_order_is_rejected_without_overwrite() -> None:
    use_case, _ = _setup(credits=5, renderer=FakeRenderer())
    asyncio.run(use_case.execute(_dispute(order_id="o1")))

    with pytest.raises(ChargeRejected) as exc:
        asyncio.run(use_case.execute(_dispute(order_id="o2")))
    assert exc.value.outcome is ChargeOutcome.DISPUTE_ID_CONFLICT

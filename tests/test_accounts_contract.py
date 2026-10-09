"""Har AccountRepository implementation ka bartao ek jaisa hona chahiye (contract tests).

Postgres variant sirf TEST_DATABASE_URL set ho to chalta hai.
"""

import asyncio
import os
from collections.abc import Awaitable, Callable

import pytest

from application.ports import AccountRepository
from domain.accounts import ChargeOutcome, hash_api_key
from infrastructure.in_memory_accounts import InMemoryAccountRepository

DSN = os.environ.get("TEST_DATABASE_URL")

Scenario = Callable[[AccountRepository], Awaitable[None]]


async def _with_postgres(scenario: Scenario) -> None:
    from infrastructure.postgres_accounts import PostgresAccountRepository
    from infrastructure.postgres_repository import create_pool

    assert DSN
    pool = await create_pool(DSN)
    try:
        await pool.execute("TRUNCATE charged_disputes, accounts CASCADE")
        await scenario(PostgresAccountRepository(pool))
    finally:
        await pool.close()


async def _with_memory(scenario: Scenario) -> None:
    await scenario(InMemoryAccountRepository())


@pytest.fixture(
    params=[
        pytest.param(_with_memory, id="memory"),
        pytest.param(
            _with_postgres, id="postgres",
            marks=pytest.mark.skipif(not DSN, reason="TEST_DATABASE_URL not set"),
        ),
    ]
)
def run(request: pytest.FixtureRequest) -> Callable[[Scenario], None]:
    runner: Callable[[Scenario], Awaitable[None]] = request.param
    return lambda scenario: asyncio.run(runner(scenario))


def test_lookup_by_key_hash(run: Callable[[Scenario], None]) -> None:
    async def scenario(repo: AccountRepository) -> None:
        await repo.create("shop-a", hash_api_key("k1"), 3)
        account = await repo.get_by_key_hash(hash_api_key("k1"))
        assert account is not None and account.tenant_id == "shop-a" and account.credits == 3
        assert await repo.get_by_key_hash(hash_api_key("wrong")) is None

    run(scenario)


def test_charges_once_per_dispute(run: Callable[[Scenario], None]) -> None:
    async def scenario(repo: AccountRepository) -> None:
        await repo.create("shop-a", hash_api_key("k1"), 2)
        assert await repo.charge("shop-a", "dp_1", "o1") is ChargeOutcome.CHARGED
        # Same dispute + order dobara: free
        assert await repo.charge("shop-a", "dp_1", "o1") is ChargeOutcome.ALREADY_CHARGED
        assert await repo.get_credits("shop-a") == 1
        # Same dispute_id, alag order: conflict, credit nahi katta
        assert await repo.charge("shop-a", "dp_1", "o2") is ChargeOutcome.DISPUTE_ID_CONFLICT
        assert await repo.get_credits("shop-a") == 1

    run(scenario)


def test_insufficient_credits_changes_nothing(run: Callable[[Scenario], None]) -> None:
    async def scenario(repo: AccountRepository) -> None:
        await repo.create("shop-a", hash_api_key("k1"), 1)
        assert await repo.charge("shop-a", "dp_1", "o1") is ChargeOutcome.CHARGED
        assert await repo.check_charge("shop-a", "dp_2", "o2") is ChargeOutcome.INSUFFICIENT_CREDITS
        assert await repo.charge("shop-a", "dp_2", "o2") is ChargeOutcome.INSUFFICIENT_CREDITS
        # Rollback hua: dp_2 charged mark nahi hua, credits top-up ke baad charge ho sakta hai
        await repo.add_credits("shop-a", 1)
        assert await repo.charge("shop-a", "dp_2", "o2") is ChargeOutcome.CHARGED
        assert await repo.get_credits("shop-a") == 0

    run(scenario)


def test_check_charge_is_read_only(run: Callable[[Scenario], None]) -> None:
    async def scenario(repo: AccountRepository) -> None:
        await repo.create("shop-a", hash_api_key("k1"), 1)
        assert await repo.check_charge("shop-a", "dp_1", "o1") is ChargeOutcome.CHARGED
        assert await repo.get_credits("shop-a") == 1

    run(scenario)


def test_tenants_are_isolated(run: Callable[[Scenario], None]) -> None:
    async def scenario(repo: AccountRepository) -> None:
        await repo.create("shop-a", hash_api_key("k1"), 1)
        await repo.create("shop-b", hash_api_key("k2"), 1)
        assert await repo.charge("shop-a", "dp_1", "o1") is ChargeOutcome.CHARGED
        # Doosra tenant same dispute_id use kare to apna alag charge
        assert await repo.charge("shop-b", "dp_1", "o9") is ChargeOutcome.CHARGED
        assert await repo.get_credits("shop-a") == 0
        assert await repo.get_credits("shop-b") == 0

    run(scenario)


def test_deactivate(run: Callable[[Scenario], None]) -> None:
    async def scenario(repo: AccountRepository) -> None:
        await repo.create("shop-a", hash_api_key("k1"), 1)
        await repo.set_active("shop-a", False)
        account = await repo.get_by_key_hash(hash_api_key("k1"))
        assert account is not None and not account.active

    run(scenario)


@pytest.mark.skipif(not DSN, reason="TEST_DATABASE_URL not set")
def test_postgres_concurrent_charges_never_overspend() -> None:
    async def scenario(repo: AccountRepository) -> None:
        await repo.create("shop-a", hash_api_key("k1"), 1)
        # 1 credit, 10 alag disputes ek saath — sirf ek charge hona chahiye
        outcomes = await asyncio.gather(
            *(repo.charge("shop-a", f"dp_{i}", f"o{i}") for i in range(10))
        )
        assert outcomes.count(ChargeOutcome.CHARGED) == 1
        assert outcomes.count(ChargeOutcome.INSUFFICIENT_CREDITS) == 9
        assert await repo.get_credits("shop-a") == 0

        # Same dispute 10 dafa ek saath (double-click) — ek charge, baaki already
        await repo.add_credits("shop-a", 5)
        outcomes = await asyncio.gather(*(repo.charge("shop-a", "dp_x", "ox") for _ in range(10)))
        assert outcomes.count(ChargeOutcome.CHARGED) == 1
        assert outcomes.count(ChargeOutcome.ALREADY_CHARGED) == 9
        assert await repo.get_credits("shop-a") == 4

    asyncio.run(_with_postgres(scenario))

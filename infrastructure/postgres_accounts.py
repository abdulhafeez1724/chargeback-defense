import asyncpg

from domain.accounts import Account, ChargeOutcome

ACCOUNTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    tenant_id  text        PRIMARY KEY,
    key_hash   text        NOT NULL UNIQUE,
    credits    integer     NOT NULL CHECK (credits >= 0),
    active     boolean     NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS charged_disputes (
    tenant_id  text        NOT NULL REFERENCES accounts (tenant_id),
    dispute_id text        NOT NULL,
    order_id   text        NOT NULL,
    charged_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, dispute_id)
);
"""


class UnknownTenant(Exception):
    pass


class _RollbackInsufficient(Exception):
    pass


class PostgresAccountRepository:
    """AccountRepository ka asyncpg implementation."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_by_key_hash(self, key_hash: str) -> Account | None:
        row = await self._pool.fetchrow(
            "SELECT tenant_id, credits, active FROM accounts WHERE key_hash = $1", key_hash
        )
        if row is None:
            return None
        return Account(tenant_id=row["tenant_id"], credits=row["credits"], active=row["active"])

    async def check_charge(self, tenant_id: str, dispute_id: str, order_id: str) -> ChargeOutcome:
        async with self._pool.acquire() as conn:
            charged_order = await conn.fetchval(
                "SELECT order_id FROM charged_disputes WHERE tenant_id = $1 AND dispute_id = $2",
                tenant_id, dispute_id,
            )
            if charged_order is not None:
                return _existing(charged_order, order_id)
            credits = await conn.fetchval(
                "SELECT credits FROM accounts WHERE tenant_id = $1", tenant_id
            )
        if not credits:
            return ChargeOutcome.INSUFFICIENT_CREDITS
        return ChargeOutcome.CHARGED

    async def charge(self, tenant_id: str, dispute_id: str, order_id: str) -> ChargeOutcome:
        async with self._pool.acquire() as conn:
            try:
                async with conn.transaction():
                    # Same dispute ki concurrent request yahan unique index pe wait karti hai,
                    # pehli commit ke baad DO NOTHING → neeche "already charged" path.
                    inserted = await conn.fetchval(
                        """
                        INSERT INTO charged_disputes (tenant_id, dispute_id, order_id)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (tenant_id, dispute_id) DO NOTHING
                        RETURNING true
                        """,
                        tenant_id, dispute_id, order_id,
                    )
                    if inserted:
                        # Row lock: do alag disputes ek hi aakhri credit nahi le sakte
                        remaining = await conn.fetchval(
                            "UPDATE accounts SET credits = credits - 1"
                            " WHERE tenant_id = $1 AND credits > 0 RETURNING credits",
                            tenant_id,
                        )
                        if remaining is None:
                            raise _RollbackInsufficient
                        return ChargeOutcome.CHARGED
            except _RollbackInsufficient:
                return ChargeOutcome.INSUFFICIENT_CREDITS

            charged_order = await conn.fetchval(
                "SELECT order_id FROM charged_disputes WHERE tenant_id = $1 AND dispute_id = $2",
                tenant_id, dispute_id,
            )
        return _existing(charged_order, order_id)

    async def get_credits(self, tenant_id: str) -> int:
        credits = await self._pool.fetchval(
            "SELECT credits FROM accounts WHERE tenant_id = $1", tenant_id
        )
        if credits is None:
            raise UnknownTenant(tenant_id)
        return int(credits)

    async def create(self, tenant_id: str, key_hash: str, credits: int) -> None:
        await self._pool.execute(
            "INSERT INTO accounts (tenant_id, key_hash, credits) VALUES ($1, $2, $3)",
            tenant_id, key_hash, credits,
        )

    async def add_credits(self, tenant_id: str, amount: int) -> int:
        credits = await self._pool.fetchval(
            "UPDATE accounts SET credits = credits + $2 WHERE tenant_id = $1 RETURNING credits",
            tenant_id, amount,
        )
        if credits is None:
            raise UnknownTenant(tenant_id)
        return int(credits)

    async def set_active(self, tenant_id: str, active: bool) -> None:
        status = await self._pool.execute(
            "UPDATE accounts SET active = $2 WHERE tenant_id = $1", tenant_id, active
        )
        if status == "UPDATE 0":
            raise UnknownTenant(tenant_id)


def _existing(charged_order: str, order_id: str) -> ChargeOutcome:
    if charged_order == order_id:
        return ChargeOutcome.ALREADY_CHARGED
    return ChargeOutcome.DISPUTE_ID_CONFLICT

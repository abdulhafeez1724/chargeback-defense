import logging

import asyncpg

from infrastructure.postgres_accounts import ACCOUNTS_SCHEMA
from domain.entities import (
    Attachment,
    Dispute,
    DisputeReason,
    EvidenceItem,
    EvidenceType,
    Order,
)

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS disputes (
    tenant_id        text        NOT NULL,
    dispute_id       text        NOT NULL,
    reason           text        NOT NULL,
    order_id         text        NOT NULL,
    amount           numeric(12, 2) NOT NULL,
    currency         char(3)     NOT NULL,
    placed_at        timestamptz NOT NULL,
    customer_email   text        NOT NULL,
    billing_address  text        NOT NULL,
    shipping_address text        NOT NULL,
    customer_ip      text,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, dispute_id)
);

CREATE TABLE IF NOT EXISTS dispute_evidence (
    tenant_id             text    NOT NULL,
    dispute_id            text    NOT NULL,
    position              integer NOT NULL,
    type                  text    NOT NULL,
    summary               text    NOT NULL,
    attachment_ref        text,
    attachment_filename   text,
    attachment_media_type text,
    attachment_data       bytea,
    PRIMARY KEY (tenant_id, dispute_id, position),
    FOREIGN KEY (tenant_id, dispute_id)
        REFERENCES disputes (tenant_id, dispute_id) ON DELETE CASCADE
);
"""


async def create_pool(dsn: str) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA)
        await conn.execute(ACCOUNTS_SCHEMA)
    logger.info("postgres pool ready, schema ensured")
    return pool


class PostgresDisputeRepository:
    """DisputeRepository port ka asyncpg implementation."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, tenant_id: str, dispute_id: str) -> Dispute | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM disputes WHERE tenant_id = $1 AND dispute_id = $2",
                tenant_id,
                dispute_id,
            )
            if row is None:
                return None
            evidence_rows = await conn.fetch(
                "SELECT * FROM dispute_evidence"
                " WHERE tenant_id = $1 AND dispute_id = $2 ORDER BY position",
                tenant_id,
                dispute_id,
            )

        return Dispute(
            dispute_id=row["dispute_id"],
            tenant_id=row["tenant_id"],
            reason=DisputeReason(row["reason"]),
            order=Order(
                order_id=row["order_id"],
                amount=row["amount"],
                currency=row["currency"],
                placed_at=row["placed_at"],
                customer_email=row["customer_email"],
                billing_address=row["billing_address"],
                shipping_address=row["shipping_address"],
                customer_ip=row["customer_ip"],
            ),
            evidence=[_evidence_from_row(r) for r in evidence_rows],
        )

    async def save(self, dispute: Dispute) -> None:
        o = dispute.order
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(
                """
                INSERT INTO disputes (tenant_id, dispute_id, reason, order_id, amount, currency,
                    placed_at, customer_email, billing_address, shipping_address, customer_ip)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (tenant_id, dispute_id) DO UPDATE SET
                    reason = EXCLUDED.reason, order_id = EXCLUDED.order_id,
                    amount = EXCLUDED.amount, currency = EXCLUDED.currency,
                    placed_at = EXCLUDED.placed_at, customer_email = EXCLUDED.customer_email,
                    billing_address = EXCLUDED.billing_address,
                    shipping_address = EXCLUDED.shipping_address,
                    customer_ip = EXCLUDED.customer_ip, updated_at = now()
                """,
                dispute.tenant_id, dispute.dispute_id, dispute.reason.value, o.order_id,
                o.amount, o.currency, o.placed_at, o.customer_email, o.billing_address,
                o.shipping_address, o.customer_ip,
            )
            await conn.execute(
                "DELETE FROM dispute_evidence WHERE tenant_id = $1 AND dispute_id = $2",
                dispute.tenant_id,
                dispute.dispute_id,
            )
            await conn.executemany(
                """
                INSERT INTO dispute_evidence (tenant_id, dispute_id, position, type, summary,
                    attachment_ref, attachment_filename, attachment_media_type, attachment_data)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                [
                    (
                        dispute.tenant_id, dispute.dispute_id, i, e.type.value, e.summary,
                        e.attachment_ref,
                        e.attachment.filename if e.attachment else None,
                        e.attachment.media_type if e.attachment else None,
                        e.attachment.data if e.attachment else None,
                    )
                    for i, e in enumerate(dispute.evidence)
                ],
            )


def _evidence_from_row(r: asyncpg.Record) -> EvidenceItem:
    attachment = None
    if r["attachment_data"] is not None:
        attachment = Attachment(
            filename=r["attachment_filename"],
            media_type=r["attachment_media_type"],
            data=bytes(r["attachment_data"]),
        )
    return EvidenceItem(
        type=EvidenceType(r["type"]),
        summary=r["summary"],
        attachment_ref=r["attachment_ref"],
        attachment=attachment,
    )

from typing import Protocol

from domain.entities import Dispute
from domain.evidence_policy import EvidenceGap


class DisputeRepository(Protocol):
    """Disputes ka storage port. Har call tenant-scoped hai."""

    async def get(self, tenant_id: str, dispute_id: str) -> Dispute | None:
        """Dispute return kare, ya None agar is tenant ke liye mojood nahi."""
        ...

    async def save(self, dispute: Dispute) -> None:
        """Dispute insert/update kare (upsert), dispute.tenant_id ke under."""
        ...


class EvidencePackRenderer(Protocol):
    """Evidence pack ko document (PDF) bytes me render karta hai."""

    async def render(self, dispute: Dispute, gap: EvidenceGap) -> bytes:
        """CPU-bound implementations event loop block na karein (asyncio.to_thread)."""
        ...

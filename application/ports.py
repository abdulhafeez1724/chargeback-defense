from typing import Protocol

from domain.accounts import Account, ChargeOutcome
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


class AccountRepository(Protocol):
    """API-key accounts aur credits. charge() atomic hona chahiye (concurrent requests)."""

    async def get_by_key_hash(self, key_hash: str) -> Account | None: ...

    async def check_charge(self, tenant_id: str, dispute_id: str, order_id: str) -> ChargeOutcome:
        """Read-only preview: charge() abhi chale to kya hoga. Kuch nahi badalta."""
        ...

    async def charge(self, tenant_id: str, dispute_id: str, order_id: str) -> ChargeOutcome: ...

    async def get_credits(self, tenant_id: str) -> int: ...

    # Admin operations (scripts/admin.py)
    async def create(self, tenant_id: str, key_hash: str, credits: int) -> None: ...

    async def add_credits(self, tenant_id: str, amount: int) -> int: ...

    async def set_active(self, tenant_id: str, active: bool) -> None: ...

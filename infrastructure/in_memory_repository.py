from domain.entities import Dispute


class InMemoryDisputeRepository:
    """DisputeRepository port ka dev/test implementation. Restart pe data khatam."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], Dispute] = {}

    async def get(self, tenant_id: str, dispute_id: str) -> Dispute | None:
        return self._items.get((tenant_id, dispute_id))

    async def save(self, dispute: Dispute) -> None:
        self._items[(dispute.tenant_id, dispute.dispute_id)] = dispute

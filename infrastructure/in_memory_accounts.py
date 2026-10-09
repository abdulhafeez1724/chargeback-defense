from domain.accounts import Account, ChargeOutcome


class InMemoryAccountRepository:
    """AccountRepository ka dev/test implementation.

    Methods me koi await nahi, is liye asyncio me har call atomic hai.
    """

    def __init__(self) -> None:
        self._by_tenant: dict[str, tuple[str, int, bool]] = {}  # tenant → (key_hash, credits, active)
        self._charged: dict[tuple[str, str], str] = {}  # (tenant, dispute) → order_id

    async def get_by_key_hash(self, key_hash: str) -> Account | None:
        for tenant, (h, credits, active) in self._by_tenant.items():
            if h == key_hash:
                return Account(tenant_id=tenant, credits=credits, active=active)
        return None

    async def check_charge(self, tenant_id: str, dispute_id: str, order_id: str) -> ChargeOutcome:
        charged_order = self._charged.get((tenant_id, dispute_id))
        if charged_order is not None:
            if charged_order == order_id:
                return ChargeOutcome.ALREADY_CHARGED
            return ChargeOutcome.DISPUTE_ID_CONFLICT
        if self._by_tenant[tenant_id][1] < 1:
            return ChargeOutcome.INSUFFICIENT_CREDITS
        return ChargeOutcome.CHARGED

    async def charge(self, tenant_id: str, dispute_id: str, order_id: str) -> ChargeOutcome:
        outcome = await self.check_charge(tenant_id, dispute_id, order_id)
        if outcome is ChargeOutcome.CHARGED:
            key_hash, credits, active = self._by_tenant[tenant_id]
            self._by_tenant[tenant_id] = (key_hash, credits - 1, active)
            self._charged[(tenant_id, dispute_id)] = order_id
        return outcome

    async def get_credits(self, tenant_id: str) -> int:
        return self._by_tenant[tenant_id][1]

    async def create(self, tenant_id: str, key_hash: str, credits: int) -> None:
        if tenant_id in self._by_tenant:
            raise ValueError(f"tenant {tenant_id!r} already exists")
        self._by_tenant[tenant_id] = (key_hash, credits, True)

    async def add_credits(self, tenant_id: str, amount: int) -> int:
        key_hash, credits, active = self._by_tenant[tenant_id]
        self._by_tenant[tenant_id] = (key_hash, credits + amount, active)
        return credits + amount

    async def set_active(self, tenant_id: str, active: bool) -> None:
        key_hash, credits, _ = self._by_tenant[tenant_id]
        self._by_tenant[tenant_id] = (key_hash, credits, active)

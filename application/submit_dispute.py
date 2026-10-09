import logging

from application.build_evidence_pack import BuildEvidencePackUseCase, EvidencePack
from application.ports import AccountRepository, DisputeRepository
from domain.accounts import ChargeOutcome
from domain.entities import Dispute

logger = logging.getLogger(__name__)


class ChargeRejected(Exception):
    def __init__(self, outcome: ChargeOutcome) -> None:
        super().__init__(outcome.value)
        self.outcome = outcome


class SubmitDisputeUseCase:
    """Dispute save → PDF → credit charge. Credit sirf kamyab PDF pe katta hai."""

    def __init__(
        self,
        disputes: DisputeRepository,
        accounts: AccountRepository,
        build_pack: BuildEvidencePackUseCase,
    ) -> None:
        self._disputes = disputes
        self._accounts = accounts
        self._build_pack = build_pack

    async def execute(self, dispute: Dispute) -> tuple[EvidencePack, int]:
        """(pack, credits_remaining) return karta hai, ya ChargeRejected raise."""
        key = (dispute.tenant_id, dispute.dispute_id, dispute.order.order_id)

        # Sasta pre-check: bina credit ke PDF render ka kaam na karein
        preview = await self._accounts.check_charge(*key)
        if not preview.allowed:
            raise ChargeRejected(preview)

        await self._disputes.save(dispute)
        pack = await self._build_pack.execute(dispute.tenant_id, dispute.dispute_id)

        # Asal faisla atomic charge me — pre-check ke baad concurrent request credit le sakti hai
        outcome = await self._accounts.charge(*key)
        if not outcome.allowed:
            raise ChargeRejected(outcome)

        remaining = await self._accounts.get_credits(dispute.tenant_id)
        logger.info(
            "tenant %s dispute %s: %s, %d credits left",
            dispute.tenant_id, dispute.dispute_id, outcome.value, remaining,
        )
        return pack, remaining

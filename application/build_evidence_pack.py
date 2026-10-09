import logging
from dataclasses import dataclass

from application.ports import DisputeRepository, EvidencePackRenderer
from domain.evidence_policy import EvidenceGap, assess

logger = logging.getLogger(__name__)


class DisputeNotFound(Exception):
    def __init__(self, tenant_id: str, dispute_id: str) -> None:
        super().__init__(f"dispute {dispute_id!r} not found for tenant {tenant_id!r}")
        self.tenant_id = tenant_id
        self.dispute_id = dispute_id


@dataclass(frozen=True, slots=True)
class EvidencePack:
    dispute_id: str
    gap: EvidenceGap
    document: bytes


class BuildEvidencePackUseCase:
    def __init__(self, repo: DisputeRepository, renderer: EvidencePackRenderer) -> None:
        self._repo = repo
        self._renderer = renderer

    async def execute(self, tenant_id: str, dispute_id: str) -> EvidencePack:
        dispute = await self._repo.get(tenant_id, dispute_id)
        if dispute is None:
            raise DisputeNotFound(tenant_id, dispute_id)

        gap = assess(dispute)
        if gap.missing:
            logger.info(
                "dispute %s missing evidence: %s",
                dispute_id,
                sorted(t.value for t in gap.missing),
            )

        document = await self._renderer.render(dispute, gap)
        return EvidencePack(dispute_id=dispute_id, gap=gap, document=document)

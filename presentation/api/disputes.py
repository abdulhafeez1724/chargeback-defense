from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from application.build_evidence_pack import BuildEvidencePackUseCase, DisputeNotFound
from application.ports import DisputeRepository
from domain.entities import DisputeReason, EvidenceType
from domain.evidence_policy import required_for
from presentation.api.deps import get_build_pack_use_case, get_repository, get_tenant_id
from presentation.api.schemas import DisputeIn

router = APIRouter(prefix="/disputes", tags=["disputes"])


@router.get("/requirements")
async def evidence_requirements() -> dict[DisputeReason, list[EvidenceType]]:
    """Har reason ke liye required evidence — form isi se checklist dikhata hai."""
    return {reason: sorted(required_for(reason)) for reason in DisputeReason}


@router.post(
    "",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}, "description": "Evidence pack PDF"}},
)
async def create_evidence_pack(
    payload: DisputeIn,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    repo: Annotated[DisputeRepository, Depends(get_repository)],
    use_case: Annotated[BuildEvidencePackUseCase, Depends(get_build_pack_use_case)],
) -> Response:
    await repo.save(payload.to_domain(tenant_id))
    try:
        pack = await use_case.execute(tenant_id, payload.dispute_id)
    except DisputeNotFound as exc:  # save ke foran baad nahi hona chahiye
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "dispute not persisted") from exc

    # Gap merchant ke liye headers me — PDF issuer ko jati hai, us me weakness nahi likhte
    return Response(
        content=pack.document,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="evidence-{pack.dispute_id}.pdf"',
            "X-Evidence-Strength": f"{pack.gap.strength:.2f}",
            "X-Evidence-Missing": ",".join(sorted(pack.gap.missing)),
        },
    )

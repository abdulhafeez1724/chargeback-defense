from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from application.build_evidence_pack import DisputeNotFound
from application.submit_dispute import ChargeRejected, SubmitDisputeUseCase
from domain.accounts import Account, ChargeOutcome
from domain.entities import DisputeReason, EvidenceType
from domain.evidence_policy import required_for
from presentation.api.deps import get_account, get_submit_use_case
from presentation.api.schemas import DisputeIn

router = APIRouter(prefix="/disputes", tags=["disputes"])

_REJECTION: dict[ChargeOutcome, tuple[int, str]] = {
    ChargeOutcome.INSUFFICIENT_CREDITS: (
        status.HTTP_402_PAYMENT_REQUIRED,
        "no credits left — buy another pack to generate a new dispute",
    ),
    ChargeOutcome.DISPUTE_ID_CONFLICT: (
        status.HTTP_409_CONFLICT,
        "this dispute_id was already used for a different order",
    ),
}


@router.get("/requirements")
async def evidence_requirements() -> dict[DisputeReason, list[EvidenceType]]:
    """Har reason ke liye required evidence — form isi se checklist dikhata hai."""
    return {reason: sorted(required_for(reason)) for reason in DisputeReason}


@router.post(
    "",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "Evidence pack PDF"},
        402: {"description": "No credits left"},
        409: {"description": "dispute_id reused for a different order"},
    },
)
async def create_evidence_pack(
    payload: DisputeIn,
    account: Annotated[Account, Depends(get_account)],
    use_case: Annotated[SubmitDisputeUseCase, Depends(get_submit_use_case)],
) -> Response:
    try:
        pack, credits_remaining = await use_case.execute(payload.to_domain(account.tenant_id))
    except ChargeRejected as exc:
        code, detail = _REJECTION[exc.outcome]
        raise HTTPException(code, detail) from exc
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
            "X-Credits-Remaining": str(credits_remaining),
        },
    )

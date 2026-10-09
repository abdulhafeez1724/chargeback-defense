from typing import Annotated

from fastapi import APIRouter, Depends

from domain.accounts import Account
from presentation.api.deps import get_account

router = APIRouter(tags=["account"])


@router.get("/account")
async def account_info(account: Annotated[Account, Depends(get_account)]) -> dict[str, str | int]:
    return {"tenant_id": account.tenant_id, "credits": account.credits}

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from application.build_evidence_pack import BuildEvidencePackUseCase
from application.ports import AccountRepository, DisputeRepository, EvidencePackRenderer
from application.submit_dispute import SubmitDisputeUseCase
from domain.accounts import Account, hash_api_key
from infrastructure.pdf_renderer import FpdfEvidencePackRenderer

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_renderer = FpdfEvidencePackRenderer()


# main.py ka lifespan app start pe repos set karta hai (Postgres ya in-memory)
def get_repository(request: Request) -> DisputeRepository:
    repo: DisputeRepository = request.app.state.repo
    return repo


def get_accounts(request: Request) -> AccountRepository:
    accounts: AccountRepository = request.app.state.accounts
    return accounts


def get_renderer() -> EvidencePackRenderer:
    return _renderer


async def get_account(
    api_key: Annotated[str | None, Depends(_api_key_header)],
    accounts: Annotated[AccountRepository, Depends(get_accounts)],
) -> Account:
    # Hash pe lookup — DB me asal key kabhi store nahi hoti
    account = await accounts.get_by_key_hash(hash_api_key(api_key)) if api_key else None
    if account is None or not account.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing API key",
            headers={"WWW-Authenticate": "APIKey"},
        )
    return account


def get_submit_use_case(
    repo: Annotated[DisputeRepository, Depends(get_repository)],
    accounts: Annotated[AccountRepository, Depends(get_accounts)],
    renderer: Annotated[EvidencePackRenderer, Depends(get_renderer)],
) -> SubmitDisputeUseCase:
    return SubmitDisputeUseCase(repo, accounts, BuildEvidencePackUseCase(repo, renderer))

import hmac
import logging
import os
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from application.build_evidence_pack import BuildEvidencePackUseCase
from application.ports import DisputeRepository, EvidencePackRenderer
from infrastructure.pdf_renderer import FpdfEvidencePackRenderer

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@lru_cache
def _api_keys() -> dict[str, str]:
    """CHARGEBACK_API_KEYS="key1:tenant1,key2:tenant2" → {key: tenant_id}."""
    raw = os.environ.get("CHARGEBACK_API_KEYS", "")
    keys: dict[str, str] = {}
    for pair in filter(None, (p.strip() for p in raw.split(","))):
        key, sep, tenant = pair.partition(":")
        if not sep or not key or not tenant:
            raise RuntimeError("CHARGEBACK_API_KEYS entries must be 'key:tenant'")
        keys[key] = tenant
    if not keys:
        logger.warning("CHARGEBACK_API_KEYS is empty — all requests will be rejected")
    return keys


async def get_tenant_id(api_key: Annotated[str | None, Depends(_api_key_header)]) -> str:
    if api_key:
        for key, tenant in _api_keys().items():
            if hmac.compare_digest(key.encode(), api_key.encode()):
                return tenant
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid or missing API key",
        headers={"WWW-Authenticate": "APIKey"},
    )


def get_repository(request: Request) -> DisputeRepository:
    # main.py ka lifespan app start pe set karta hai (Postgres ya in-memory)
    repo: DisputeRepository = request.app.state.repo
    return repo


@lru_cache
def get_renderer() -> EvidencePackRenderer:
    return FpdfEvidencePackRenderer()


def get_build_pack_use_case(
    repo: Annotated[DisputeRepository, Depends(get_repository)],
    renderer: Annotated[EvidencePackRenderer, Depends(get_renderer)],
) -> BuildEvidencePackUseCase:
    return BuildEvidencePackUseCase(repo, renderer)

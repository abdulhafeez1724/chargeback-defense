import hashlib
import secrets
from dataclasses import dataclass
from enum import StrEnum

API_KEY_PREFIX = "cbd_"


@dataclass(frozen=True, slots=True)
class Account:
    tenant_id: str
    credits: int
    active: bool


class ChargeOutcome(StrEnum):
    """Ek dispute ke liye credit katne ka nateeja.

    Rule: har naye dispute pe 1 credit. Same dispute + same order dobara = free
    (typo fix karke PDF regenerate). Same dispute_id pe alag order = conflict.
    """

    CHARGED = "charged"
    ALREADY_CHARGED = "already_charged"
    INSUFFICIENT_CREDITS = "insufficient_credits"
    DISPUTE_ID_CONFLICT = "dispute_id_conflict"

    @property
    def allowed(self) -> bool:
        return self in (ChargeOutcome.CHARGED, ChargeOutcome.ALREADY_CHARGED)


def generate_api_key() -> str:
    return API_KEY_PREFIX + secrets.token_urlsafe(24)


def hash_api_key(key: str) -> str:
    # Random high-entropy keys ke liye SHA-256 kaafi hai (passwords ke liye bcrypt/argon2 chahiye hota)
    return hashlib.sha256(key.encode()).hexdigest()

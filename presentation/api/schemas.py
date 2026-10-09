from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Self

from PIL import Image, UnidentifiedImageError
from pydantic import Base64Bytes, BaseModel, ConfigDict, Field, field_validator, model_validator

from domain.entities import (
    Attachment,
    Dispute,
    DisputeReason,
    EvidenceItem,
    EvidenceType,
    Order,
)

MAX_ATTACHMENT_BYTES = 4 * 1024 * 1024
MAX_ATTACHMENTS = 10
MAX_IMAGE_PIXELS = 40_000_000  # decompression bomb guard
_MEDIA_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg"}


def sniff_image(data: bytes) -> str:
    """Asal bytes se format pehchano — client ka content-type trust nahi karte."""
    try:
        with Image.open(BytesIO(data)) as img:
            fmt = img.format or ""
            width, height = img.size  # header se, poori image decode kiye baghair
            if fmt not in _MEDIA_TYPES:
                raise ValueError("attachment must be a PNG or JPEG image")
            if width * height > MAX_IMAGE_PIXELS:
                raise ValueError("image dimensions too large")
            img.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("attachment is not a valid PNG or JPEG image") from exc
    return _MEDIA_TYPES[fmt]


class AttachmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1, max_length=200)
    data: Base64Bytes

    @field_validator("data")
    @classmethod
    def _valid_image(cls, v: bytes) -> bytes:
        if len(v) > MAX_ATTACHMENT_BYTES:
            raise ValueError("attachment larger than 4 MB")
        sniff_image(v)
        return v

    def to_domain(self) -> Attachment:
        return Attachment(filename=self.filename, media_type=sniff_image(self.data), data=self.data)


class EvidenceItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: EvidenceType
    summary: str = Field(min_length=1, max_length=2000)
    attachment_ref: str | None = Field(default=None, max_length=500)
    attachment: AttachmentIn | None = None


class OrderIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    placed_at: datetime
    customer_email: str = Field(min_length=3, max_length=254)
    billing_address: str = Field(min_length=1, max_length=500)
    shipping_address: str = Field(min_length=1, max_length=500)
    customer_ip: str | None = Field(default=None, max_length=45)

    @field_validator("currency")
    @classmethod
    def _lower_alpha_currency(cls, v: str) -> str:
        if not v.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return v.lower()


class DisputeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dispute_id: str = Field(min_length=1, max_length=100)
    reason: DisputeReason
    order: OrderIn
    evidence: list[EvidenceItemIn] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def _limit_attachments(self) -> Self:
        if sum(e.attachment is not None for e in self.evidence) > MAX_ATTACHMENTS:
            raise ValueError(f"at most {MAX_ATTACHMENTS} attachments per dispute")
        return self

    def to_domain(self, tenant_id: str) -> Dispute:
        o = self.order
        return Dispute(
            dispute_id=self.dispute_id,
            tenant_id=tenant_id,
            reason=self.reason,
            order=Order(
                order_id=o.order_id,
                amount=o.amount,
                currency=o.currency,
                placed_at=o.placed_at,
                customer_email=o.customer_email,
                billing_address=o.billing_address,
                shipping_address=o.shipping_address,
                customer_ip=o.customer_ip,
            ),
            evidence=[
                EvidenceItem(
                    type=e.type,
                    summary=e.summary,
                    attachment_ref=e.attachment_ref,
                    attachment=e.attachment.to_domain() if e.attachment else None,
                )
                for e in self.evidence
            ],
        )

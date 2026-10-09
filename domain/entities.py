from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class DisputeReason(StrEnum):
    # Stripe `dispute.reason` values ka subset (docs.stripe.com/api/disputes/object, verified 2026-10)
    FRAUDULENT = "fraudulent"
    PRODUCT_NOT_RECEIVED = "product_not_received"
    PRODUCT_UNACCEPTABLE = "product_unacceptable"
    DUPLICATE = "duplicate"
    SUBSCRIPTION_CANCELED = "subscription_canceled"
    CREDIT_NOT_PROCESSED = "credit_not_processed"


class EvidenceType(StrEnum):
    TRACKING = "tracking"
    DELIVERY_PROOF = "delivery_proof"
    CUSTOMER_IP = "customer_ip"
    BILLING_MATCH = "billing_match"
    CUSTOMER_COMMUNICATION = "customer_communication"
    REFUND_POLICY = "refund_policy"
    PRODUCT_DESCRIPTION = "product_description"
    CANCELLATION_POLICY = "cancellation_policy"
    SEPARATE_CHARGE_RECEIPT = "separate_charge_receipt"
    PRIOR_UNDISPUTED_PAYMENTS = "prior_undisputed_payments"


@dataclass(frozen=True, slots=True)
class Attachment:
    filename: str
    media_type: str  # "image/png" | "image/jpeg" — presentation layer verify karti hai
    data: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    type: EvidenceType
    summary: str
    attachment_ref: str | None = None
    attachment: Attachment | None = None


@dataclass(frozen=True, slots=True)
class Order:
    order_id: str
    amount: Decimal
    currency: str
    placed_at: datetime
    customer_email: str
    billing_address: str
    shipping_address: str
    customer_ip: str | None = None


@dataclass(slots=True)
class Dispute:
    dispute_id: str
    tenant_id: str
    order: Order
    reason: DisputeReason
    evidence: list[EvidenceItem] = field(default_factory=list)

    def add_evidence(self, item: EvidenceItem) -> None:
        self.evidence.append(item)

    def provided_types(self) -> set[EvidenceType]:
        return {e.type for e in self.evidence}

from dataclasses import dataclass

from domain.entities import Dispute, DisputeReason, EvidenceType

# Physical-goods sellers ke liye, Stripe "Dispute reason code categories" guide pe based
# (docs.stripe.com/disputes/categories, verified 2026-10). Baaki types optional/supporting hain.
_REQUIRED: dict[DisputeReason, frozenset[EvidenceType]] = {
    DisputeReason.FRAUDULENT: frozenset(
        {EvidenceType.BILLING_MATCH, EvidenceType.TRACKING, EvidenceType.DELIVERY_PROOF}
    ),
    DisputeReason.PRODUCT_NOT_RECEIVED: frozenset(
        {EvidenceType.TRACKING, EvidenceType.DELIVERY_PROOF}
    ),
    DisputeReason.PRODUCT_UNACCEPTABLE: frozenset(
        {EvidenceType.PRODUCT_DESCRIPTION, EvidenceType.REFUND_POLICY,
         EvidenceType.CUSTOMER_COMMUNICATION}
    ),
    DisputeReason.DUPLICATE: frozenset(
        {EvidenceType.SEPARATE_CHARGE_RECEIPT, EvidenceType.TRACKING}
    ),
    DisputeReason.SUBSCRIPTION_CANCELED: frozenset(
        {EvidenceType.CANCELLATION_POLICY, EvidenceType.CUSTOMER_COMMUNICATION}
    ),
    DisputeReason.CREDIT_NOT_PROCESSED: frozenset(
        {EvidenceType.REFUND_POLICY, EvidenceType.CUSTOMER_COMMUNICATION}
    ),
}


@dataclass(frozen=True, slots=True)
class EvidenceGap:
    missing: frozenset[EvidenceType]
    strength: float  # 0.0–1.0, provided/required ratio


def required_for(reason: DisputeReason) -> frozenset[EvidenceType]:
    return _REQUIRED[reason]


def assess(dispute: Dispute) -> EvidenceGap:
    required = required_for(dispute.reason)
    missing = required - dispute.provided_types()
    strength = 1 - len(missing) / len(required)
    return EvidenceGap(missing=frozenset(missing), strength=round(strength, 2))

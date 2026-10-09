import asyncio
import logging
from io import BytesIO

from fpdf import FPDF
from PIL import Image, ImageOps

from domain.entities import Attachment, Dispute, DisputeReason, EvidenceItem, EvidenceType
from domain.evidence_policy import EvidenceGap

logger = logging.getLogger(__name__)

# Generic rebuttal templates. Card-network specific requirements: verify in Stripe docs.
# Narrative sirf provided evidence ka claim karti hai — bina saboot ka claim case kamzor karta hai.
_INTRO: dict[DisputeReason, str] = {
    DisputeReason.FRAUDULENT: (
        "The cardholder claims this transaction was not authorized. "
        "The evidence below shows the order was placed by the legitimate cardholder."
    ),
    DisputeReason.PRODUCT_NOT_RECEIVED: (
        "The cardholder claims the product was not received. "
        "The evidence below shows the order was fulfilled."
    ),
    DisputeReason.PRODUCT_UNACCEPTABLE: (
        "The cardholder claims the product was not as described. "
        "The evidence below shows the product matched its description."
    ),
    DisputeReason.DUPLICATE: (
        "The cardholder claims they were charged more than once. "
        "The evidence below shows each charge corresponds to a separate purchase."
    ),
    DisputeReason.SUBSCRIPTION_CANCELED: (
        "The cardholder claims the subscription was canceled. "
        "The evidence below shows the charge was valid under the accepted terms."
    ),
    DisputeReason.CREDIT_NOT_PROCESSED: (
        "The cardholder claims a refund or credit was not processed. "
        "The evidence below shows the customer was not entitled to the refund claimed "
        "under the policy disclosed at purchase."
    ),
}

_CLAIM: dict[EvidenceType, str] = {
    EvidenceType.TRACKING: "The order was shipped with tracking.",
    EvidenceType.DELIVERY_PROOF: (
        "The carrier confirmed delivery to the shipping address provided by the customer."
    ),
    EvidenceType.CUSTOMER_IP: "The order originated from the customer's IP address.",
    EvidenceType.BILLING_MATCH: "The billing details matched the cardholder's information.",
    EvidenceType.CUSTOMER_COMMUNICATION: "Our communication with the customer is included.",
    EvidenceType.REFUND_POLICY: "Our refund policy was disclosed to the customer at purchase.",
    EvidenceType.PRODUCT_DESCRIPTION: "The product description shown at purchase is included.",
    EvidenceType.CANCELLATION_POLICY: (
        "Our cancellation policy was disclosed to the customer before purchase."
    ),
    EvidenceType.SEPARATE_CHARGE_RECEIPT: (
        "A separate receipt shows the other charge was for a different purchase."
    ),
    EvidenceType.PRIOR_UNDISPUTED_PAYMENTS: (
        "The same card was used for earlier purchases that were not disputed."
    ),
}


def _narrative(dispute: Dispute) -> str:
    # EvidenceType declaration order me — PDF output deterministic rahe
    claims = [_CLAIM[t] for t in EvidenceType if t in dispute.provided_types()]
    return " ".join([_INTRO[dispute.reason], *claims])

_EVIDENCE_LABEL: dict[EvidenceType, str] = {
    EvidenceType.TRACKING: "Shipment tracking",
    EvidenceType.DELIVERY_PROOF: "Proof of delivery",
    EvidenceType.CUSTOMER_IP: "Customer IP address",
    EvidenceType.BILLING_MATCH: "Billing details match",
    EvidenceType.CUSTOMER_COMMUNICATION: "Customer communication",
    EvidenceType.REFUND_POLICY: "Refund policy",
    EvidenceType.PRODUCT_DESCRIPTION: "Product description",
    EvidenceType.CANCELLATION_POLICY: "Cancellation policy",
    EvidenceType.SEPARATE_CHARGE_RECEIPT: "Receipt for the other (non-duplicate) charge",
    EvidenceType.PRIOR_UNDISPUTED_PAYMENTS: "Prior undisputed payments on the same card",
}


def _upright_image(data: bytes) -> Image.Image:
    # Phone photos EXIF orientation tag use karti hain — apply na karo to PDF me terchi
    with Image.open(BytesIO(data)) as img:
        return ImageOps.exif_transpose(img)


def _latin1(text: str) -> str:
    # fpdf2 core fonts sirf latin-1 support karte hain
    return text.encode("latin-1", "replace").decode("latin-1")


class FpdfEvidencePackRenderer:
    """EvidencePackRenderer port ka fpdf2 implementation."""

    async def render(self, dispute: Dispute, gap: EvidenceGap) -> bytes:
        # PDF generation CPU-bound hai — event loop block na ho
        return await asyncio.to_thread(self._render_sync, dispute, gap)

    def _render_sync(self, dispute: Dispute, gap: EvidenceGap) -> bytes:
        order = dispute.order
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        def heading(text: str) -> None:
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, _latin1(text), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)

        def line(text: str) -> None:
            pdf.multi_cell(0, 6, _latin1(text), new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, "Dispute Evidence Pack", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        line(f"Dispute ID: {dispute.dispute_id}")
        line(f"Reason: {dispute.reason.value.replace('_', ' ').title()}")

        heading("Summary")
        line(_narrative(dispute))

        heading("Order details")
        line(f"Order ID: {order.order_id}")
        line(f"Amount: {order.amount} {order.currency.upper()}")
        line(f"Placed at: {order.placed_at.isoformat(sep=' ', timespec='minutes')}")
        line(f"Customer email: {order.customer_email}")
        line(f"Billing address: {order.billing_address}")
        line(f"Shipping address: {order.shipping_address}")
        if order.customer_ip:
            line(f"Customer IP: {order.customer_ip}")

        heading("Evidence")
        if not dispute.evidence:
            line("No evidence items provided.")
        exhibits: list[tuple[int, EvidenceItem, Attachment]] = []
        for i, item in enumerate(dispute.evidence, start=1):
            pdf.set_font("Helvetica", "B", 10)
            line(f"{i}. {_EVIDENCE_LABEL[item.type]}")
            pdf.set_font("Helvetica", "", 10)
            line(item.summary)
            if item.attachment_ref:
                line(f"Attachment: {item.attachment_ref}")
            if item.attachment:
                exhibits.append((len(exhibits) + 1, item, item.attachment))
                line(f"See Exhibit {len(exhibits)}.")

        # Har exhibit apne page pe, image page me fit (aspect ratio same)
        for n, item, att in exhibits:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(
                0, 8, _latin1(f"Exhibit {n}: {_EVIDENCE_LABEL[item.type]}"),
                new_x="LMARGIN", new_y="NEXT",
            )
            pdf.set_font("Helvetica", "", 9)
            line(f"File: {att.filename}")
            pdf.ln(2)
            pdf.image(
                _upright_image(att.data),
                w=pdf.epw,
                h=pdf.h - pdf.get_y() - pdf.b_margin,
                keep_aspect_ratio=True,
            )

        output = bytes(pdf.output())
        logger.info(
            "rendered pack for dispute %s (%d bytes, strength %.2f)",
            dispute.dispute_id,
            len(output),
            gap.strength,
        )
        return output

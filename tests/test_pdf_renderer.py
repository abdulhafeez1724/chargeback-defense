from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO

from PIL import Image

from domain.entities import Dispute, DisputeReason, EvidenceItem, EvidenceType, Order
from infrastructure.pdf_renderer import _narrative, _upright_image


def _fraud_dispute(*types: EvidenceType) -> Dispute:
    order = Order(
        order_id="1001",
        amount=Decimal("89.00"),
        currency="usd",
        placed_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
        customer_email="jane@example.com",
        billing_address="12 Oak Ave",
        shipping_address="12 Oak Ave",
    )
    d = Dispute("dp_1", "t1", order, DisputeReason.FRAUDULENT)
    for t in types:
        d.add_evidence(EvidenceItem(t, "x"))
    return d


def test_narrative_does_not_claim_unprovided_evidence() -> None:
    text = _narrative(_fraud_dispute(EvidenceType.CUSTOMER_IP, EvidenceType.BILLING_MATCH))

    assert "IP address" in text
    assert "billing details" in text
    assert "delivery" not in text.lower()


def test_narrative_includes_delivery_when_provided() -> None:
    text = _narrative(_fraud_dispute(EvidenceType.DELIVERY_PROOF))
    assert "confirmed delivery" in text


def test_upright_image_applies_exif_rotation() -> None:
    # 400x200 landscape pixels, EXIF orientation 6 = "rotate 90° CW to display"
    img = Image.new("RGB", (400, 200))
    exif = Image.Exif()
    exif[0x0112] = 6
    buf = BytesIO()
    img.save(buf, format="JPEG", exif=exif)

    assert _upright_image(buf.getvalue()).size == (200, 400)

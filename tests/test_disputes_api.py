import asyncio
import base64
from collections.abc import Iterator
from io import BytesIO
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from main import app

HEADERS = {"X-API-Key": "test-key"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DEV_API_KEYS", "test-key:tenant-a")
    monkeypatch.setenv("DEV_CREDITS", "2")
    with TestClient(app) as c:
        yield c


def _payload(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "dispute_id": "dp_123",
        "reason": "product_not_received",
        "order": {
            "order_id": "1001",
            "amount": "49.99",
            "currency": "USD",
            "placed_at": "2026-10-01T12:00:00Z",
            "customer_email": "buyer@example.com",
            "billing_address": "1 Main St, Austin, TX",
            "shipping_address": "1 Main St, Austin, TX",
        },
        "evidence": [
            {"type": "tracking", "summary": "USPS 9400 1000 0000 0000 0000 00 — delivered Oct 4"},
            {"type": "delivery_proof", "summary": "Carrier delivery scan with photo"},
        ],
    }
    body.update(overrides)
    return body


def test_returns_pdf_with_strength_headers(client: TestClient) -> None:
    res = client.post("/disputes", json=_payload(), headers=HEADERS)

    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")
    assert res.headers["x-evidence-strength"] == "1.00"
    assert res.headers["x-evidence-missing"] == ""


def test_reports_missing_evidence(client: TestClient) -> None:
    res = client.post("/disputes", json=_payload(evidence=[]), headers=HEADERS)

    assert res.status_code == 200
    assert res.headers["x-evidence-strength"] == "0.00"
    assert res.headers["x-evidence-missing"] == "delivery_proof,tracking"


def test_rejects_missing_api_key(client: TestClient) -> None:
    assert client.post("/disputes", json=_payload()).status_code == 401


def test_rejects_wrong_api_key(client: TestClient) -> None:
    res = client.post("/disputes", json=_payload(), headers={"X-API-Key": "nope"})
    assert res.status_code == 401


def test_validates_reason(client: TestClient) -> None:
    res = client.post("/disputes", json=_payload(reason="not_a_reason"), headers=HEADERS)
    assert res.status_code == 422


def _png_b64(width: int = 300, height: int = 200) -> str:
    buf = BytesIO()
    Image.new("RGB", (width, height), (200, 30, 30)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _evidence_with(data: str) -> list[dict[str, Any]]:
    return [{
        "type": "delivery_proof",
        "summary": "Delivery photo at front door",
        "attachment": {"filename": "delivery.png", "data": data},
    }]


def test_embeds_image_attachment_as_exhibit(client: TestClient) -> None:
    res = client.post("/disputes", json=_payload(evidence=_evidence_with(_png_b64())), headers=HEADERS)

    assert res.status_code == 200
    assert res.content.count(b"/Type /Page\n") + res.content.count(b"/Type /Page ") >= 2
    assert b"/Subtype /Image" in res.content


def test_rejects_non_image_disguised_as_png(client: TestClient) -> None:
    fake = base64.b64encode(b"<script>alert(1)</script>").decode()
    res = client.post("/disputes", json=_payload(evidence=_evidence_with(fake)), headers=HEADERS)

    assert res.status_code == 422
    assert "PNG or JPEG" in res.text


def test_rejects_too_many_attachments(client: TestClient) -> None:
    item = _evidence_with(_png_b64(10, 10))[0]
    res = client.post("/disputes", json=_payload(evidence=[item] * 11), headers=HEADERS)

    assert res.status_code == 422
    assert "at most 10 attachments" in res.text


def test_credits_charged_per_new_dispute(client: TestClient) -> None:
    first = client.post("/disputes", json=_payload(dispute_id="dp_a"), headers=HEADERS)
    again = client.post("/disputes", json=_payload(dispute_id="dp_a"), headers=HEADERS)
    second = client.post("/disputes", json=_payload(dispute_id="dp_b"), headers=HEADERS)
    third = client.post("/disputes", json=_payload(dispute_id="dp_c"), headers=HEADERS)

    assert first.headers["x-credits-remaining"] == "1"
    assert again.headers["x-credits-remaining"] == "1"  # regenerate free
    assert second.headers["x-credits-remaining"] == "0"
    assert third.status_code == 402
    assert client.get("/account", headers=HEADERS).json() == {"tenant_id": "tenant-a", "credits": 0}


def test_dispute_id_reused_for_other_order_conflicts(client: TestClient) -> None:
    client.post("/disputes", json=_payload(dispute_id="dp_a"), headers=HEADERS)
    other_order = _payload(dispute_id="dp_a")
    other_order["order"]["order_id"] = "9999"

    res = client.post("/disputes", json=other_order, headers=HEADERS)

    assert res.status_code == 409


def test_deactivated_key_rejected(client: TestClient) -> None:
    asyncio.run(app.state.accounts.set_active("tenant-a", False))
    assert client.post("/disputes", json=_payload(), headers=HEADERS).status_code == 401
    assert client.get("/account", headers=HEADERS).status_code == 401

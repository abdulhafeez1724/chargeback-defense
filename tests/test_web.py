from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from main import app
from presentation.api.body_limit import BodySizeLimitMiddleware
from presentation.web import routes


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("CHECKOUT_URL", "https://example.test/buy?a=1&b=2")
    monkeypatch.setenv("PACK_PRICE", "$19")
    routes._landing_html.cache_clear()
    with TestClient(app) as c:
        yield c
    routes._landing_html.cache_clear()


def test_landing_injects_escaped_config(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert 'href="https://example.test/buy?a=1&amp;b=2"' in res.text
    assert "{{" not in res.text


def test_builder_page_served(client: TestClient) -> None:
    res = client.get("/app")
    assert res.status_code == 200
    assert "Build your evidence pack" in res.text


def test_requirements_endpoint_is_public(client: TestClient) -> None:
    res = client.get("/disputes/requirements")
    assert res.status_code == 200
    assert res.json()["product_not_received"] == ["delivery_proof", "tracking"]


def test_rejects_oversized_body() -> None:
    async def echo(request: Request) -> PlainTextResponse:
        return PlainTextResponse(str(len(await request.body())))

    small = Starlette(routes=[Route("/", echo, methods=["POST"])])
    small.add_middleware(BodySizeLimitMiddleware, max_bytes=100)
    c = TestClient(small)

    assert c.post("/", content=b"x" * 100).text == "100"
    assert c.post("/", content=b"x" * 101).status_code == 413

    def chunks() -> Iterator[bytes]:  # Content-Length ke baghair (chunked)
        for _ in range(5):
            yield b"x" * 50

    assert c.post("/", content=chunks()).status_code == 413

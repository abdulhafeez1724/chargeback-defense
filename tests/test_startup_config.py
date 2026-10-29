"""APP_ENV=production me zaroori env vars ke baghair app start nahi honi chahiye."""

import pytest
from fastapi.testclient import TestClient

from main import PRODUCTION_REQUIRED_ENV, app


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("APP_ENV", "DEV_API_KEYS", *PRODUCTION_REQUIRED_ENV):
        monkeypatch.delenv(name, raising=False)


def test_production_without_config_fails_listing_all_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="DATABASE_URL, CHECKOUT_URL, CONTACT_EMAIL"):
        with TestClient(app):
            pass


def test_production_missing_database_url_fails_before_in_memory_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CHECKOUT_URL", "https://example.test/buy")
    monkeypatch.setenv("CONTACT_EMAIL", "help@example.test")
    with pytest.raises(RuntimeError, match=r"missing: DATABASE_URL$"):
        with TestClient(app):
            pass


def test_production_treats_empty_value_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    monkeypatch.setenv("CHECKOUT_URL", "")
    monkeypatch.setenv("CONTACT_EMAIL", "help@example.test")
    with pytest.raises(RuntimeError, match=r"missing: CHECKOUT_URL$"):
        with TestClient(app):
            pass


def test_without_app_env_dev_mode_starts_unchanged() -> None:
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}

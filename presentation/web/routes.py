import html
import os
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(include_in_schema=False)

_DIR = Path(__file__).parent


@lru_cache
def _landing_html() -> str:
    values = {
        # Lemon Squeezy / Gumroad product ka checkout link — account banne ke baad set karein
        "CHECKOUT_URL": os.environ.get("CHECKOUT_URL", "#pricing"),
        "PRICE": os.environ.get("PACK_PRICE", "$19"),
        "CONTACT_EMAIL": os.environ.get("CONTACT_EMAIL", "support@example.com"),
    }
    page = (_DIR / "landing.html").read_text(encoding="utf-8")
    for key, value in values.items():
        page = page.replace("{{" + key + "}}", html.escape(value))
    return page


@router.get("/", response_class=HTMLResponse)
async def landing() -> str:
    return _landing_html()


@router.get("/app", response_class=HTMLResponse)
async def builder() -> str:
    return (_DIR / "app.html").read_text(encoding="utf-8")

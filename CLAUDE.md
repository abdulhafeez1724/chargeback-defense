# Chargeback Defense Pack

## Goal
Small US online stores (Shopify/Stripe sellers) ke liye tool jo dispute/chargeback ka
evidence pack (PDF) banata hai taake merchant dispute jeet sake.
Target: is month (Oct 2026) pehle $100 kamana — per-dispute $15-25 ya small monthly plan.

## Plan (3 weeks)
- Week 1: FastAPI service — dispute data input → reason-code template → PDF output
- Week 2: Landing page + Gumroad/Lemon Squeezy payment; Reddit/FB seller groups me value-first posts
- Week 3: Pehle customers semi-manual handle karna (productized service), feedback se tool improve

## Architecture (Clean Architecture — strict)
- domain/        pure Python, zero framework imports (entities, evidence_policy)
- application/   use cases + ports (Protocols for repos/renderers)
- infrastructure/ Postgres repos, PDF renderer
- presentation/api/ FastAPI routers, API-key auth via Depends

## Code rules
- Type hints everywhere, async by default
- Pydantic v2 syntax only (model_config, field_validator)
- Protocols/ABCs for interfaces, DI via Depends or constructor
- logging, no print
- Stripe/Shopify API details: agar pakka na ho to "verify in docs" bolo, guess mat karo

## Working style
- Responses Roman Urdu me
- Code change se pehle approach explain karo
- Har step ke baad user output paste karega, phir agla step
- Existing code me changes: sirf before/after snippet, poori file nahi
- Interview-relevant points highlight karo

## Status
- [x] Project setup, venv (Python 3.12), fastapi/uvicorn/pydantic installed
- [x] domain/entities.py — DisputeReason, EvidenceType, EvidenceItem, Order, Dispute
- [x] domain/evidence_policy.py — assess() → EvidenceGap(missing, strength)
- [x] application/ports.py — DisputeRepository, EvidencePackRenderer Protocols
- [x] application/build_evidence_pack.py — BuildEvidencePackUseCase, DisputeNotFound
- [x] infrastructure/pdf_renderer.py — fpdf2, narrative sirf provided evidence claim karti hai
- [x] infrastructure/in_memory_repository.py — DATABASE_URL na ho to (dev/tests)
- [x] presentation/api/disputes.py — POST /disputes → PDF; gap X-Evidence-* headers me (PDF me nahi)
- [x] presentation/web/ — landing (/) + builder form (/app); GET /disputes/requirements (public)
- [x] tests/ (21; Postgres test sirf TEST_DATABASE_URL pe), mypy strict clean; form browser me Playwright se verify
- [x] infrastructure/postgres_repository.py — asyncpg, 2 tables, save() ek transaction; schema startup pe (no Alembic yet)
- [x] Evidence policy Stripe docs se verify (2026-10): duplicate/subscription/fraud fix, credit_not_processed add
- [x] Attachments: PNG/JPEG base64 JSON me, Pillow se verify (4MB, 10 max, pixel limit), PDF me exhibits, EXIF rotation fix
- [ ] (user) Payment: Lemon Squeezy/Gumroad product → CHECKOUT_URL
- [ ] (user) Contact email → CONTACT_EMAIL
- [x] Body size limit middleware (60MB → 413)
- [x] Dockerfile (non-root, $PORT, pip retries; asyncpg) — container + Postgres me verify; requirements.txt (prod) / requirements-dev.txt
- [x] scripts/new_api_key.py — customer ke liye key + env line
- [x] docs/outreach.md — Reddit/FB value-first post drafts
- [ ] (user) Hosting choose → deploy + managed Postgres (DATABASE_URL)
- [ ] (user) Outreach posting (docs/outreach.md)
- [ ] Payment webhook → auto API key (payment provider tay hone ke baad)
- [ ] Reasons abhi nahi: unrecognized, general, noncompliant (Stripe categories)

## Run
- `CHARGEBACK_API_KEYS="key:tenant" CHECKOUT_URL=... PACK_PRICE='$19' CONTACT_EMAIL=... .venv/bin/uvicorn main:app --reload`
- `.venv/bin/python -m pytest` · `.venv/bin/python -m mypy`
- Postgres local: `docker run -d --rm --name cbd-pg --network host -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=chargeback postgres:16-alpine -c port=55432`
  phir `DATABASE_URL=postgresql://postgres:devpass@127.0.0.1:55432/chargeback` (tests: TEST_DATABASE_URL)
- Is machine pe `docker run -p` port mapping timeout karti hai → `--network host` use karo
- `docker build -t chargeback-defense . && docker run -p 8000:8000 -e CHARGEBACK_API_KEYS=... chargeback-defense`
- Naya customer: `.venv/bin/python scripts/new_api_key.py <tenant-id>`

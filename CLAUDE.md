# Chargeback Defense Pack

## Goal
Small US online stores (Shopify/Stripe sellers) ke liye tool jo dispute/chargeback ka
evidence pack (PDF) banata hai taake merchant dispute jeet sake.
Target: **31 Oct 2026 se pehle launch** aur pehla paying customer. $19 = 1 dispute credit.

## FEATURE FREEZE (launch tak)
Product feature-complete hai. Sirf launch-readiness ka kaam karna hai: koi naya feature, refactor ya Phase 2/3 nahi.

## Launch decisions (tay ho chuke)
- Payment: **Gumroad**, $19 = 1 credit (product + `CHECKOUT_URL` user banayega)
- Fulfillment: **manual**. Gumroad sale → `scripts/admin.py create/add-credits` → 24 ghante me key email (docs/fulfillment.md)
- Refunds: unused credit 14 din me full; tool ki kharabi se PDF na bane to full; dispute outcome pe refund nahi
- Hosting: **Render** (Docker web service + managed Postgres), docs/deploy.md. Render settings/pricing guess mat karo: "verify in Render docs"
- Prod env: `APP_ENV=production`, `DATABASE_URL`, `CHECKOUT_URL`, `CONTACT_EMAIL`, `PACK_PRICE=$19`.
  `DEV_API_KEYS` / `DEV_CREDITS` production me kabhi set nahi karne

## ⚠️ Reminder: Render free Postgres expires 2026-11-28
Us din tak paid plan pe upgrade ya data migrate karna hai, warna customer accounts/keys/credits aur disputes
gum ho jayenge (upgrade/backup options: verify in Render docs). Expiry se ~1 hafta pehle (2026-11-21) action lo.

## Plan (launch)
1. [x] Tests + mypy; production-readiness check
2. [x] `APP_ENV=production` guard; docs/deploy.md; docs/fulfillment.md; refund policy
3. [x] (user) Gumroad product → `CHECKOUT_URL`; support email → `CONTACT_EMAIL`
4. [x] (user) Render deploy (docs/deploy.md) → smoke test green (2026-10-29)
5. [ ] (user) Outreach posting (docs/outreach.md) → pehla customer → manual fulfillment
6. Launch ke baad: feedback, phir Phase 2 (Gumroad webhook) / Phase 3

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
- [x] tests/ (45; Postgres + concurrency tests sirf TEST_DATABASE_URL pe), mypy strict clean; form browser me Playwright se verify
- [x] infrastructure/postgres_repository.py — asyncpg, 2 tables, save() ek transaction; schema startup pe (no Alembic yet)
- [x] Evidence policy Stripe docs se verify (2026-10): duplicate/subscription/fraud fix, credit_not_processed add
- [x] Attachments: PNG/JPEG base64 JSON me, Pillow se verify (4MB, 10 max, pixel limit), PDF me exhibits, EXIF rotation fix
- [x] (user) Payment: Gumroad product live ($19 = 1 credit) → CHECKOUT_URL=https://861109752920.gumroad.com/l/yibrtr
- [x] (user) Contact email → CONTACT_EMAIL=ahafeez791@gmail.com
- [x] Body size limit middleware (60MB → 413)
- [x] Dockerfile (non-root, $PORT, pip retries; asyncpg) — container + Postgres me verify; requirements.txt (prod) / requirements-dev.txt
- [x] Git repo (main)
- [x] Accounts + credits (Phase 1): keys DB me SHA-256 hash, 1 credit per new dispute, same dispute+order regenerate free,
      same dispute_id + alag order → 409, no credit → 402, credit sirf kamyab PDF pe; atomic charge (Postgres txn)
- [x] scripts/admin.py — create / add-credits / show / deactivate / activate (DATABASE_URL)
- [x] docs/outreach.md — Reddit/FB value-first post drafts
- [x] APP_ENV=production guard: DATABASE_URL/CHECKOUT_URL/CONTACT_EMAIL missing → startup fail (tests/test_startup_config.py)
- [x] docs/deploy.md: Render steps, env table, smoke test (locally prod mode + Postgres pe verify)
- [x] docs/fulfillment.md: Gumroad sale → admin script → email templates, refund policy; landing + /app pe "within 24 hours" + refund line
- [x] (user) Render deploy + managed Postgres → https://chargeback-defense.onrender.com; production smoke test pass
      (health, landing, admin create, PDF 200, free regenerate 200, no credit 402, wrong key 401, deactivate 401)
- [ ] (user) Outreach posting (docs/outreach.md)
- [ ] Phase 2 (launch ke baad): Gumroad webhook → scripts/admin create/add-credits automatic
- [ ] Phase 3: monthly plan, merchant dashboard, usage history (customers ke baad)
- [ ] Reasons abhi nahi: unrecognized, general, noncompliant (Stripe categories)

## Run
- Dev (no DB): `DEV_API_KEYS="key:tenant" DEV_CREDITS=100 CHECKOUT_URL=... PACK_PRICE='$19' CONTACT_EMAIL=... .venv/bin/uvicorn main:app --reload`
- Prod: `APP_ENV=production DATABASE_URL=... CHECKOUT_URL=... CONTACT_EMAIL=...` → keys sirf DB se; DEV_API_KEYS ignore (docs/deploy.md)
- `.venv/bin/python -m pytest` · `.venv/bin/python -m mypy`
- Postgres local: `docker run -d --rm --name cbd-pg --network host -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=chargeback postgres:16-alpine -c port=55432`
  phir `DATABASE_URL=postgresql://postgres:devpass@127.0.0.1:55432/chargeback` (tests: TEST_DATABASE_URL)
- Is machine pe `docker run -p` port mapping timeout karti hai → `--network host` use karo
- `docker build -t chargeback-defense . && docker run -p 8000:8000 -e DATABASE_URL=... chargeback-defense`
- Naya customer: `DATABASE_URL=... .venv/bin/python -m scripts.admin create <tenant-id> --credits 1`
  (Docker me: `docker exec <container> python -m scripts.admin ...`)

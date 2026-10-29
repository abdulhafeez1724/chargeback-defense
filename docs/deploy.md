# Deploy: Render (Docker web service + managed Postgres)

Jo cheez "verify in Render docs" likhi hai, Render dashboard / docs me check karein. Plans, pricing aur
UI labels badalte rehte hain, isliye yahan guess nahi kiya gaya.

## 0. Pehle se tayyar

- `main` branch pe tests + mypy green (`.venv/bin/python -m pytest`, `.venv/bin/python -m mypy`)
- Gumroad product ka checkout link (`CHECKOUT_URL`)
- Support email (`CONTACT_EMAIL`)
- Render account, GitHub account connected (repo private hai: Render ko is repo ka access dena hoga, verify in Render docs)

## 1. Postgres banayein

1. Render dashboard → **New → PostgreSQL**.
2. Name: `chargeback-db` (koi bhi). **Region** note karein: web service bhi isi region me banegi taake
   internal URL kaam kare.
3. Plan: free Postgres ki expiry/limits ho sakti hain. Paying customers ka data is me hoga, isliye plan
   chunne se pehle limits **verify in Render docs**.
4. Banne ke baad database page pe do URLs milenge (verify exact labels in Render docs):
   - **Internal Database URL**: web service ke `DATABASE_URL` ke liye
   - **External Database URL**: laptop se `scripts/admin.py` chalane ke liye (docs/fulfillment.md)
5. External access ke liye IP allow-list / access control setting ho sakti hai. Apna IP allow karein
   (verify in Render docs).

Schema khud banta hai: app aur `scripts/admin.py` dono startup pe `CREATE TABLE IF NOT EXISTS` chalate hain.
Alag migration step nahi hai.

## 2. Web service banayein

1. **New → Web Service** → GitHub repo `abdulhafeez1724/chargeback-defense` → branch `main`.
2. Runtime / language: **Docker** (root me `Dockerfile` hai; Dockerfile path default `./Dockerfile`).
3. **Region**: Postgres wala hi.
4. Instance type: free instance idle hone pe sleep kar sakta hai (pehli request slow). Limits
   **verify in Render docs**.
5. **Health Check Path**: `/health`
6. Start command / port: kuch set na karein. Dockerfile ka `CMD` `$PORT` pe sunta hai jo Render deta hai.
   `PORT` khud set **mat** karein (Render ka default port aur detection, verify in Render docs).
7. Environment variables: neeche wali table.
8. Auto-deploy on push to `main`: on rakhein (default, verify in Render docs).

## 3. Environment variables

| Variable | Value | Zaroori | Note |
|---|---|---|---|
| `APP_ENV` | `production` | ✅ | Exact lowercase `production`. Is ke saath neeche ke 3 vars missing hon to app start nahi hogi (fail fast). |
| `DATABASE_URL` | Render Postgres ka **Internal** Database URL | ✅ | Set ho to keys/credits sirf DB se. |
| `CHECKOUT_URL` | Gumroad product link | ✅ | Landing page ka "Buy a pack" button. |
| `CONTACT_EMAIL` | support email | ✅ | Landing page footer. |
| `PACK_PRICE` | `$19` | recommended | Na ho to bhi default `$19`. |
| `DEV_API_KEYS` | — | ❌ **set mat karein** | Sirf local dev. `DATABASE_URL` ke saath ignore hota hai, phir bhi production me na rakhein. |
| `DEV_CREDITS` | — | ❌ **set mat karein** | Sirf local dev. |
| `PORT` | — | ❌ | Render khud deta hai. |

Landing page ki values process start pe cache hoti hain. `CHECKOUT_URL` / `CONTACT_EMAIL` badlein to service
restart / redeploy hona chahiye (env change pe Render redeploy karta hai ya nahi, verify in Render docs).

## 4. Deploy check (logs)

Deploy logs me yeh dikhna chahiye:

```
postgres pool ready, schema ensured
Uvicorn running on http://0.0.0.0:<port>
```

Agar yeh dikhe to env var missing hai. Table dobara check karein:

```
RuntimeError: APP_ENV=production but required env vars are missing: ...
Application startup failed. Exiting.
```

Yeh warning production me **kabhi nahi** aani chahiye (matlab `DATABASE_URL` nahi mila):

```
DATABASE_URL not set — using in-memory storage (lost on restart)
```

## 5. Post-deploy smoke test

Laptop se, repo folder me. Placeholders bharein:

```bash
export BASE=https://<your-service>.onrender.com
export DATABASE_URL='<External Database URL>'   # SSL error aaye to aakhir me ?sslmode=require lagayein
```

**5.1 Health + landing page**

```bash
curl -fsS $BASE/health                       # → {"status":"ok"}
curl -fsS $BASE/ | grep -o 'href="[^"]*gumroad[^"]*"'   # Gumroad link dikhna chahiye
curl -fsS $BASE/ | grep -c 'within 24 hours'            # → 1
curl -fsS $BASE/ | grep -cE '\{\{|example\.com|#pricing' # → 0 (koi placeholder/default nahi)
```

Browser me `$BASE/` bhi kholein: Buy button Gumroad pe jaye, contact email sahi ho.

**5.2 Test account banayein (admin script → Render Postgres)**

```bash
.venv/bin/python -m scripts.admin create smoke-test --credits 1
# → API key (customer ko bhejein — dobara nahi dikhegi): cbd_...
export KEY='cbd_...'
curl -fsS -H "X-API-Key: $KEY" $BASE/account   # → {"tenant_id":"smoke-test","credits":1}
```

**5.3 Dispute submit → PDF download**

```bash
cat > /tmp/smoke-dispute.json <<'EOF'
{
  "dispute_id": "dp_smoke_1",
  "reason": "product_not_received",
  "order": {
    "order_id": "1001",
    "amount": "49.99",
    "currency": "USD",
    "placed_at": "2026-10-01T12:00:00Z",
    "customer_email": "buyer@example.com",
    "billing_address": "1 Main St, Austin, TX",
    "shipping_address": "1 Main St, Austin, TX"
  },
  "evidence": [
    {"type": "tracking", "summary": "USPS 9400 1000 0000 0000 0000 00 - delivered Oct 4"},
    {"type": "delivery_proof", "summary": "Carrier delivery scan with photo"}
  ]
}
EOF

curl -sS -D - -o /tmp/smoke-pack.pdf -X POST $BASE/disputes \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  --data @/tmp/smoke-dispute.json
# → HTTP 200, content-type: application/pdf, x-credits-remaining: 0, x-evidence-strength: ...

head -c 5 /tmp/smoke-pack.pdf   # → %PDF-
```

PDF kholke dekhein: dispute/order details aur dono evidence items hon.

**5.4 Credits ka rule**

```bash
# Wahi dispute + wahi order dobara → free regenerate, 200, credits 0 hi rahen
curl -sS -o /dev/null -w '%{http_code}\n' -X POST $BASE/disputes \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" --data @/tmp/smoke-dispute.json   # → 200

# Naya dispute, credit khatam → 402
sed 's/dp_smoke_1/dp_smoke_2/' /tmp/smoke-dispute.json > /tmp/smoke-dispute-2.json
curl -sS -o /dev/null -w '%{http_code}\n' -X POST $BASE/disputes \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" --data @/tmp/smoke-dispute-2.json # → 402

# Ghalat key → 401
curl -sS -o /dev/null -w '%{http_code}\n' -H "X-API-Key: wrong" $BASE/account          # → 401
```

**5.5 Browser form (optional)**

`$BASE/app` kholein, key daalein, `dp_smoke_1` wali details bhar ke submit karein. Same dispute hai isliye free
regenerate hoga aur PDF download hona chahiye.

**5.6 Cleanup**

```bash
.venv/bin/python -m scripts.admin deactivate smoke-test
curl -sS -o /dev/null -w '%{http_code}\n' -H "X-API-Key: $KEY" $BASE/account   # → 401
rm /tmp/smoke-dispute*.json /tmp/smoke-pack.pdf
unset DATABASE_URL KEY
```

Sab green → launch ready. Koi step fail ho to Render logs dekhein. Pichle deploy pe rollback ka option
dashboard me hota hai (verify in Render docs).

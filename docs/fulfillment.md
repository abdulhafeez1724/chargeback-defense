# Fulfillment: Gumroad sale → API key (manual, 24 ghante ke andar)

Landing page wada karta hai: **"API key emailed within 24 hours of purchase"**. Din me kam az kam 2 dafa
Gumroad sales check karein. Har sale pe seller ko email aati hai ya nahi, yeh notification setting
verify in Gumroad docs.

$19 = 1 credit = 1 naya dispute. Same dispute ID + same order dobara generate karna free hai.

## 0. Ek dafa ka setup

**Customer record (private, repo me NAHI).** Buyer emails PII hain, isliye Google Sheet ya local file me rakhein:

| Date | Gumroad sale ID | Buyer email | tenant-id | Credits bought | Key sent at |
|---|---|---|---|---|---|

API key khud kabhi record me na likhein. DB me sirf us ka hash hai, aur key sirf email me jaati hai.

**Admin script chalane ka tareeqa chunein.** Dono me se jo available ho:

**A. Laptop se (External Database URL)**
- Render Postgres page se **External Database URL** lein (deploy.md step 1).
- Agar Postgres pe IP allow-list / access control hai to apna current IP allow karein (verify in Render docs).
- URL shell history me na jaye, is liye `read -s` se daalein:

```bash
cd ~/chargeback-defense
read -rsp 'External DATABASE_URL: ' DATABASE_URL; echo; export DATABASE_URL
.venv/bin/python -m scripts.admin show some-tenant   # connection test → "unknown tenant: ..." theek hai
```

SSL / connection error aaye to URL ke aakhir me `?sslmode=require` lagayein. Kaam khatam ho to `unset DATABASE_URL`.

**B. Render Shell (web service ke container ke andar)**
- Dashboard → web service → **Shell** (yeh feature har instance type pe available hai ya nahi, verify in
  Render docs. Free instance pe shayad na mile).
- Container me `DATABASE_URL` (internal) pehle se set hai aur working dir `/app` hai:

```bash
python -m scripts.admin show some-tenant
```

Neeche commands A ke hisaab se likhi hain (`.venv/bin/python -m scripts.admin ...`). B me sirf
`python -m scripts.admin ...` likhein.

## 1. Sale email aayi: checklist

1. Gumroad sale se yeh note karein: **buyer email**, **sale ID**, **quantity** (agar product pe quantity
   on hai, credits = quantity; Gumroad email me quantity dikhti hai ya nahi, verify in Gumroad docs).
2. Customer record me buyer email dhoondein:
   - **Naya customer** → step 2
   - **Purana customer** (pehle se tenant-id hai) → step 3
3. Agar sale refunded / disputed dikhe to key mat bhejein.

## 2. Naya customer: `create`

tenant-id ka format: lowercase, digits, dashes, 3–40 chars. Email ke domain ya store ke naam se banayein,
jaise `jane@acmestore.com` → `acmestore`. Gmail jaisi email ho to `jane-smith` jaisa naam.

```bash
.venv/bin/python -m scripts.admin show acmestore        # → "unknown tenant" = naam free hai
.venv/bin/python -m scripts.admin create acmestore --credits 1
# Created acmestore with 1 credit(s).
# API key (customer ko bhejein — dobara nahi dikhegi): cbd_...
```

- Key **sirf ek dafa** dikhti hai. Seedha email template (neeche) me paste karein.
- `tenant 'acmestore' already exists` aaye to doosra naam lein (`acmestore-2`).
- Record me row add karein (key ke baghair), phir **Email A** bhejein.

## 3. Purana customer: `add-credits`

```bash
.venv/bin/python -m scripts.admin add-credits acmestore 1
# acmestore: +1 → 2 credit(s)
```

Purani key hi chalti rahegi, nayi key nahi banti. Record update karein, phir **Email B** bhejein.

## 4. Edge cases

**Customer ki key kho gayi.** Key reset ka command nahi hai (feature freeze). Workaround:

```bash
.venv/bin/python -m scripts.admin show acmestore                 # → N credit(s)
.venv/bin/python -m scripts.admin create acmestore-2 --credits N # N >= 1 hona chahiye
.venv/bin/python -m scripts.admin deactivate acmestore
```

Nayi key bhejein (Email A). Note: purane tenant ke disputes ka free regenerate naye tenant pe nahi milega.
Agar N = 0 ho to `create` 0 credits nahi leta. Faisla aap ka hai: 1 goodwill credit dein ya naya pack khareedne ka kahein.

**Refund maanga.** Policy (landing page pe bhi yahi likhi hai):

| Situation | Refund |
|---|---|
| Credit use nahi hua, purchase ko 14 din se kam hue | ✅ Full refund |
| PDF tool ki kharabi ki wajah se generate nahi ho saki | ✅ Full refund |
| Dispute haar gaye / outcome pasand nahi aaya | ❌ Nahi (faisla card issuer karta hai) |

1. `show <tenant>` se credits dekhein. Credits = purchased credits matlab use nahi hua. Gumroad me purchase
   date check karein (14 din).
2. Gumroad me refund karein.
3. Jitne credits refund hue, utne account me nahi rehne chahiye. Minus credits ka command nahi hai,
   isliye agar account me baaki sab credits isi purchase ke the to `deactivate` karein. Agar purane
   unused credits bhi hain to `deactivate` + nayi key wala workaround (upar) use karein, refund ke baad
   jitne credits bachte hain utne dein.

**PDF generate nahi hui.** Credit sirf kamyab PDF pe katta hai, isliye fail hone pe credit nahi gaya.
`show` se confirm karein. Error details maangein (screenshot / error message) aur Render logs dekhein.
Fix ho jaye to customer apna credit use kar sakta hai. Woh refund chahe to policy ke mutabiq full refund dein.

**Galat customer ko credit chala gaya.** Minus credits ka command nahi hai. Agar unhon ne abhi use nahi
kiya to `deactivate` karein, sahi account ko `add-credits` dein, aur galti wale customer se baat karein.

## 5. Email templates

`<APP_URL>` = Render service URL (ya custom domain). `CONTACT_EMAIL` wale address se bhejein.
API key subject line me kabhi na daalein.

### Email A: naya customer

**Subject:** Your Chargeback Defense Pack is ready

> Hi <first name>,
>
> Thanks for your purchase! Your account is set up with **<N> credit(s)**. One credit builds the
> evidence pack for one new dispute.
>
> **Your API key:**
> `<cbd_...>`
>
> Keep this key private. It works like a password for your account.
>
> **How to build your pack**
> 1. Open <APP_URL>/app
> 2. Paste your API key, pick the dispute reason, and enter the order details and the evidence you have
>    (tracking, delivery proof, customer messages, screenshots).
> 3. Download the PDF. Before submitting, check the missing-evidence list. If something is missing
>    (for example proof of delivery), gather it first.
> 4. Upload the PDF in your Stripe or Shopify dispute response before the response deadline shown there.
>
> Need to fix a typo? Re-submitting the **same dispute ID with the same order** regenerates the PDF for
> free. A different dispute uses a new credit.
>
> This tool organizes your evidence. It is not legal advice and cannot guarantee a dispute outcome.
> The card issuer makes the final decision.
>
> Refunds: full refund for an unused credit within 14 days, or if the PDF can't be generated due to a
> problem with the tool. No refunds based on the dispute outcome.
>
> Questions or problems? Just reply to this email.
>
> <your name>
> Chargeback Defense Pack

### Email B: purana customer, aur credits

**Subject:** Credits added to your Chargeback Defense Pack account

> Hi <first name>,
>
> Thanks for buying again! I've added **<N> credit(s)**. You now have **<total> credit(s)**.
> Keep using the same API key at <APP_URL>/app.
>
> Lost your key? Reply to this email and I'll send you a new one.
>
> <your name>

## 6. Bhejne ke baad

- Record me "Key sent at" bharein.
- Pehle kuch customers se 2–3 din baad pochhein: pack kaisa laga, kya missing tha? Yeh feedback Week 3 ke liye hai.
- `DATABASE_URL` unset karein / terminal band karein.

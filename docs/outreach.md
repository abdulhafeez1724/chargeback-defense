# Outreach drafts (Week 2)

Posting se pehle:
- Har subreddit/group ke self-promotion rules parhein. Kai jagah link sirf comments me ya bilkul allowed nahi.
- Pehle 1–2 hafte sirf madad karein (dispute wale sawalon ke jawab), link na daalein.
- Stripe ke deadlines/fees jaisi specific baatein post se pehle Stripe docs me verify karein.
- Koi win-rate ya "guaranteed" claim nahi.

---

## Post 1: Guide (r/shopify, r/ecommerce, FB seller groups)

**Title:** What evidence to include for each chargeback reason (small-store checklist)

I've been digging into how disputes work for small stores. The biggest mistake I see is sending the
same generic evidence for every dispute. The issuer is answering one question, and that question
depends on the reason code. Here's a checklist by reason:

**"Fraudulent" / unauthorized**
The question: did the real cardholder place this order?
- AVS (address) and CVC check results from your payment processor
- Customer IP address and rough location, if it matches the billing area
- Proof of delivery to the billing/shipping address on the order
- Any past orders from the same customer that weren't disputed

**"Product not received"**
The question: did it actually arrive?
- Tracking number with carrier and full tracking history
- Delivery confirmation (scan, photo, or signature if you have it)
- The shipping address the customer entered at checkout

**"Not as described"**
The question: did they get what the listing said?
- Screenshot of the product page as it looked when they ordered
- Your refund/return policy and where it's shown at checkout
- Emails or chats where you offered a return or fix

**"Subscription canceled"**
- Your cancellation terms and proof the customer agreed to them
- When and how they could have canceled, and that the charge came before any cancellation

**"Refund / credit not processed"** (they say they returned it and got no refund)
- Your refund/return policy and where it's shown at checkout
- Whether the return actually arrived (return tracking), and its condition if that matters under your policy
- Emails where you explained the refund decision

**"Duplicate"**
- A separate receipt for the other charge, showing it was a different order
- Shipping labels or tracking for both orders

**General tips**
- Lead with a short summary: the reason, your answer, and the evidence that proves it.
- Only claim what you can prove. "Delivered" without delivery proof weakens your whole response.
- Screenshots beat descriptions. Label them (Exhibit 1, Exhibit 2…) and refer to them in the summary.
- Submit well before the deadline (check the exact date in your Stripe/Shopify dashboard).

Happy to answer questions about a specific dispute (remove personal details first).

> Link na daalein. Agar koi pooche "is ke liye koi tool hai?", tab comment me link dein.

---

## Post 2: Short comment template (for "I got a chargeback, what do I do?" threads)

Sorry, that's stressful. First check the **reason code** in your dashboard, because the evidence you need
depends on it. For [reason], the key things are [2–3 items from the checklist above]. Put a short
summary on top and attach screenshots, labeled as exhibits. Also: don't claim anything you can't
show proof for. If you want, I built a small tool that turns order details plus screenshots into an
organized PDF and tells you what's missing: [link]. You can also just follow the checklist by hand.

---

## Post 3: Soft launch (only where self-promo is allowed, e.g. "Feedback Friday" threads)

**Title:** I built a small tool that turns your order data into a chargeback evidence PDF. Feedback wanted.

Small stores lose disputes they should win, often because the response is disorganized or
missing one key piece of proof. So I built a simple builder: pick the dispute reason, enter the
order, add your evidence and screenshots. It gives you a clean PDF with a summary written for that
reason, plus a checklist of what you're still missing before you submit.

It's $19 per pack, and the first few people get one free in exchange for honest feedback.
It's not legal advice and can't guarantee a result, since the issuer decides. [link]

What would make this more useful for you?

---

## DM reply (someone asks for help)

Thanks for reaching out! Send me (1) the dispute reason, (2) the order date and amount, and
(3) what evidence you have (tracking, delivery photo, emails, etc.). Remove the customer's card
details. I'll tell you what's missing and send you the PDF pack.

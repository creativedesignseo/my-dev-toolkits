# Specialist Agent 03 — Payments & Checkout Flow (CRITICAL)

[Inject `_shared-header.md` with N=3, AREA_NAME=payments, AREA_PREFIX=PAY]

## Your mission — the most important of the audit

Audit the **end-to-end payment flow** of {{PROJECT_NAME}} using {{payments_provider}}. From the moment the user clicks "Buy now" until the access is granted (or denied), every step must be inspected for security, correctness, and idempotency.

This is the area where real money is lost. Be paranoid.

## Provider-specific context

Payments provider detected: **{{payments_provider}}**

- If `stripe`: focus on Checkout Sessions, webhooks with `constructEvent`, idempotency keys, `payment_intent.*` events, `charge.refunded`, `charge.dispute.created`.
- If `paddle`: focus on Paddle Billing API, webhooks with HMAC signature, `transaction.completed`, alerts.
- If `lemonsqueezy`: focus on hosted checkout, webhook signing, signatures.
- If `bizum` / `redsys`: focus on TPV integration, request signing, callback verification. Bizum without a real PSP integration is a CRITICAL finding by itself.
- If `none` detected but the project handles money: that's also a CRITICAL finding.

## Investigation checklist

### A. The "Buy now" button
1. Find every place in the frontend where a checkout is initiated. Common patterns: `handleBuy`, `handleCheckout`, `handlePayment`, calls to `loadStripe`, `createCheckoutSession`, etc.
2. Verify the button:
   - Disables itself during processing
   - Prevents double-clicks (state flag, refs, idempotency keys)
   - Redirects unauthenticated users to login with a `state.from` to return after
   - Shows the same price that's sent to the backend (or, better, sends NO price and lets backend compute)
   - Has appropriate ARIA labels (`aria-busy`, `aria-disabled`)
3. Look for mobile sticky CTA variants. If they exist, verify they have the same protections.

### B. Payment modal / page
1. Locate the payment modal/page UI (look for `PaymentModal`, `CheckoutModal`, `<Modal>` with payment content).
2. Check:
   - Available methods displayed correctly (card, wallet balance, hybrid)
   - Wallet balance shown matches reality
   - Insufficient balance blocks the wallet option
   - Trust signals: card logos (Visa/MC/Amex), padlock, "secured by {{provider}}" wording
   - Order summary: what's being bought, for how much, refund policy
   - Responsive on mobile (no overflow, scrollable if needed)

### C. Server-side checkout session creation
For each serverless function that creates a checkout session, audit line-by-line:

1. **Auth:** Is the user authenticated (JWT verified)? If not, this is a CRITICAL finding.
2. **userId:** Is it from the JWT, or trusted from the request body?
3. **amount:** Is it computed server-side from DB lookup, or trusted from the body? **If from body → CRITICAL.**
4. **Item/group/product ID:** Is it validated (exists, is available, has stock, user is allowed to buy)?
5. **Duplicate purchase check:** Does the function verify the user isn't already a member / hasn't already bought?
6. **Currency, decimals:** Is `unit_amount` correctly in cents (or smallest unit)? Any rounding bugs?
7. **Metadata:** What's in `metadata`? Is anything client-controlled that the webhook will trust?
8. **success_url / cancel_url:** Are they hardcoded by environment, or derived from `event.headers.origin`? (Origin-based URLs are vulnerable to phishing.)
9. **Provider SDK initialization:** Is `apiVersion` pinned? (Untracked drift is bad.)
10. **Error handling:** Are errors logged server-side, or leaked to the client?

### D. Webhook (CRITICAL — every line)
Locate the webhook function. Audit:

1. **Signature verification:** Is it actually done, with the correct secret env var?
2. **Raw body reading:** Is the request body read as the raw bytes (Netlify/Vercel sometimes auto-decode)? Look for `isBase64Encoded` handling.
3. **Idempotency:** Is there a `stripe_events_processed` (or equivalent) table with the event ID as a unique key? If not → CRITICAL.
4. **Events handled:** Which event types are processed? Should at minimum include:
   - `checkout.session.completed` / `transaction.completed`
   - `payment_intent.payment_failed` / failure events
   - `charge.refunded` / refund events
   - `charge.dispute.created` / chargeback events
5. **Fulfillment logic:**
   - Is fulfillment idempotent?
   - Is the membership/access granted SOLELY based on the webhook (not on the user returning to `success_url`)?
   - Does the webhook write to DB in an atomic transaction (RPC), or in multiple non-transactional steps?
6. **Status code on error:** If the webhook fails, does it return 5xx (so the provider retries) or 2xx (silently losing the event)?
7. **Logging:** Does it leak PII (emails, full metadata, stack traces) to a `debug_logs` table or stdout?

### E. Wallet / balance flow (if applicable)
1. How is the wallet topped up? Verify it's only via webhook (not via a direct frontend RPC call).
2. How is balance debited on purchase? Is it atomic (`SELECT ... FOR UPDATE`)?
3. Can the balance go negative?
4. Concurrency: two purchases at the same time — race condition?
5. Are debug routes / dev-only top-up buttons present in production?

### F. Hybrid payment (wallet + card, if applicable)
1. When is the wallet debited — before or after the card payment confirms?
2. If the user cancels the card payment, is the wallet refunded automatically?
3. Is the `walletDeducted` value computed by the client (manipulable) or by the server?
4. Is the operation atomic via webhook?

### G. Antifraud checklist
Test each of these against the code. For each, answer "protected: yes/partial/no" and cite the file:line where applicable.

1. Same user joins the same group/product twice → UNIQUE constraint? Pre-purchase check?
2. Pay for a full / sold-out item → server-side stock check?
3. Pay for a nonexistent item → existence check?
4. Manipulate `itemId` in DevTools → server validates?
5. Manipulate `amount` in DevTools → server recalculates?
6. Pay using another `userId` → JWT-bound, not body-bound?
7. Get access by visiting `success_url` without paying → access ONLY from webhook?
8. Replay the webhook → idempotent?
9. Manual / Bizum / offline payment path → is there a verification?
10. Rate limit on checkout creation → can someone spam your Stripe account?

## What to deliver

The most important agent. Give it the full ~1500 words. Include:

- A verdict: ready / launch-with-caveats / blocked
- A 22-point pre-production checklist marked ✅/❌
- The 10 most critical findings ranked
- A phased fix roadmap focused on the payment module

## Don't

- Don't audit general security outside the payment flow (Agent 2).
- Don't audit RLS policies on non-payment tables (Agent 4).
- Don't audit UI consistency outside the checkout (Agent 6).

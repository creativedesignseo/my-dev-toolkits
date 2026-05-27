# Example output — `AUDIT_REPORT.md` from a real run

> This is an **anonymized excerpt** of the audit report produced for a real subscription-sharing SaaS that was about to launch with real payments. Project name redacted to `acme-sub`. The score and findings are real — the implementation details are real too.

---

# Production Readiness Audit — acme-sub

> **Audit date:** 2026-05-25T14:32:00Z
> **Mode:** full
> **Git commit:** `6ab5df0`
> **Stack:** React 18 + Vite 6 + Supabase + Stripe + Netlify Functions + Tailwind 3

```
╔══════════════════════════════════════════════════════════╗
║  PRODUCTION READINESS REPORT — acme-sub                  ║
║  Mode: full                          2026-05-25T14:32Z   ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Score:  █░░░░░░░░░░░░░░░░░░░░░  8/100  🛑 BLOCKED       ║
║                                                          ║
║  Security      ░░░░░░░░░░  0/25                          ║
║  Payments      ░░░░░░░░░░  0/20                          ║
║  Data layer    █░░░░░░░░░  2/15                          ║
║  UI/UX         ███░░░░░░░  3/10                          ║
║  QA            ██░░░░░░░░  2/10                          ║
║  Admin         █░░░░░░░░░  1/5                           ║
║  SEO/Perf      ░░░░░░░░░░  0/5                           ║
║  Deploy        ░░░░░░░░░░  0/5                           ║
║  Stack         ░░░░░░░░░░  0/3                           ║
║  Legal         ░░░░░░░░░░  0/2                           ║
║                                                          ║
║  Findings: 7 critical · 25 high · 40 medium · 18 low     ║
║                                                          ║
║  Top blockers (P0):                                      ║
║   1. SEC-001 Wallet top-up RPC callable from frontend    ║
║   2. SEC-002 Credentials in plain text + RLS open        ║
║   3. SEC-003 Self-elevation to super_admin via RLS gap   ║
║   4. PAY-015 amount accepted from client body            ║
║   5. PAY-034 Manual-payment.js endpoint unauthenticated  ║
║   6. SEC-007 test-db function exposes service_role key   ║
║   7. DB-008 memberships INSERT bypass                    ║
║                                                          ║
║  Full report: ./AUDIT_REPORT.md                          ║
╚══════════════════════════════════════════════════════════╝
```

## Executive summary

acme-sub is a SaaS for sharing digital subscriptions (Netflix, Spotify, etc.) built on React + Vite + Supabase + Stripe + Netlify Functions. The scaffolding is functional but the trust boundary between client and server is misplaced in every layer: critical business logic (price calculation, identity assertion, wallet balance) is executed or trusted from the browser, and Supabase RLS policies are so permissive that any user with DevTools knowledge can: self-elevate to super_admin with one UPDATE, top up their wallet infinitely via a SECURITY DEFINER RPC, read the plain-text credentials of every shared account in the system, pay 0.01€ for any subscription by manipulating the `amount` in the checkout request, and create paid memberships with a direct INSERT bypassing payment entirely. There are at least 7 independent fraud vectors and one catastrophic third-party credentials leak. Combined with zero tests, zero TypeScript, zero CI/CD, no Error Boundaries, and a README that misstates the stack version, the project is best described as an advanced prototype, not a production-ready SaaS handling real money.

**Verdict: 🛑 BLOCKED — DO NOT LAUNCH.** Phase 0 of the roadmap (1-3 days of work) is inaplazable.

---

## Critical findings (P0) — must fix before launch

### SEC-001 — Wallet top-up RPC callable from any authenticated user

- **Severity:** 🔴 Critical
- **Area:** security
- **Location:** `database/wallets.sql:63-91`, used at `src/pages/WalletPage.jsx:44-60`
- **Description:** The function `handle_wallet_topup(p_user_id, p_amount, p_stripe_id, p_description)` is marked `SECURITY DEFINER` and has no REVOKE. Any authenticated user can call it from the browser console:
  ```js
  supabase.rpc('handle_wallet_topup', {
    p_user_id: '<own-uid>', p_amount: 1e9,
    p_stripe_id: 'fake', p_description: 'hack'
  })
  ```
  The function adds the amount to `wallets.balance` and creates a transaction record. Result: arbitrary infinite balance.
- **Impact:** Total loss of revenue path. Attacker pays for subscriptions with imaginary money.
- **Recommendation:** `REVOKE EXECUTE ON FUNCTION handle_wallet_topup FROM PUBLIC, anon, authenticated; GRANT EXECUTE TO service_role;` Only the Stripe webhook (using service-role key) should be able to call it.

### SEC-002 — Plain-text third-party credentials, RLS reads them publicly

- **Severity:** 🔴 Critical
- **Area:** security
- **Location:** `database/schema.sql:73-75` (columns `credentials_login`, `credentials_password`); `database/rls_policies.sql:41-45` (policy `auth_read_groups` with `USING (true)`)
- **Description:** Netflix / Spotify / HBO credentials are stored as plain text in `subscription_groups`. The policy `auth_read_groups` allows any authenticated user to `SELECT *` over the whole table, exposing all credentials regardless of group membership. The `visibility_fix.sql` patch even extends this to anonymous users for "public" groups.
- **Impact:** Mass leak of third-party account credentials. Reputational disaster + GDPR liability + likely violation of Netflix/Spotify/HBO ToS.
- **Recommendation:** (1) Move credentials to a separate table `group_credentials` with no SELECT policy. (2) Encrypt at rest using `pgsodium` or Supabase Vault. (3) Read only via the existing `get_group_credentials(uuid)` RPC, which already checks paid membership.

### SEC-003 — Self-elevation to super_admin via RLS gap

- **Severity:** 🔴 Critical
- **Area:** security
- **Location:** `database/schema.sql:151-154`
- **Description:** The UPDATE policy on `profiles` is `auth.uid() = id` with no `WITH CHECK` constraining columns. Any user can run:
  ```js
  supabase.from('profiles').update({ role: 'super_admin' }).eq('id', user.id)
  ```
  and gain full admin access immediately.
- **Impact:** Complete administrative compromise. Once super_admin, the attacker can ban users, modify all data, read all credentials (via admin endpoints).
- **Recommendation:** Use a trigger that rejects role changes by the user itself, OR move `role` to a separate table `user_roles` with strict RLS.

[... 4 more critical findings ...]

---

## High findings (P1) — must fix in first sprint after launch

[... 25 high findings ...]

---

## Phased remediation roadmap

### Phase 0 — Stop the bleed (1-3 days, BLOCKING)

> Must be completed before accepting any real payment or PII.

1. Delete `netlify/functions/test-db.js` and `netlify/functions/manual-payment.js` (resolves SEC-001, SEC-007, ADM-002).
2. Remove `X-Robots-Tag: noindex` from `netlify.toml` (resolves SEO-001).
3. Add SPA redirect `/* → /index.html 200` to `netlify.toml` (resolves DEPLOY-003).
4. Add security headers (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy) to `netlify.toml`.
5. Document missing secrets in `.env.example` (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `SUPABASE_SERVICE_ROLE_KEY`).
6. SQL hardening (see Appendix C):
   - `REVOKE EXECUTE` on financial RPCs
   - Trigger to prevent role self-edit
   - Rewrite `memberships FOR ALL` policy
   - `UNIQUE INDEX` on `payment_transactions.stripe_payment_intent_id`
   - `CHECK (slots_occupied <= max_slots)`
7. Serverless function hardening:
   - JWT required in `create-checkout`, `create-group-checkout`, `create-topup-session`
   - `userId` from JWT, never from body
   - Recalculate `amount` server-side from DB lookup
   - Pin `apiVersion` in `new Stripe(...)`
8. Webhook hardening:
   - Idempotency via `stripe_events_processed` table
   - Handle `event.isBase64Encoded` (Netlify)
   - Add `payment_intent.payment_failed`, `charge.refunded`, `charge.dispute.created`
   - Return 5xx on transient errors
9. Runtime fixes:
   - Fix `DashboardPage.jsx:5` commented `LogIn` import (resolves QA-010 — guaranteed white screen)
   - Fix `LoginPage.jsx:119` Tailwind typo `hover:number-700` → `hover:text-primary-700`
   - Fix `useWallet` to return `balance: balance ?? 0`

### Phase 1 — Stabilization (1-2 weeks)

[... 10 numbered actions ...]

### Phase 2 — Production quality (3-4 weeks)

[... 12 numbered actions ...]

### Phase 3 — Modernization (3-6 months)

[... 8 numbered actions ...]

---

## Per-area details

[... collapsible sections with each specialist's full report ...]

---

## Appendix C — SQL hardening snippets

```sql
BEGIN;

-- 1. Block self-elevation
DROP POLICY "Usuarios actualizan su propio perfil" ON profiles;
CREATE POLICY "Usuarios actualizan campos seguros de su perfil"
  ON profiles FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

CREATE OR REPLACE FUNCTION public.prevent_role_self_edit()
RETURNS TRIGGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
    IF OLD.role IS DISTINCT FROM NEW.role
       AND NOT EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'super_admin') THEN
        RAISE EXCEPTION 'Cannot modify role of a profile';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_profile_safe_update
  BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION public.prevent_role_self_edit();

-- 2. Revoke financial RPCs from authenticated
REVOKE EXECUTE ON FUNCTION public.handle_wallet_topup(UUID, DECIMAL, TEXT, TEXT)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.handle_wallet_topup(UUID, DECIMAL, TEXT, TEXT)
  TO service_role;

-- 3. Idempotency
ALTER TABLE payment_transactions
  ADD CONSTRAINT uq_payment_stripe_pi UNIQUE (stripe_payment_intent_id);

CREATE TABLE IF NOT EXISTS public.stripe_events_processed (
    event_id TEXT PRIMARY KEY,
    processed_at TIMESTAMPTZ DEFAULT now()
);

-- [... more snippets ...]

COMMIT;
```

---

*Generated by `saas-audit` skill v0.1.0 — read-only audit. To apply fixes, use `/saas-audit --fix` (v0.2 — coming soon).*

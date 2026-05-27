# Specialist Agent 09 — Deploy, Environment Variables & Production Readiness

[Inject `_shared-header.md` with N=9, AREA_NAME=deploy, AREA_PREFIX=DEPLOY]

## Your mission

Verify the project is correctly configured to be built, deployed, and operated in production. Find every gap between "works on my machine" and "works in production safely".

## Investigation checklist

### A. Environment variables
1. Read `.env.example`. List every variable it documents.
2. Grep the entire codebase for `process.env.X` and `import.meta.env.VITE_X`. List every variable actually used.
3. Build a comparison table: variable | used in (files) | in .env.example? | public (VITE_/NEXT_PUBLIC_) or secret? | issue.
4. Flag:
   - Variables used but not in `.env.example`
   - Variables in `.env.example` but unused (e.g., `VITE_APP_URL` ghost)
   - Secret-looking variables with public prefix (`VITE_STRIPE_SECRET_KEY` would be catastrophic)
   - Missing critical secrets for the detected stack:
     - {{payments_provider}} secret key
     - {{payments_provider}} webhook secret
     - {{backend}} service role / admin key
     - Auth secrets

### B. Hosting configuration
For {{hosting}}:

If **netlify**:
1. `netlify.toml` — `[build]` correct? `command`, `publish`, `functions`?
2. SPA redirect — does it have `[[redirects]] from = "/*" to = "/index.html" status = 200`? Or a `public/_redirects` file?
3. Security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy) present?
4. `X-Robots-Tag: noindex` — flag as critical pre-prod blocker if present.
5. Context-specific env vars (`[context.production]`, `[context.deploy-preview]`)?

If **vercel**:
1. `vercel.json` — correct framework, output dir, regions?
2. Headers and rewrites?
3. Edge config?

If **other / unknown**: document the gap.

### C. Build and lint
1. `package.json` scripts: `dev`, `build`, `preview`, `lint`, `test`, `format`, `typecheck`?
2. `eslint.config.{js,mjs}` exists? Or older `.eslintrc.*`?
3. Run `npm run lint` would succeed in a clean checkout? (Often `eslint .` fails because no config file exists.)
4. `prettier` config?
5. `tsconfig.json` strictness (if TS)?

### D. Vite / framework config
1. `vite.config.{js,ts}` — base, alias, plugins, build options?
2. Source maps in production build? (Leaks source code; off by default in Vite — verify.)
3. Manual chunks defined (for caching efficiency)?

### E. CI/CD
1. `.github/workflows/` exists? Workflows defined?
2. Pre-commit hooks (`.husky/`)? `lint-staged` configured?
3. Tests run in CI?
4. Build runs in CI?
5. Deploy hooks (auto-deploy on push to main)?

### F. Documentation
Read `README.md` and any planning docs (`IMPLEMENTATION_PLAN.md`, `PROJECT_BLUEPRINT.md`, `CHANGELOG.md`).

1. Does the README accurately describe the stack? (Compare to `package.json`.)
2. Are setup instructions complete?
3. Is the deploy target documented correctly?
4. Is the webhook URL / configuration documented? (Provider webhook = `https://your-domain/.netlify/functions/webhook-name`.)
5. Is the SQL schema application order documented (if applicable)?
6. Is there a `LICENSE` file matching the README's stated license?

### G. Git hygiene
1. `.gitignore` covers `.env*`, `node_modules`, `dist`, `.netlify`, `.vercel`, `coverage`, etc.?
2. Recent commits — any accidental commits of secrets? (`git log --oneline | head -20`)
3. Branch strategy — is `main` protected?

### H. Production-specific risks
1. Are `success_url` / `cancel_url` hardcoded to localhost anywhere?
2. Are CORS origins set to `*` in production?
3. Are debug routes / test endpoints (`/test`, `/.netlify/functions/test-db`) present?
4. Is there a feature flag system, or hardcoded `if (window.location.hostname === 'localhost')` checks?
5. Stripe (or equivalent) mode: test vs live — how is it switched?

### I. Observability (mention but don't deep dive)
1. Sentry / Logflare / Datadog configured?
2. Error boundaries reporting to a service?
3. Webhook delivery monitoring?

## What to deliver

Beyond YAML findings:

- **Env vars table** (variable | files | in .env.example | type | issue)
- **README vs reality discrepancy table**
- **Pre-production checklist** marked ✅/❌
- **Recommended `.env.example` template** (full, with comments explaining each var)
- **Recommended security headers snippet** for `netlify.toml` / `vercel.json`

## Don't

- Don't audit application security (Agent 2).
- Don't audit stack versions / dependencies (Agent 10).
- Don't audit SEO meta tags (Agent 8).

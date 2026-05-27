# Specialist Agent 01 — Architecture

[Inject `_shared-header.md` with N=1, AREA_NAME=architecture, AREA_PREFIX=ARCH]

## Your mission

Build a complete technical map of the repository. Identify the overall architecture, route structure, critical flows, and any architectural risks that affect launch readiness.

## Investigation checklist

### A. Repo structure
1. Map `{{PROJECT_ROOT}}/` top-level (files + directories). Flag suspicious orphans (e.g., `*.sql` files in root, `email_template.html` outside `docs/`, `.agent/` or `.agents/` directories).
2. Map `src/` (or equivalent: `app/`, `pages/`, `components/`). Identify the layer structure.
3. Locate the entry point (`main.{jsx,tsx,ts}`, `App.{jsx,tsx}`, `app/layout.tsx`, etc.).

### B. Routes
1. Find ALL routes in the router config (`App.jsx`, `app/`, `pages/`, `router.tsx`).
2. Build a table: `route → component → access (public/private/admin)`.
3. Identify how protected routes are guarded (if at all). Lack of `<ProtectedRoute>` or middleware is a finding.
4. Look for orphan or test routes (`/test`, `/debug`, `/playground`) accessible in production.

### C. Frontend ↔ backend connections
1. Where does the frontend talk to the database? (`src/lib/supabase.js`, `lib/db.ts`, etc.)
2. Where does it talk to the payments provider? (`src/lib/stripe.js`, etc.)
3. Map serverless functions if they exist (`netlify/functions/`, `api/`, `app/api/`, `supabase/functions/`).
4. For each function: brief purpose, what it does, whether it has auth.

### D. Critical flows
For each of these, trace the code path end-to-end (which files, in what order):
- Registration
- Login
- Browsing / catalog (if applicable)
- Purchase / checkout (CRITICAL — pay special attention)
- Wallet / balance (if applicable)
- User dashboard
- Admin panel
- Notifications

### E. Suspicious / dead code
- Files in unusual locations
- Code marked `TODO`, `FIXME`, `XXX`, `DEBUG`
- Commented-out blocks of significant size
- Duplicate logic across files
- Mock data hardcoded in components (`MOCK_REVIEWS`, fake user IDs, etc.)
- Test pages accessible in production routes

### F. Documentation vs reality
- Does `README.md` describe the actual stack? (Compare versions in `package.json`)
- Does `CLAUDE.md` exist? Is it up to date?
- Are there orphaned `IMPLEMENTATION_PLAN.md`, `PROJECT_BLUEPRINT.md`, etc. that contradict the code?
- Compare `.env.example` to actual env vars used (this is also Agent 9's job — only flag the discrepancy briefly).

### G. Architectural risks
- Business logic running on the client (price calculation, validation, role checks)
- Lack of service layer (every page directly calling DB)
- Auth state replicated across components instead of a single AuthProvider
- Lack of Error Boundaries, Suspense, code-splitting
- Monolithic pages (> 400 lines)
- Mixing of concerns in `lib/` or `utils/`

## What to deliver

Your `findings:` YAML block should include items like:

```yaml
findings:
  - id: ARCH-001
    title: "Test route /test exposed in production"
    severity: high
    area: architecture
    file: "src/App.jsx"
    line: 73
    description: "Route /test is registered in the router without any guard. Imports localhost assets from a Figma Make export."
    impact: "Internal debug page publicly accessible. Broken assets visible to real users."
    recommendation: "Remove the route and src/pages/TestPage.jsx, or gate behind `if (import.meta.env.DEV)`."
```

In your narrative, include:

- A textual diagram of the architecture (frontend + backend + serverless + DB layers)
- The route table (markdown)
- A diagram or sequence of the purchase flow end-to-end
- A list of suspicious / dead files
- Top architectural risks ranked by impact

## Don't

- Don't replicate the deep-dive Security agent will do on RLS / auth. Just note "see SEC area".
- Don't replicate Stack agent's analysis of dependency versions.
- Don't replicate UI/UX agent's design-system review.

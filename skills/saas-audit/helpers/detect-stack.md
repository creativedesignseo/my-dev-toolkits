# Stack Detection Heuristics

The orchestrator runs this BEFORE spawning specialist agents so each agent receives accurate stack context.

## Procedure

Run these checks in order. Stop at the first match for each category.

### Framework

1. `package.json` has `"next"` → **next**
2. `package.json` has `"@remix-run/react"` → **remix**
3. `package.json` has `"react"` + `"vite"` → **react** (Vite SPA)
4. `package.json` has `"react"` + `"react-scripts"` → **react** (CRA — flag as legacy)
5. `package.json` has `"vue"` + `"nuxt"` → **nuxt**
6. `package.json` has `"vue"` → **vue**
7. `package.json` has `"svelte"` + `"@sveltejs/kit"` → **sveltekit**
8. `package.json` has `"astro"` → **astro**
9. `package.json` has `"solid-js"` → **solid**
10. Else → **other** (report to user, may need manual config)

### Language

1. `tsconfig.json` exists AND majority of files are `.ts`/`.tsx` → **typescript**
2. `tsconfig.json` exists but most files are `.js`/`.jsx` → **mixed** (flag as deuda)
3. Else → **javascript**

### Bundler

1. `vite.config.{js,ts}` exists → **vite**
2. `next.config.{js,mjs,ts}` exists → **turbopack** (or **webpack** for next < 13)
3. `webpack.config.{js,ts}` exists → **webpack**
4. `rollup.config.{js,ts}` exists → **rollup**
5. Else → **other**

### Backend / Database

1. `package.json` has `"@supabase/supabase-js"` → **supabase**
2. `package.json` has `"firebase"` or `"firebase-admin"` → **firebase**
3. `package.json` has `"prisma"` or `"@prisma/client"` → check `schema.prisma` for provider:
   - `provider = "postgresql"` → **postgres**
   - `provider = "mysql"` → **mysql**
   - `provider = "mongodb"` → **mongodb**
4. `package.json` has `"drizzle-orm"` → check `drizzle.config.{js,ts}`
5. `package.json` has `"mongoose"` → **mongodb**
6. `package.json` has `"pg"` or `"postgres"` → **postgres**
7. `package.json` has `"mysql2"` or `"mysql"` → **mysql**
8. No DB dep found but `/api/` or `/server/` exists → **custom-api**
9. Else → **none**

### Payments

1. `package.json` has `"stripe"` or `"@stripe/stripe-js"` → **stripe**
2. `package.json` has `"@paddle/paddle-js"` or `"paddle-node-sdk"` → **paddle**
3. `package.json` has `"@lemonsqueezy/lemonsqueezy.js"` → **lemonsqueezy**
4. `package.json` has `"@paypal/react-paypal-js"` → **paypal**
5. grep for "redsys" in source → **redsys**
6. grep for "bizum" in source → **bizum** (often a manual flow, flag for review)
7. Else → **none** (if SaaS without payments, ask user to confirm)

### Auth

1. `package.json` has `"@supabase/auth-ui-react"` or supabase + auth in code → **supabase-auth**
2. `package.json` has `"next-auth"` or `"@auth/core"` → **nextauth**
3. `package.json` has `"@clerk/nextjs"` or `"@clerk/clerk-react"` → **clerk**
4. `package.json` has `"@auth0/auth0-react"` or `"@auth0/nextjs-auth0"` → **auth0**
5. `package.json` has `"firebase"` + auth in code → **firebase-auth**
6. Roll-your-own JWT in code → **custom** (flag as risk)
7. Else → **none**

### Hosting

1. `netlify.toml` or `.netlify/` → **netlify**
2. `vercel.json` or `.vercel/` → **vercel**
3. `wrangler.toml` → **cloudflare**
4. `fly.toml` → **fly**
5. `render.yaml` → **render**
6. `Dockerfile` + no other indicator → **docker** (deploy target unclear)
7. `serverless.yml` → **aws-serverless**
8. Else → **unknown**

### Serverless functions

1. `netlify/functions/` directory exists → **netlify-functions**
2. `api/` directory at root + Vercel → **vercel-functions**
3. `app/api/` directory → **next-route-handlers**
4. `supabase/functions/` → **supabase-edge-functions**
5. `functions/` + firebase → **firebase-functions**
6. Else → **none**

### Styles

1. `tailwind.config.{js,ts}` or `tailwind.config.cjs` → **tailwind**
2. `*.module.css` files exist → **css-modules**
3. `package.json` has `"styled-components"` → **styled-components**
4. `package.json` has `"@emotion/react"` → **emotion**
5. Else → **plain-css**

### i18n

1. `package.json` has `"react-i18next"` → **react-i18next**
2. `package.json` has `"next-intl"` → **next-intl**
3. `package.json` has `"next-i18next"` → **next-i18next**
4. `package.json` has `"vue-i18n"` → **vue-i18n**
5. Else → **none**

### Output language detection

Run in this order:

1. Read `CLAUDE.md` if exists. Count Spanish vs English words in first 500 chars. Majority Spanish → `es`.
2. Read `README.md`. Same heuristic.
3. Read last 5 commit messages (`git log -5 --format=%s`). Same heuristic.
4. Default → `en`.

## Output

After detection, print to the user:

```
🔍 Stack detected:

  Framework:  React + Vite
  Language:   JavaScript
  Backend:    Supabase
  Payments:   Stripe
  Auth:       Supabase Auth
  Hosting:    Netlify
  Functions:  Netlify Functions
  Styles:     Tailwind
  i18n:       None
  Output language: es

Spawning 11 specialist agents in parallel. Estimated time: 45 minutes.

Continue? [y/N]
```

Wait for confirmation before spawning agents.

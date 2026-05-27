# saas-audit

> **Multi-agent production-readiness audit for SaaS projects.** Spawns 13 specialist agents in parallel and produces a single `AUDIT_REPORT.md` with a weighted **Production Readiness Score 0–100**, prioritized findings, and a phased remediation roadmap.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Skill](https://img.shields.io/badge/Claude%20Code-Skill-blue)](https://skills.sh/)
[![Version](https://img.shields.io/badge/version-0.1.0-green)](#versioning)

---

## What it does

When you run `/saas-audit` in a SaaS project, it:

1. **Detects the stack** (React/Next/Vue/Astro, Stripe/Paddle/LemonSqueezy, Supabase/Firebase/Postgres, Netlify/Vercel, Tailwind, etc.).
2. **Spawns 11 specialist agents in parallel**, each auditing a critical area:
   - Architecture
   - Security
   - Payments (Stripe/Paddle end-to-end)
   - Database (RLS / RPC / migrations)
   - Admin area
   - UI/UX (especially checkout trust)
   - QA functional (static end-to-end analysis)
   - SEO / Performance
   - Deploy / Production readiness
   - Stack / Modernization
   - Legal / Compliance (GDPR, DSA, consumer law, third-party ToS)
3. **Consolidates findings** (deduplication, severity calibration).
4. **Calculates a Production Readiness Score 0–100** weighted by area.
5. **Generates `AUDIT_REPORT.md`** at the project root with a phased roadmap (Phase 0 → Phase 3).

The output looks like this:

```
╔══════════════════════════════════════════════════════════╗
║  PRODUCTION READINESS REPORT — MyProject                 ║
║  Mode: full                          2026-05-25T14:32Z   ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Score:  ████░░░░░░░░░░░░░░░░░░  8/100  🛑 BLOCKED       ║
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
║  Findings: 7 critical · 25 high · 40 medium              ║
║                                                          ║
║  Full report: ./AUDIT_REPORT.md                          ║
╚══════════════════════════════════════════════════════════╝
```

## When to use it

✅ **Use it for:**
- Pre-launch audit of a SaaS with real payments
- Periodic health check before major releases
- Due diligence on an acquisition target
- Client deliverable for technical audits (agencies)

❌ **Don't use it for:**
- Single-file code review → use `obra/superpowers@requesting-code-review`
- Generic repo overview → use `anthropic-skills:github-repo-audit`
- Pure UI / design audit → use `pbakaus/impeccable@audit`
- Pure SEO audit → use `coreyhaines31/marketingskills@seo-audit`
- Static sites without backend → overkill (use `--quick` mode at most)

## Installation

```bash
npx skills add creativedesignseo/dev-toolkits-skills@saas-audit -g -y
```

Or clone directly:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/creativedesignseo/dev-toolkits-skills.git
ln -s "$(pwd)/dev-toolkits-skills/skills/saas-audit" ~/.claude/skills/saas-audit
```

## Usage

In any project directory, in Claude Code:

```
/saas-audit
```

The skill will:
1. Detect your stack
2. Ask you to confirm before spawning 11 agents
3. Run them in parallel (~45 min for full mode)
4. Write `AUDIT_REPORT.md` at the project root
5. Append history to `.saas-audit/history.json`

### Modes

| Command | Agents | Time | Use case |
|---|---|---|---|
| `/saas-audit` | 11 specialists + 2 meta | ~45 min | Full pre-launch audit |
| `/saas-audit --quick` | 6 essentials | ~15 min | Sanity check |
| `/saas-audit --focus=payments` | 4 (Payments + Security + Database + QA) | ~10 min | Stripe issues |
| `/saas-audit --focus=security` | 4 (Security + Database + Admin + Deploy) | ~10 min | Pre-pentest |
| `/saas-audit --focus=ui` | 3 (UI/UX + SEO + QA) | ~8 min | Polish phase |

### Output

Two files are written to your project:

- `AUDIT_REPORT.md` — full audit report (root of project, intended to be committed or shared)
- `.saas-audit/history.json` — score history (gitignored)

## Scoring algorithm

Production Readiness Score is **0–100**, weighted across 10 areas:

| Area | Weight |
|---|---:|
| Security | 25 |
| Payments | 20 |
| Data layer | 15 |
| UI/UX | 10 |
| QA functional | 10 |
| Admin | 5 |
| SEO / Performance | 5 |
| Deploy / Env | 5 |
| Stack / Modernization | 3 |
| Legal / Compliance | 2 |

Findings subtract points by severity:

| Severity | Penalty |
|---|---:|
| Critical (P0) | -10 |
| High (P1) | -5 |
| Medium (P2) | -2 |
| Low (P3) | -0.5 |
| Recommendation | 0 |

Penalties cap at each area's weight. Score = sum of area scores, clamped to [0, 100].

Thresholds:

| Range | Badge | Verdict |
|---|---|---|
| 90-100 | 🟢 LAUNCH READY | Ship it |
| 70-89 | 🟡 LAUNCH WITH CAVEATS | Ship with monitoring |
| 50-69 | 🟠 SIGNIFICANT WORK | Phase 1 of roadmap first |
| 25-49 | 🔴 NOT READY | Phase 0 + 1 mandatory |
| 0-24 | 🛑 BLOCKED | Do not accept real money |

Full algorithm in [`helpers/scoring.md`](./helpers/scoring.md).

## Supported stacks

| Layer | Supported |
|---|---|
| **Framework** | React (Vite/CRA), Next.js (App + Pages router), Vue/Nuxt, SvelteKit, Astro, Solid |
| **Language** | JavaScript, TypeScript, mixed |
| **Backend** | Supabase, Firebase, Postgres (Prisma/Drizzle), MySQL, MongoDB, custom-api |
| **Payments** | Stripe, Paddle, LemonSqueezy, PayPal, Redsys, Bizum (with caveats) |
| **Auth** | Supabase Auth, NextAuth, Clerk, Auth0, Firebase Auth |
| **Hosting** | Netlify, Vercel, Cloudflare, Fly, Render |
| **Functions** | Netlify Functions, Vercel Functions, Next route handlers, Supabase Edge Functions, Firebase Functions |
| **Styles** | Tailwind, CSS Modules, styled-components, Emotion |
| **i18n** | react-i18next, next-intl, next-i18next, vue-i18n |

The skill adapts the prompts based on detection. For exotic stacks, the orchestrator will ask you to confirm the stack block before spawning agents.

## Multi-language

- **The skill itself is in English** (community convention, broader discoverability).
- **The output report is in your project's language** (detected from `CLAUDE.md` / `README.md`):
  - Spanish project → `AUDIT_REPORT.md` in Spanish
  - English project → `AUDIT_REPORT.md` in English
  - Mixed → defaults to English

## Versioning

| Version | Status | Features |
|---|---|---|
| **v0.1.0** | **Current** | Audit only (SCAN + SCORE + REPORT) |
| v0.2.0 | Planned | Auto-fix mode (`--fix`) for P0/P1 mechanical fixes in worktrees |
| v0.3.0 | Planned | Verify mode (`--verify`) for delta tracking between audits |
| v0.4.0 | Planned | GitHub Action integration, badge generation, publication to skills.sh |

## Comparison with similar skills

| Skill | Scope | Multi-agent? | Score? | Auto-fix? |
|---|---|---|---|---|
| **saas-audit** (this) | Full SaaS pre-launch | ✅ 13 agents | ✅ 0-100 | 🚧 v0.2 |
| `anthropic-skills:github-repo-audit` | Generic repo overview | ❌ single | ❌ | ❌ |
| `pbakaus/impeccable@audit` | UI / design only | ❌ single | ❌ | ❌ |
| `coreyhaines31/marketingskills@seo-audit` | SEO only | ❌ single | ❌ | ❌ |
| `wshobson/agents@multi-reviewer-patterns` | PR review (5 dimensions) | Pattern only | ❌ | ❌ |
| `firebase/agent-skills@firebase-security-rules-auditor` | Firebase RLS only | ❌ single | ❌ | ❌ |

## Privacy

This skill runs entirely locally. It:
- Reads files from your project directory
- Sends them to Claude (your existing Claude Code session)
- Writes `AUDIT_REPORT.md` and `.saas-audit/history.json` locally

It does NOT:
- Send any data to third-party services
- Phone home with telemetry
- Require OAuth or external credentials
- Modify any file other than the two report files

## Contributing

PRs welcome. Special interest in:
- Additional stack detections (Remix, Astro variants, Bun-based frameworks)
- Additional payments providers (Mollie, Razorpay, Square)
- Additional regulatory frameworks (CCPA for California, LGPD for Brazil)
- Improvements to the scoring algorithm (especially the area weights)

## License

MIT. Free to use, fork, modify, redistribute. If you use it on client work, attribution is appreciated but not required.

## Credits

Built by [Adspubli](https://adspubli.com) (Jonatan @ creativedesignseo).

Pattern proven on real SaaS audits — first iteration was a 10-agent ad-hoc audit on LowSplit (a subscription-sharing SaaS), which detected 7 P0 vulnerabilities including credentials stored in plain text, self-elevation to super_admin via RLS gaps, and price manipulation in the Stripe checkout. Score: 8/100.

See [`examples/lowsplit-anonymized.md`](./examples/lowsplit-anonymized.md) for the (anonymized) report.

---
name: saas-audit
description: Orchestrates an in-depth multi-agent production-readiness audit of a SaaS project. Spawns 11 specialist agents in parallel (architecture, security, payments, database, admin, UI/UX, QA, SEO/performance, deploy, stack, legal) plus 2 meta agents (orchestrator + reporter) to produce a consolidated AUDIT_REPORT.md with a Production Readiness Score 0-100, prioritized findings (P0-P3) and a phased remediation roadmap. Use when the user asks IN ENGLISH "audit my SaaS", "production readiness audit", "is this ready for production", "audit this project", "/saas-audit", "full audit", "security and payments audit", or IN SPANISH "auditoría completa", "audita este SaaS", "audita el proyecto", "está listo para producción", "auditoría de pagos", "revisa seguridad y Stripe". Specifically optimized for SaaS with real payments (Stripe, Paddle, LemonSqueezy, Bizum) and a backend (Supabase, Firebase, Postgres, MongoDB). Supports three modes — full (13 agents, ~45 min), quick (6 agents, ~15 min), focus (4 agents on a single concern). Generates a structured report in the user's project language (detected from CLAUDE.md / README) but the skill itself runs in English. Read-only by default — does NOT modify code, only produces the report.
license: MIT
---

# saas-audit

Multi-agent production-readiness audit for SaaS projects with real payments. Spawns specialist agents in parallel, calculates a weighted Production Readiness Score 0–100, and produces a single consolidated `AUDIT_REPORT.md` with prioritized findings (P0–P3) and a phased remediation roadmap.

## When to invoke

Invoke when the user says any of (English or Spanish):

- `/saas-audit` (explicit command — always invoke)
- "audit my SaaS / this project", "do a production readiness audit"
- "audita este SaaS", "auditoría completa", "está listo para producción"
- "security and payments audit", "auditoría de pagos y seguridad"
- User pastes a repo URL and asks for an audit, deep review, or "is this ready to launch"

Do NOT invoke for:
- Single-file code review (use `requesting-code-review` or `code-review` instead)
- Generic repo overview (use `anthropic-skills:github-repo-audit`)
- Pure UI/design audit (use `pbakaus/impeccable@audit`)
- Static sites without backend (overkill — recommend `quick` mode at most)

## Modes

| Mode | Agents | Time | Use when |
|---|---|---|---|
| **full** (default) | 13 (all 11 specialists + orchestrator + reporter) | ~45 min | Pre-production launch of a SaaS with payments |
| **quick** | 6 (Architecture, Security, Payments, Database, Deploy, Stack) + reporter | ~15 min | Early-stage projects, sanity check |
| **focus=payments** | 4 (Payments, Security, Database, QA) + reporter | ~10 min | Suspect issue in Stripe / checkout flow |
| **focus=security** | 4 (Security, Database, Admin, Deploy) + reporter | ~10 min | Pre-pentest hardening |
| **focus=ui** | 3 (UI/UX, SEO/Performance, QA) + reporter | ~8 min | Polish phase before launch |

Parse the user's invocation:
- Default → `full` mode
- `/saas-audit --quick` or "quick audit" → `quick`
- `/saas-audit --focus=payments` or "audit payments" / "audita pagos" → `focus=payments`
- `/saas-audit --focus=security` → `focus=security`
- `/saas-audit --focus=ui` → `focus=ui`

## Hard rules — do not violate

1. **Read-only.** This skill NEVER modifies code, NEVER commits, NEVER pushes. Only produces `AUDIT_REPORT.md` at the repo root and `.saas-audit/history.json`. Fixers come in v0.2.
2. **Never run destructive commands.** No `rm`, no `git reset`, no SQL migrations, no `npm install`. Only read.
3. **Never invent findings.** Every finding MUST reference `file:line` or a concrete endpoint/URL. If the agent can't cite a source, drop the finding.
4. **Never assume cloud credentials.** Don't attempt to query Supabase, Stripe API, or any external service. All analysis is static (reading repo files).
5. **Always parallelize.** Specialist agents MUST be spawned in a single message with multiple `Agent` tool calls. Sequential spawning negates the entire benefit of this skill.
6. **Always be brutally honest.** Each agent prompt includes "no sugar-coating, prioritize critical findings". The user is making real launch decisions.
7. **Respect token budget.** If a single agent returns more than 8000 words, instruct the reporter to truncate the prose and keep the structured YAML findings only.

## Procedure

### Step 1 — Confirm working directory

Run `pwd` and `git rev-parse --show-toplevel`. Confirm to the user this is the project root being audited. If not in a git repo, ask whether to proceed (some projects are not versioned yet).

### Step 2 — Detect the stack

Follow `helpers/detect-stack.md`. Output a STACK block like:

```yaml
stack:
  framework: react | next | vue | nuxt | svelte | astro | other
  bundler: vite | webpack | turbopack | rollup | other
  language: javascript | typescript | mixed
  backend: supabase | firebase | postgres | mongodb | mysql | custom-api | none
  payments: stripe | paddle | lemonsqueezy | bizum | redsys | none
  auth: supabase-auth | nextauth | clerk | auth0 | firebase-auth | custom | none
  hosting: netlify | vercel | cloudflare | fly | render | aws | other | unknown
  serverless: netlify-functions | vercel-functions | edge-functions | supabase-functions | none
  styles: tailwind | css-modules | styled-components | other
  i18n: react-i18next | next-intl | none
output_language: es | en | other  # detected from CLAUDE.md / README primary language
```

Show this STACK block to the user before spawning agents. If anything looks wrong, ask for correction.

### Step 3 — Detect output language

Read `README.md`, `CLAUDE.md`, recent commit messages. If majority Spanish → `output_language: es`. Default → `en`. The orchestrator passes this to each specialist so the final report matches the user's working language.

### Step 4 — Select agents based on mode

Map mode to agent set:

```
full:           01,02,03,04,05,06,07,08,09,10,11
quick:          01,02,03,04,09,10
focus=payments: 02,03,04,07
focus=security: 02,04,05,09
focus=ui:       06,07,08
```

Always include the reporter at the end.

### Step 5 — Spawn specialist agents in parallel

For each selected agent, read its prompt from `prompts/NN-name.md`, substitute placeholders (`{{PROJECT_ROOT}}`, `{{STACK}}`, `{{OUTPUT_LANGUAGE}}`, `{{PROJECT_NAME}}`), and spawn via the `Agent` tool with `subagent_type: "general-purpose"`. **ALL agents in a single message** with multiple `Agent` tool calls (this is critical for parallelism).

Each agent prompt instructs it to output:
1. A TLDR (3-5 lines)
2. A structured YAML `findings:` block (see schema in `helpers/scoring.md`)
3. A short Markdown narrative report

Run agents in the background (`run_in_background: true`) and continue.

### Step 6 — Wait for completions

As each agent completes, mark a sub-task done. When all agents have returned:

### Step 7 — Invoke the Reporter

Follow `helpers/report-template.md`. The reporter:

1. Collects all `findings:` YAML blocks from the specialists
2. **Deduplicates** by `file:line` + title similarity
3. Applies the scoring algorithm from `helpers/scoring.md`
4. Computes the Production Readiness Score (0-100, weighted by area)
5. Generates the consolidated `AUDIT_REPORT.md` at the project root
6. Saves the score + summary to `.saas-audit/history.json` (creates the directory if needed)
7. Adds `.saas-audit/` to `.gitignore` if not present
8. Prints a final terminal-style banner with the score, top 10 findings, and next steps

### Step 8 — Present the result to the user

Show the score banner, summarize the top 5 critical findings, and indicate where the full report lives (`./AUDIT_REPORT.md`). Offer next steps:

- "Want me to apply the P0 fixes? (v0.2 feature — not yet available)"
- "Want a focused re-audit on a specific area?"
- "Want me to open issues in GitHub for each finding?"

## Scoring overview

See `helpers/scoring.md` for the full algorithm.

Quick reference — area weights (sum to 100):

| Area | Weight | Rationale |
|---|---|---|
| Security | 25 | Fraud = direct revenue loss |
| Payments | 20 | Core revenue path |
| Data layer (RLS/RPC) | 15 | Foundation of trust |
| UI/UX (checkout focus) | 10 | Conversion |
| QA functional | 10 | Stability |
| Admin | 5 | Operations |
| SEO / Performance | 5 | Growth |
| Deploy / Env | 5 | Stability |
| Stack / Modernization | 3 | Maintainability |
| Legal / Compliance | 2 | Regulatory risk |

Severity penalties (applied within each area, capped at area weight):

| Severity | Penalty |
|---|---|
| Critical (P0) | -10 pts |
| High (P1) | -5 pts |
| Medium (P2) | -2 pts |
| Low (P3) | -0.5 pts |
| Recommendation | 0 pts |

Final score: `100 - sum(penalties)`, clamped to `[0, 100]`.

Score thresholds:
- 90-100: 🟢 LAUNCH READY
- 70-89: 🟡 LAUNCH WITH CAVEATS
- 50-69: 🟠 SIGNIFICANT WORK REQUIRED
- 25-49: 🔴 NOT READY
- 0-24: 🛑 BLOCKED — DO NOT LAUNCH

## Output structure

The reporter writes a single `AUDIT_REPORT.md` at the project root with this structure:

```
# Production Readiness Audit — {{PROJECT_NAME}}

## Score Banner
## Executive Summary (5 lines)
## Critical Findings (P0) — must fix before launch
## High Findings (P1) — must fix in first sprint after launch
## Medium Findings (P2) — backlog
## Low Findings (P3) — nice to have
## Phased Roadmap
  ### Phase 0 — Stop the Bleed (1-3 days)
  ### Phase 1 — Stabilization (1-2 weeks)
  ### Phase 2 — Production Quality (3-4 weeks)
  ### Phase 3 — Modernization (3-6 months)
## Per-Area Reports (collapsed sections)
## Appendix — full findings table
```

History is persisted in `.saas-audit/history.json`:

```json
{
  "audits": [
    {
      "timestamp": "2026-05-25T12:34:56Z",
      "mode": "full",
      "score": 8,
      "by_area": { "security": 0, "payments": 0, "data": 2, ... },
      "findings_count": { "critical": 7, "high": 25, "medium": 40, "low": 18 }
    }
  ]
}
```

## Examples

See `examples/lowsplit-anonymized.md` for a real audit output (anonymized) showing what the final report looks like for a SaaS scoring 8/100.

## Limitations (v0.1)

- **Read-only.** No auto-fix yet — that's v0.2.
- **Static analysis only.** Doesn't query live Stripe / Supabase APIs.
- **Heuristic detection.** Stack detection works well for common stacks; for exotic setups, the user may need to correct the STACK block before spawning agents.
- **Token-intensive.** Full mode reads many files across the repo. For repos > 500 files, prefer `quick` or `focus` mode.
- **One language at a time.** If the project mixes Spanish and English heavily, the reporter picks the dominant one.

## Versioning

Current: **v0.1.0** (audit only). Roadmap:

- v0.2 — Specialist fixer mode (`--fix` applies P0+P1 fixes in isolated worktrees with user confirmation)
- v0.3 — Verify mode (`--verify` re-audits and shows delta from previous run)
- v0.4 — Publication to skills.sh, GitHub Actions integration, badge generation

## License

MIT. Free to use, fork, modify, redistribute.

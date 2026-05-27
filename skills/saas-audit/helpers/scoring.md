# Scoring Algorithm — Production Readiness Score (0-100)

This document defines the **deterministic** scoring algorithm used by the reporter agent. Every audit MUST apply this exactly — no improvisation.

## Finding schema (input)

Every specialist agent outputs findings in this YAML schema:

```yaml
findings:
  - id: SEC-001                  # required: area-prefix + 3-digit sequential
    title: "Short imperative title"
    severity: critical | high | medium | low | recommendation
    area: security                # required: one of the 10 areas (see below)
    file: "path/to/file.ext"      # required if applicable (some legal/process findings don't have a file)
    line: 123                     # optional
    description: "Multi-line description of what's wrong"
    impact: "Business/security/UX impact"
    reproduction: "Steps to reproduce"  # optional
    recommendation: "Concrete, actionable fix"
    references:                   # optional
      - "https://stripe.com/docs/webhooks/best-practices"
```

**Area enum (10 values):**
`architecture | security | payments | data | admin | ui-ux | qa | seo-perf | deploy | stack | legal`

(Note: `architecture` findings are distributed across other areas for scoring — see "Area mapping" below.)

## Area weights (sum to 100)

| Area | Weight | Rationale |
|---|---:|---|
| security | 25 | Fraud and breach = direct revenue + reputation loss |
| payments | 20 | Core revenue path; any bug = lost money |
| data | 15 | RLS, integrity, atomicity — foundation of trust |
| ui-ux | 10 | Conversion (focus on checkout flow) |
| qa | 10 | Runtime crashes, broken flows |
| admin | 5 | Operational capability |
| seo-perf | 5 | Growth and Core Web Vitals |
| deploy | 5 | Configuration, env vars, prod readiness |
| stack | 3 | Maintainability, modernization |
| legal | 2 | GDPR, ToS, consumer law |
| **Total** | **100** | |

`architecture` findings: re-categorize each one into its nearest area before scoring (e.g., "no AuthProvider" → `security`; "no code-splitting" → `seo-perf`; "monolithic pages" → `stack`).

## Severity penalties

Each finding subtracts points from its area's weight:

| Severity | Code | Penalty |
|---|---|---:|
| Critical | P0 | -10 pts |
| High | P1 | -5 pts |
| Medium | P2 | -2 pts |
| Low | P3 | -0.5 pts |
| Recommendation | — | 0 pts |

**Important:** Penalties within an area are summed, then **capped at the area weight**. An area cannot go below 0.

Example: 7 critical findings in `security` = 7 × -10 = -70, but `security` weight is 25, so the area scores `max(0, 25 - 70) = 0`.

## Final score formula

```
area_score(a) = max(0, weight(a) - sum(penalties of findings in a))
total_score   = sum(area_score(a) for all a)
final_score   = clamp(total_score, 0, 100)
```

## Score thresholds and badges

| Range | Badge | Verdict |
|---|---|---|
| 90-100 | 🟢 LAUNCH READY | Ship it (minor polish only) |
| 70-89 | 🟡 LAUNCH WITH CAVEATS | Document known issues; ship with monitoring |
| 50-69 | 🟠 SIGNIFICANT WORK | Phase 1 of roadmap required first |
| 25-49 | 🔴 NOT READY | Phase 0 + Phase 1 mandatory |
| 0-24 | 🛑 BLOCKED | Do not accept real money or PII |

## Deduplication rules

Before scoring, deduplicate findings across specialists:

1. **Exact file:line match + similar title (>70% overlap)** → keep the highest-severity one, drop the rest. Add `also_detected_by: [SEC-001, DB-002]` to the kept finding.
2. **Same file but different lines, same root cause** (e.g., "missing JWT" across 4 endpoints) → consolidate into one finding with `affected_locations: [...]`.
3. **Cross-area findings** (e.g., RLS issue detected by both Security and Database agents) → keep the one from the area where it has the highest impact (usually Security for auth issues, Data for integrity issues).

## Banner format

The reporter generates a terminal-style banner:

```
╔══════════════════════════════════════════════════════════╗
║  PRODUCTION READINESS REPORT — {{PROJECT_NAME}}          ║
║  Mode: {{MODE}}                          {{TIMESTAMP}}   ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Score:  ████░░░░░░░░░░░░░░░░░░  {{N}}/100  {{BADGE}}    ║
║                                                          ║
║  Security      {{bar}}  {{n}}/25                         ║
║  Payments      {{bar}}  {{n}}/20                         ║
║  Data layer    {{bar}}  {{n}}/15                         ║
║  UI/UX         {{bar}}  {{n}}/10                         ║
║  QA            {{bar}}  {{n}}/10                         ║
║  Admin         {{bar}}  {{n}}/5                          ║
║  SEO/Perf      {{bar}}  {{n}}/5                          ║
║  Deploy        {{bar}}  {{n}}/5                          ║
║  Stack         {{bar}}  {{n}}/3                          ║
║  Legal         {{bar}}  {{n}}/2                          ║
║                                                          ║
║  Findings: {{c}} critical · {{h}} high · {{m}} medium    ║
║            · {{l}} low · {{r}} recommendations           ║
║                                                          ║
║  Top blockers (P0):                                      ║
║   1. {{title1}}                                          ║
║   2. {{title2}}                                          ║
║   ...                                                     ║
║                                                          ║
║  Full report: ./AUDIT_REPORT.md                          ║
║  Next: /saas-audit --fix  (v0.2, coming soon)            ║
╚══════════════════════════════════════════════════════════╝
```

Bar renderer: 10 characters wide. `█` for filled, `░` for empty. `bar_filled = round((n / max) * 10)`.

## History persistence

After each audit, append to `.saas-audit/history.json`:

```json
{
  "audits": [
    {
      "timestamp": "2026-05-25T12:34:56Z",
      "mode": "full",
      "git_commit": "abc123",
      "score": 8,
      "by_area": {
        "security": 0,
        "payments": 0,
        "data": 2,
        "ui-ux": 3,
        "qa": 2,
        "admin": 1,
        "seo-perf": 0,
        "deploy": 0,
        "stack": 0,
        "legal": 0
      },
      "findings_count": {
        "critical": 7,
        "high": 25,
        "medium": 40,
        "low": 18,
        "recommendation": 12
      },
      "top_blockers": ["SEC-001", "PAY-015", "DB-002"]
    }
  ]
}
```

If `.saas-audit/` doesn't exist, create it. Add `.saas-audit/` to `.gitignore` if not present.

## Worked example (LowSplit-style)

Findings detected:
- Security: 4 critical, 6 high → penalties = 40 + 30 = 70 → area_score = max(0, 25-70) = **0**
- Payments: 3 critical, 8 high → penalties = 30 + 40 = 70 → area_score = max(0, 20-70) = **0**
- Data: 2 critical, 5 high, 4 medium → penalties = 20 + 25 + 8 = 53 → area_score = max(0, 15-53) = **0**
- UI/UX: 0 critical, 3 high, 8 medium → penalties = 15 + 16 = 31 → area_score = max(0, 10-31) = **0**

Wait, this gives 0 across the board. Let me re-check with a less-broken project:

Findings:
- Security: 0 critical, 2 high → -10 → 25-10 = **15**
- Payments: 0 critical, 1 high, 3 medium → -5-6 = -11 → 20-11 = **9**
- Data: 0 critical, 1 high → -5 → 15-5 = **10**
- UI/UX: 0 critical, 4 medium → -8 → 10-8 = **2**
- QA: 0 critical, 1 high, 2 medium → -5-4 = -9 → 10-9 = **1**
- Admin: 1 medium → -2 → 5-2 = **3**
- SEO/Perf: 2 medium → -4 → 5-4 = **1**
- Deploy: 1 high → -5 → 5-5 = **0**
- Stack: 1 medium → -2 → 3-2 = **1**
- Legal: 1 medium → -2 → 2-2 = **0**

Total = 15+9+10+2+1+3+1+0+1+0 = **42** → 🔴 NOT READY

This is more realistic for a project that has some work but is not catastrophic.

## Error handling

- If an agent fails to return findings: log a `WARNING` in the report, score that area as `weight - 0 = full weight` (assume zero issues found but flag uncertainty).
- If findings reference files that don't exist: drop them silently (the agent hallucinated).
- If a finding has unknown severity: treat as `low`.

#!/usr/bin/env python3
"""
gsc_cli — Multi-account Google Search Console CLI for Adspubli

Subcommands:
  login        --account X                        # OAuth flow
  list-sites   --account X                        # All verified sites
  queries      --account X --site URL             # Top queries (keywords)
                  [--since 30daysAgo] [--until today] [--limit 25]
                  [--filter-query "vaciado"]
  pages        --account X --site URL             # Top pages
                  [--since ...] [--limit ...]
  positions    --account X --site URL --keywords k1,k2,...
                  # Average position for specific keywords

Uses the Search Console API v1.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from urllib.parse import quote_plus

from googleapiclient.errors import HttpError

from _auth import SCOPES, get_credentials, service, token_path


# ── Service builder ─────────────────────────────────────────────────────────
def gsc_service(account: str):
    return service(account, "searchconsole", "v1", SCOPES["webmasters_readonly"])


# ── Date helpers ────────────────────────────────────────────────────────────
def resolve_date(s: str) -> str:
    """
    Convert relative dates (e.g. '30daysAgo', 'today', 'yesterday') to YYYY-MM-DD.
    GSC API expects absolute dates only.
    """
    s = s.strip().lower()
    today = dt.date.today()
    if s in ("today",):
        return today.isoformat()
    if s in ("yesterday",):
        return (today - dt.timedelta(days=1)).isoformat()
    if s.endswith("daysago"):
        try:
            n = int(s.replace("daysago", "").strip())
            return (today - dt.timedelta(days=n)).isoformat()
        except ValueError:
            pass
    # Assume YYYY-MM-DD already
    return s


def parse_list(s: str | None) -> list[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


# ── Subcommands ─────────────────────────────────────────────────────────────
def cmd_login(args):
    get_credentials(args.account, SCOPES["webmasters_readonly"])
    print(f"✅ Logged in (Search Console scopes) as {args.account}")
    print(f"   Token: {token_path(args.account)}")


def cmd_list_sites(args):
    svc = gsc_service(args.account)
    res = svc.sites().list().execute()
    sites = res.get("siteEntry", [])
    if not sites:
        print("(no verified sites for this account)")
        return
    print(f"🌐 {len(sites)} site(s) verified:\n")
    for s in sites:
        perm = s.get("permissionLevel", "—")
        url = s.get("siteUrl", "—")
        mark = {"siteOwner": "👑", "siteFullUser": "✏️ ", "siteRestrictedUser": "👁️ "}.get(perm, "?")
        print(f"  {mark}  {url}")
        print(f"       permission: {perm}")
        print()


def _print_table(rows: list[dict], headers: list[str], json_out: bool):
    if not rows:
        print("(no data)")
        return
    if json_out:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    # Width per column
    table = []
    for r in rows:
        keys = r.get("keys", [])
        vals = list(keys) + [
            f"{r.get('clicks', 0):,}",
            f"{r.get('impressions', 0):,}",
            f"{r.get('ctr', 0)*100:.2f}%",
            f"{r.get('position', 0):.1f}",
        ]
        table.append(vals)
    widths = [max(len(h), max(len(str(row[i])) for row in table)) for i, h in enumerate(headers)]
    fmt = " │ ".join(f"{{:<{w}}}" for w in widths)
    sep = "─┼─".join("─" * w for w in widths)
    print(fmt.format(*headers))
    print(sep)
    for row in table:
        print(fmt.format(*row))


def cmd_queries(args):
    svc = gsc_service(args.account)
    body = {
        "startDate": resolve_date(args.since),
        "endDate": resolve_date(args.until),
        "dimensions": ["query"],
        "rowLimit": args.limit,
    }
    if args.filter_query:
        body["dimensionFilterGroups"] = [{
            "filters": [{
                "dimension": "query",
                "operator": "contains",
                "expression": args.filter_query,
            }]
        }]
    try:
        res = svc.searchanalytics().query(siteUrl=args.site, body=body).execute()
    except HttpError as e:
        sys.exit(f"❌ GSC API error: {e}")
    rows = res.get("rows", [])
    print(f"🔍 Top {len(rows)} queries — {args.site} — {body['startDate']} → {body['endDate']}\n")
    _print_table(rows, ["Query", "Clicks", "Impr.", "CTR", "Pos."], args.json)


def cmd_pages(args):
    svc = gsc_service(args.account)
    body = {
        "startDate": resolve_date(args.since),
        "endDate": resolve_date(args.until),
        "dimensions": ["page"],
        "rowLimit": args.limit,
    }
    try:
        res = svc.searchanalytics().query(siteUrl=args.site, body=body).execute()
    except HttpError as e:
        sys.exit(f"❌ GSC API error: {e}")
    rows = res.get("rows", [])
    print(f"📄 Top {len(rows)} pages — {args.site} — {body['startDate']} → {body['endDate']}\n")
    _print_table(rows, ["Page", "Clicks", "Impr.", "CTR", "Pos."], args.json)


def cmd_positions(args):
    svc = gsc_service(args.account)
    keywords = parse_list(args.keywords)
    if not keywords:
        sys.exit("❌ --keywords is required (comma-separated list).")

    print(f"📈 Avg position per keyword — {args.site} — {resolve_date(args.since)} → {resolve_date(args.until)}\n")
    rows_out = []
    for kw in keywords:
        body = {
            "startDate": resolve_date(args.since),
            "endDate": resolve_date(args.until),
            "dimensions": ["query"],
            "dimensionFilterGroups": [{
                "filters": [{
                    "dimension": "query",
                    "operator": "equals",
                    "expression": kw,
                }]
            }],
            "rowLimit": 1,
        }
        try:
            res = svc.searchanalytics().query(siteUrl=args.site, body=body).execute()
        except HttpError as e:
            sys.exit(f"❌ GSC API error on '{kw}': {e}")
        r = (res.get("rows") or [{}])[0]
        rows_out.append({
            "keys": [kw],
            "clicks": r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
            "ctr": r.get("ctr", 0),
            "position": r.get("position", 0),
        })
    _print_table(rows_out, ["Keyword", "Clicks", "Impr.", "CTR", "Pos."], args.json)


# ── CLI parser ──────────────────────────────────────────────────────────────
def make_parser():
    p = argparse.ArgumentParser(prog="gsc_cli", description="Multi-account Search Console CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp):
        sp.add_argument("--account", required=True, help="Google account email")

    sp = sub.add_parser("login", help="Authorize Search Console scopes")
    add_common(sp); sp.set_defaults(func=cmd_login)

    sp = sub.add_parser("list-sites", help="List all verified sites")
    add_common(sp); sp.set_defaults(func=cmd_list_sites)

    def add_query_common(sp):
        add_common(sp)
        sp.add_argument("--site", required=True,
                        help="Site URL exactly as registered (e.g. 'sc-domain:adspubli.com' or 'https://www.example.com/')")
        sp.add_argument("--since", default="30daysAgo")
        sp.add_argument("--until", default="today")
        sp.add_argument("--limit", type=int, default=25)
        sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("queries", help="Top search queries (keywords)")
    add_query_common(sp)
    sp.add_argument("--filter-query", help="Only queries containing this substring")
    sp.set_defaults(func=cmd_queries)

    sp = sub.add_parser("pages", help="Top pages")
    add_query_common(sp)
    sp.set_defaults(func=cmd_pages)

    sp = sub.add_parser("positions", help="Avg position for a specific set of keywords")
    add_query_common(sp)
    sp.add_argument("--keywords", "-k", required=True,
                    help="Comma-separated keywords to check")
    sp.set_defaults(func=cmd_positions)

    return p


def main():
    args = make_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

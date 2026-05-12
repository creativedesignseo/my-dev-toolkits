#!/usr/bin/env python3
"""
ga4_cli — Multi-account Google Analytics 4 CLI for Adspubli

Subcommands:
  login            --account X                              # OAuth flow
  list-accounts    --account X                              # GA accounts you can access
  list-properties  --account X [--account-id N]             # GA4 properties (web/app streams)
  report           --account X --property P
                   --metrics m1,m2,...
                   [--dimensions d1,d2,...]
                   [--since 7daysAgo] [--until today]
                   [--limit 25] [--order-by METRIC]
  realtime         --account X --property P --metrics m1,m2,... [--dimensions ...]

Uses the Google Analytics Admin API (v1beta) for listing, and the
Google Analytics Data API (v1beta) for reports.
"""
from __future__ import annotations

import argparse
import json
import sys

from googleapiclient.errors import HttpError

from _auth import SCOPES, get_credentials, service, token_path


# ── Service builders ────────────────────────────────────────────────────────
def admin_service(account: str):
    """Admin API — lists accounts, properties, streams, etc."""
    return service(account, "analyticsadmin", "v1beta", SCOPES["analytics_readonly"])


def data_service(account: str):
    """Data API — runs reports (historical + realtime)."""
    return service(account, "analyticsdata", "v1beta", SCOPES["analytics_readonly"])


# ── Helpers ─────────────────────────────────────────────────────────────────
def parse_list(s: str | None) -> list[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def fmt_property_id(p: str) -> str:
    """Accept either '534094689' or 'properties/534094689'. Return canonical form."""
    return p if p.startswith("properties/") else f"properties/{p}"


# ── Subcommands ─────────────────────────────────────────────────────────────
def cmd_login(args):
    get_credentials(args.account, SCOPES["analytics_readonly"])
    print(f"✅ Logged in (Analytics scopes) as {args.account}")
    print(f"   Token: {token_path(args.account)}")


def cmd_list_accounts(args):
    svc = admin_service(args.account)
    res = svc.accounts().list().execute()
    accounts = res.get("accounts", [])
    if not accounts:
        print("(no accounts accessible from this Google account)")
        return
    print(f"📂 {len(accounts)} Google Analytics account(s) accessible:\n")
    for a in accounts:
        print(f"  • {a.get('displayName','(no name)')}")
        print(f"      account id : {a.get('name','').replace('accounts/','')}")
        print(f"      create time: {a.get('createTime','—')[:10]}")
        print(f"      region     : {a.get('regionCode','—')}")
        print()


def cmd_list_properties(args):
    """
    The GA Admin API only accepts ONE parent filter per request, so we iterate.
    """
    svc = admin_service(args.account)

    if args.account_id:
        # Resolve the display name for nicer output
        try:
            acc = svc.accounts().get(name=f"accounts/{args.account_id}").execute()
            accounts = [(args.account_id, acc.get("displayName", "(no name)"))]
        except HttpError:
            accounts = [(args.account_id, "(?)")]
    else:
        acc_res = svc.accounts().list().execute()
        accounts = [
            (a["name"].replace("accounts/", ""), a.get("displayName", "(no name)"))
            for a in acc_res.get("accounts", [])
        ]
        if not accounts:
            print("(no accessible accounts)")
            return

    all_props = []
    for acc_id, acc_name in accounts:
        try:
            res = svc.properties().list(filter=f"parent:accounts/{acc_id}").execute()
        except HttpError as e:
            print(f"  ⚠️  Skipping account {acc_id} ({acc_name}): {e.reason}", file=sys.stderr)
            continue
        for p in res.get("properties", []):
            p["_account_name"] = acc_name
            p["_account_id"] = acc_id
            all_props.append(p)

    if not all_props:
        print("(no GA4 properties found)")
        return

    if args.json:
        print(json.dumps(all_props, indent=2, ensure_ascii=False))
        return

    print(f"📊 {len(all_props)} GA4 propert{'y' if len(all_props)==1 else 'ies'}:\n")
    for p in all_props:
        pid = p.get("name", "").replace("properties/", "")
        print(f"  • {p.get('displayName','(no name)')}")
        print(f"      property id  : {pid}")
        print(f"      account      : {p.get('_account_name','—')} ({p.get('_account_id','—')})")
        print(f"      time zone    : {p.get('timeZone','—')}")
        print(f"      currency     : {p.get('currencyCode','—')}")
        print(f"      industry     : {p.get('industryCategory','—')}")
        print(f"      create time  : {p.get('createTime','—')[:10]}")
        print()


def _print_report(report: dict, args):
    headers = (
        [d["name"] for d in report.get("dimensionHeaders", [])]
        + [m["name"] for m in report.get("metricHeaders", [])]
    )
    rows = report.get("rows", [])
    if not rows:
        print("(no data for this period)")
        return

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    # Pretty print as table
    widths = [max(len(h), 4) for h in headers]
    table = []
    for r in rows:
        vals = [d["value"] for d in r.get("dimensionValues", [])] + [
            m["value"] for m in r.get("metricValues", [])
        ]
        widths = [max(w, len(str(v))) for w, v in zip(widths, vals)]
        table.append(vals)

    fmt = " │ ".join(f"{{:<{w}}}" for w in widths)
    sep = "─┼─".join("─" * w for w in widths)
    print(fmt.format(*headers))
    print(sep)
    for row in table:
        print(fmt.format(*row))

    totals = report.get("totals", [])
    if totals:
        print(sep)
        for t in totals:
            vals = ["TOTAL"] * len(report.get("dimensionHeaders", []))
            vals += [m["value"] for m in t.get("metricValues", [])]
            print(fmt.format(*vals))


def cmd_report(args):
    svc = data_service(args.account)
    property_id = fmt_property_id(args.property)

    body = {
        "dateRanges": [{"startDate": args.since, "endDate": args.until}],
        "dimensions": [{"name": d} for d in parse_list(args.dimensions)],
        "metrics": [{"name": m} for m in parse_list(args.metrics)],
        "limit": args.limit,
    }
    if args.order_by:
        body["orderBys"] = [{
            "metric": {"metricName": args.order_by},
            "desc": True,
        }]

    try:
        report = svc.properties().runReport(property=property_id, body=body).execute()
    except HttpError as e:
        sys.exit(f"❌ GA4 API error: {e}")

    print(f"📊 Report — property {args.property} — {args.since} → {args.until}\n")
    _print_report(report, args)


def cmd_realtime(args):
    svc = data_service(args.account)
    property_id = fmt_property_id(args.property)

    body = {
        "dimensions": [{"name": d} for d in parse_list(args.dimensions)],
        "metrics": [{"name": m} for m in parse_list(args.metrics)],
        "limit": args.limit,
    }
    try:
        report = svc.properties().runRealtimeReport(property=property_id, body=body).execute()
    except HttpError as e:
        sys.exit(f"❌ GA4 API error: {e}")

    print(f"⚡ Realtime — property {args.property}\n")
    _print_report(report, args)


# ── CLI parser ──────────────────────────────────────────────────────────────
def make_parser():
    p = argparse.ArgumentParser(prog="ga4_cli", description="Multi-account GA4 CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp):
        sp.add_argument("--account", required=True, help="Google account email")

    sp = sub.add_parser("login", help="Authorize Analytics scopes")
    add_common(sp); sp.set_defaults(func=cmd_login)

    sp = sub.add_parser("list-accounts", help="List GA accounts you can access")
    add_common(sp); sp.set_defaults(func=cmd_list_accounts)

    sp = sub.add_parser("list-properties", help="List GA4 properties")
    add_common(sp)
    sp.add_argument("--account-id", help="(Optional) Filter to one GA account ID")
    sp.add_argument("--json", action="store_true", help="Output raw JSON")
    sp.set_defaults(func=cmd_list_properties)

    def add_report_args(sp):
        add_common(sp)
        sp.add_argument("--property", "-p", required=True,
                        help="GA4 property ID (e.g. 534094689 or properties/534094689)")
        sp.add_argument("--metrics", "-m", required=True,
                        help="Comma-separated metrics (e.g. sessions,conversions,activeUsers)")
        sp.add_argument("--dimensions", "-d", default="",
                        help="Comma-separated dimensions (e.g. sessionDefaultChannelGroup,country)")
        sp.add_argument("--limit", type=int, default=25)
        sp.add_argument("--order-by", help="Metric to order by (descending)")
        sp.add_argument("--json", action="store_true", help="Output raw JSON")

    sp = sub.add_parser("report", help="Run a historical report")
    add_report_args(sp)
    sp.add_argument("--since", default="7daysAgo",
                    help="Start date (e.g. 7daysAgo, 2026-01-01)")
    sp.add_argument("--until", default="today",
                    help="End date (e.g. today, yesterday, 2026-02-01)")
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("realtime", help="Realtime report (last ~30 min)")
    add_report_args(sp)
    sp.set_defaults(func=cmd_realtime)

    return p


def main():
    args = make_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

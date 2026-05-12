#!/usr/bin/env python3
"""
gtm_cli — Multi-account Google Tag Manager CLI for Adspubli

Subcommands:
  login            --account X
  list-accounts    --account X
  list-containers  --account X --account-id N
  list-workspaces  --account X --account-id N --container-id N
  list-tags        --account X --account-id N --container-id N [--workspace-id N]
  list-triggers    --account X --account-id N --container-id N [--workspace-id N]
  list-variables   --account X --account-id N --container-id N [--workspace-id N]
  get-snippet      --account X --account-id N --container-id N
  publish          --account X --account-id N --container-id N [--workspace-id N]

Uses the Tag Manager API v2.
"""
from __future__ import annotations

import argparse
import json
import sys

from googleapiclient.errors import HttpError

from _auth import SCOPES, get_credentials, service, token_path


# ── Service builder ──────────────────────────────────────────────────────────
def gtm_service(account: str, edit: bool = False):
    scope_key = "tagmanager_edit" if edit else "tagmanager_readonly"
    return service(account, "tagmanager", "v2", SCOPES[scope_key])


# ── Helpers ──────────────────────────────────────────────────────────────────
def account_path(account_id: str) -> str:
    return f"accounts/{account_id}"


def container_path(account_id: str, container_id: str) -> str:
    return f"accounts/{account_id}/containers/{container_id}"


def workspace_path(account_id: str, container_id: str, workspace_id: str) -> str:
    return f"accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}"


def get_default_workspace(svc, account_id: str, container_id: str) -> str:
    """Return the first workspace id (usually 'Default Workspace')."""
    res = svc.accounts().containers().workspaces().list(
        parent=container_path(account_id, container_id)
    ).execute()
    ws = res.get("workspace", [])
    if not ws:
        sys.exit("❌ No workspaces found in this container.")
    # Prefer the one named 'Default Workspace'
    for w in ws:
        if "Default" in w.get("name", ""):
            return w["workspaceId"]
    return ws[0]["workspaceId"]


# ── Subcommands ──────────────────────────────────────────────────────────────
def cmd_login(args):
    scope_key = "tagmanager_edit" if args.edit else "tagmanager_readonly"
    get_credentials(args.account, SCOPES[scope_key])
    print(f"✅ Logged in (Tag Manager {'edit' if args.edit else 'readonly'} scopes) as {args.account}")
    print(f"   Token: {token_path(args.account)}")


def cmd_list_accounts(args):
    svc = gtm_service(args.account)
    res = svc.accounts().list().execute()
    accounts = res.get("account", [])
    if not accounts:
        print("(no GTM accounts accessible)")
        return

    if args.json:
        print(json.dumps(accounts, indent=2, ensure_ascii=False))
        return

    print(f"📂 {len(accounts)} GTM account(s):\n")
    for a in accounts:
        print(f"  • {a.get('name', '(no name)')}")
        print(f"      account id : {a.get('accountId', '—')}")
        print(f"      fingerprint: {a.get('fingerprint', '—')[:12]}...")
        print()


def cmd_list_containers(args):
    svc = gtm_service(args.account)
    try:
        res = svc.accounts().containers().list(
            parent=account_path(args.account_id)
        ).execute()
    except HttpError as e:
        sys.exit(f"❌ GTM API error: {e}")

    containers = res.get("container", [])
    if not containers:
        print("(no containers in this account)")
        return

    if args.json:
        print(json.dumps(containers, indent=2, ensure_ascii=False))
        return

    print(f"📦 {len(containers)} container(s) in account {args.account_id}:\n")
    for c in containers:
        print(f"  • {c.get('name', '(no name)')}")
        print(f"      container id : {c.get('containerId', '—')}")
        print(f"      public id    : {c.get('publicId', '—')}  ← GTM-XXXXXX")
        print(f"      domain hint  : {', '.join(c.get('domainName', [])) or '—'}")
        print(f"      usage context: {', '.join(c.get('usageContext', [])) or '—'}")
        print()


def cmd_list_workspaces(args):
    svc = gtm_service(args.account)
    try:
        res = svc.accounts().containers().workspaces().list(
            parent=container_path(args.account_id, args.container_id)
        ).execute()
    except HttpError as e:
        sys.exit(f"❌ GTM API error: {e}")

    workspaces = res.get("workspace", [])
    if not workspaces:
        print("(no workspaces)")
        return

    if args.json:
        print(json.dumps(workspaces, indent=2, ensure_ascii=False))
        return

    print(f"🗂️  {len(workspaces)} workspace(s):\n")
    for w in workspaces:
        print(f"  • {w.get('name', '(no name)')}")
        print(f"      workspace id : {w.get('workspaceId', '—')}")
        print(f"      description  : {w.get('description', '—')}")
        print()


def _list_entities(svc, args, entity: str):
    """Generic lister for tags / triggers / variables."""
    ws_id = args.workspace_id or get_default_workspace(svc, args.account_id, args.container_id)
    ws = workspace_path(args.account_id, args.container_id, ws_id)

    try:
        collection = getattr(svc.accounts().containers().workspaces(), entity + "s")
        res = collection().list(parent=ws).execute()
    except HttpError as e:
        sys.exit(f"❌ GTM API error: {e}")

    items = res.get(entity, [])
    if not items:
        print(f"(no {entity}s in workspace {ws_id})")
        return

    if args.json:
        print(json.dumps(items, indent=2, ensure_ascii=False))
        return

    emoji = {"tag": "🏷️ ", "trigger": "⚡", "variable": "📐"}[entity]
    print(f"{emoji} {len(items)} {entity}(s) in workspace {ws_id}:\n")
    for item in items:
        name = item.get("name", "(no name)")
        item_id = item.get(f"{entity}Id", "—")
        type_ = item.get("type", "—")
        print(f"  • [{item_id}] {name}  ({type_})")


def cmd_list_tags(args):
    _list_entities(gtm_service(args.account), args, "tag")


def cmd_list_triggers(args):
    _list_entities(gtm_service(args.account), args, "trigger")


def cmd_list_variables(args):
    _list_entities(gtm_service(args.account), args, "variable")


def cmd_get_snippet(args):
    svc = gtm_service(args.account)
    try:
        container = svc.accounts().containers().get(
            path=container_path(args.account_id, args.container_id)
        ).execute()
    except HttpError as e:
        sys.exit(f"❌ GTM API error: {e}")

    public_id = container.get("publicId", "?")
    name = container.get("name", "?")

    if args.json:
        print(json.dumps({"publicId": public_id, "name": name}, indent=2))
        return

    print(f"🏷️  Container: {name}  (GTM ID: {public_id})\n")
    print("── Head snippet ──────────────────────────────────────────────────────")
    print(f"""<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
}})(window,document,'script','dataLayer','{public_id}');</script>
<!-- End Google Tag Manager -->""")
    print("\n── Body snippet (just after <body>) ──────────────────────────────────")
    print(f"""<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={public_id}"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->""")


def cmd_publish(args):
    svc = gtm_service(args.account, edit=True)
    ws_id = args.workspace_id or get_default_workspace(svc, args.account_id, args.container_id)
    ws = workspace_path(args.account_id, args.container_id, ws_id)

    print(f"⚠️  About to publish workspace {ws_id} of container {args.container_id}.")
    confirm = input("Type 'yes' to confirm: ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        return

    try:
        result = svc.accounts().containers().workspaces().create_version(
            path=ws, body={"name": "Published via gtm CLI", "notes": ""}
        ).execute()
    except HttpError as e:
        sys.exit(f"❌ GTM API error: {e}")

    version = result.get("containerVersion", {})
    version_id = version.get("containerVersionId", "?")
    print(f"✅ Version {version_id} created. Publishing...")

    try:
        svc.accounts().containers().versions().publish(
            path=f"accounts/{args.account_id}/containers/{args.container_id}/versions/{version_id}"
        ).execute()
        print(f"✅ Published! Container {args.container_id} → version {version_id}")
    except HttpError as e:
        sys.exit(f"❌ Publish error: {e}")


# ── CLI parser ───────────────────────────────────────────────────────────────
def make_parser():
    p = argparse.ArgumentParser(prog="gtm", description="Multi-account Google Tag Manager CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_account(sp):
        sp.add_argument("--account", required=True, help="Google account email")

    def add_account_container(sp):
        add_account(sp)
        sp.add_argument("--account-id", required=True, help="GTM account ID (numeric)")
        sp.add_argument("--container-id", required=True, help="GTM container ID (numeric)")

    def add_workspace_opt(sp):
        sp.add_argument("--workspace-id", default=None,
                        help="Workspace ID (default: first/Default workspace)")

    def add_json(sp):
        sp.add_argument("--json", action="store_true", help="Output raw JSON")

    # login
    sp = sub.add_parser("login", help="Authorize Tag Manager scopes")
    add_account(sp)
    sp.add_argument("--edit", action="store_true", help="Request edit+publish scopes (default: readonly)")
    sp.set_defaults(func=cmd_login)

    # list-accounts
    sp = sub.add_parser("list-accounts", help="List GTM accounts you can access")
    add_account(sp); add_json(sp)
    sp.set_defaults(func=cmd_list_accounts)

    # list-containers
    sp = sub.add_parser("list-containers", help="List containers in a GTM account")
    add_account(sp)
    sp.add_argument("--account-id", required=True)
    add_json(sp)
    sp.set_defaults(func=cmd_list_containers)

    # list-workspaces
    sp = sub.add_parser("list-workspaces", help="List workspaces in a container")
    add_account_container(sp); add_json(sp)
    sp.set_defaults(func=cmd_list_workspaces)

    # list-tags / list-triggers / list-variables
    for name, func in [("list-tags", cmd_list_tags),
                       ("list-triggers", cmd_list_triggers),
                       ("list-variables", cmd_list_variables)]:
        sp = sub.add_parser(name)
        add_account_container(sp); add_workspace_opt(sp); add_json(sp)
        sp.set_defaults(func=func)

    # get-snippet
    sp = sub.add_parser("get-snippet", help="Print GTM installation snippets for a container")
    add_account_container(sp); add_json(sp)
    sp.set_defaults(func=cmd_get_snippet)

    # publish
    sp = sub.add_parser("publish", help="Publish a workspace (creates version + publishes)")
    add_account_container(sp); add_workspace_opt(sp)
    sp.set_defaults(func=cmd_publish)

    return p


def main():
    args = make_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

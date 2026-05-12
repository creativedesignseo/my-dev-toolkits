#!/usr/bin/env python3
"""
gmail_cli — Multi-account Gmail CLI for Adspubli
Subcommands:
  login    --account <email>             # OAuth flow, stores token
  draft    --account X --to Y --subject Z [--body T | --body-file F] [--cc ...] [--bcc ...] [--attach FILE ...]
  send     (same as draft, but sends immediately)
  list     --account X [--query Q] [--max N]
  read     --account X --thread-id ID
  whoami   --account X
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
from email.message import EmailMessage
from pathlib import Path

from googleapiclient.errors import HttpError

# Shared auth helpers (token storage, OAuth flow, incremental scopes)
from _auth import SCOPES, get_credentials, service, token_path


def gmail_service(account: str):
    return service(account, "gmail", "v1", SCOPES["gmail"])


# ── Message builder ─────────────────────────────────────────────────────────
def build_message(args) -> str:
    """Build a base64url-encoded RFC 5322 message."""
    msg = EmailMessage()
    # --from-addr overrides the From header (useful for Workspace "Send as" aliases).
    # Falls back to --account if not provided.
    msg["From"] = getattr(args, "from_addr", None) or args.account
    msg["To"] = ", ".join(args.to)
    if args.cc:
        msg["Cc"] = ", ".join(args.cc)
    if args.bcc:
        msg["Bcc"] = ", ".join(args.bcc)
    msg["Subject"] = args.subject or ""

    body = args.body or ""
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    msg.set_content(body or "(empty)")

    if args.html_body or args.html_body_file:
        html = args.html_body or ""
        if args.html_body_file:
            html = Path(args.html_body_file).read_text(encoding="utf-8")
        msg.add_alternative(html, subtype="html")

    if args.attach:
        for path in args.attach:
            p = Path(path)
            if not p.is_file():
                sys.exit(f"❌ Attachment not found: {p}")
            ctype, _ = mimetypes.guess_type(str(p))
            maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
            msg.add_attachment(
                p.read_bytes(),
                maintype=maintype,
                subtype=subtype,
                filename=p.name,
            )

    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


# ── Subcommands ─────────────────────────────────────────────────────────────
def cmd_login(args):
    get_credentials(args.account, SCOPES["gmail"])
    print(f"✅ Logged in as {args.account}")
    print(f"   Token: {token_path(args.account)}")


def cmd_whoami(args):
    svc = gmail_service(args.account)
    profile = svc.users().getProfile(userId="me").execute()
    print(json.dumps(profile, indent=2, ensure_ascii=False))


def cmd_draft(args):
    svc = gmail_service(args.account)
    raw = build_message(args)
    try:
        draft = svc.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}},
        ).execute()
    except HttpError as e:
        sys.exit(f"❌ Gmail API error: {e}")
    print(f"✅ Draft created — id={draft['id']} messageId={draft['message']['id']}")
    print(f"   Open: https://mail.google.com/mail/u/?authuser={args.account}#drafts/{draft['message']['id']}")


def cmd_send(args):
    svc = gmail_service(args.account)
    raw = build_message(args)
    try:
        sent = svc.users().messages().send(
            userId="me",
            body={"raw": raw},
        ).execute()
    except HttpError as e:
        sys.exit(f"❌ Gmail API error: {e}")
    print(f"✅ Sent — id={sent['id']} threadId={sent['threadId']}")


def cmd_list(args):
    svc = gmail_service(args.account)
    res = svc.users().messages().list(
        userId="me",
        q=args.query or "",
        maxResults=args.max,
    ).execute()
    msgs = res.get("messages", [])
    if not msgs:
        print("(no messages)")
        return
    for m in msgs:
        meta = svc.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
        ).execute()
        hdrs = {h["name"]: h["value"] for h in meta["payload"]["headers"]}
        snippet = meta.get("snippet", "")[:80]
        print(f"• {m['id']}  {hdrs.get('Date', '')[:25]}")
        print(f"  From: {hdrs.get('From', '')}")
        print(f"  Subject: {hdrs.get('Subject', '')}")
        print(f"  {snippet}")
        print()


def cmd_read(args):
    svc = gmail_service(args.account)
    thread = svc.users().threads().get(userId="me", id=args.thread_id, format="full").execute()
    for m in thread["messages"]:
        hdrs = {h["name"]: h["value"] for h in m["payload"]["headers"]}
        print(f"━━━ {hdrs.get('Date','')}")
        print(f"From: {hdrs.get('From','')}")
        print(f"To: {hdrs.get('To','')}")
        print(f"Subject: {hdrs.get('Subject','')}")
        print()
        # Extract text/plain body
        def walk(part):
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
            for sub in part.get("parts", []) or []:
                txt = walk(sub)
                if txt:
                    return txt
            return None
        body = walk(m["payload"]) or m.get("snippet", "")
        print(body[:2000])
        print()


# ── CLI parser ──────────────────────────────────────────────────────────────
def make_parser():
    p = argparse.ArgumentParser(prog="gmail_cli", description="Multi-account Gmail CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp):
        sp.add_argument("--account", required=True, help="Email account, e.g. info@adspubli.com")

    sp = sub.add_parser("login", help="Run OAuth flow")
    add_common(sp); sp.set_defaults(func=cmd_login)

    sp = sub.add_parser("whoami", help="Show authenticated profile")
    add_common(sp); sp.set_defaults(func=cmd_whoami)

    def add_message_args(sp):
        add_common(sp)
        sp.add_argument("--from", dest="from_addr", default=None,
                        help="Override From header (must be a verified 'Send as' alias of --account)")
        sp.add_argument("--to", nargs="+", required=True)
        sp.add_argument("--cc", nargs="*", default=[])
        sp.add_argument("--bcc", nargs="*", default=[])
        sp.add_argument("--subject", default="")
        sp.add_argument("--body", default=None)
        sp.add_argument("--body-file", default=None)
        sp.add_argument("--html-body", default=None)
        sp.add_argument("--html-body-file", default=None)
        sp.add_argument("--attach", nargs="*", default=[], help="Paths to attachments")

    sp = sub.add_parser("draft", help="Create a draft (don't send)")
    add_message_args(sp); sp.set_defaults(func=cmd_draft)

    sp = sub.add_parser("send", help="Send a message")
    add_message_args(sp); sp.set_defaults(func=cmd_send)

    sp = sub.add_parser("list", help="List recent messages")
    add_common(sp)
    sp.add_argument("--query", "-q", default="", help="Gmail search query")
    sp.add_argument("--max", type=int, default=10)
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("read", help="Read a thread")
    add_common(sp)
    sp.add_argument("--thread-id", required=True)
    sp.set_defaults(func=cmd_read)

    return p


def main():
    args = make_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

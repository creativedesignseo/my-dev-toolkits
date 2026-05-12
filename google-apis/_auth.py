"""
_auth.py — shared OAuth 2.0 helper for all *_cli.py tools in this package.

Responsibilities:
- Load existing token for an account.
- Detect if NEW scopes are required vs what was already granted.
- If new scopes are needed, run the OAuth Installed App flow with the UNION
  of (already granted ∪ newly required) so the token grows incrementally.
- Refresh expired tokens transparently.
- Map account → client_secret file via accounts.json.

This is intentionally NOT a CLI — it's imported by gmail_cli, ga4_cli, gsc_cli, etc.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
CREDS_DIR = ROOT / "credentials"
TOKENS_DIR = CREDS_DIR / "tokens"
ACCOUNTS_MAP = ROOT / "accounts.json"
TOKENS_DIR.mkdir(parents=True, exist_ok=True)


# ── Scope registry (single source of truth for which scope each CLI uses) ───
SCOPES = {
    "gmail":               ["https://mail.google.com/"],
    "analytics_readonly":  ["https://www.googleapis.com/auth/analytics.readonly"],
    "webmasters_readonly": ["https://www.googleapis.com/auth/webmasters.readonly"],
    "drive_readonly":      ["https://www.googleapis.com/auth/drive.readonly"],
    "tagmanager_readonly": ["https://www.googleapis.com/auth/tagmanager.readonly"],
    "tagmanager_edit":     ["https://www.googleapis.com/auth/tagmanager.edit.containers",
                            "https://www.googleapis.com/auth/tagmanager.publish"],
}


# ── account → client_secret mapping ─────────────────────────────────────────
def client_secret_for(account: str) -> Path:
    if not ACCOUNTS_MAP.exists():
        sys.exit(f"❌ Missing {ACCOUNTS_MAP}")
    mapping = json.loads(ACCOUNTS_MAP.read_text())
    fname = mapping.get(account) or mapping.get("_default")
    if not fname:
        sys.exit(
            f"❌ No client_secret mapped for {account}. "
            f"Edit {ACCOUNTS_MAP} to add it."
        )
    path = CREDS_DIR / fname
    if not path.exists():
        sys.exit(f"❌ {path} not found (referenced from accounts.json for {account})")
    return path


def token_path(account: str) -> Path:
    safe = account.replace("@", "_at_").replace(".", "_")
    return TOKENS_DIR / f"{safe}.json"


def _load_existing_scopes(tp: Path) -> list[str]:
    if not tp.exists():
        return []
    try:
        return json.loads(tp.read_text()).get("scopes") or []
    except Exception:
        return []


# ── Main entry point ────────────────────────────────────────────────────────
def get_credentials(account: str, required_scopes: list[str]) -> Credentials:
    """
    Return valid Credentials covering ALL required_scopes.

    Strategy:
    1. If token exists AND already covers required_scopes → load it (refresh if expired).
    2. If token covers SOME but not all → re-run OAuth with UNION of scopes (token grows).
    3. If no token → run OAuth with required_scopes.
    """
    tp = token_path(account)
    existing = _load_existing_scopes(tp)
    union = sorted(set(existing) | set(required_scopes))
    missing = sorted(set(required_scopes) - set(existing))

    # Path 1: token covers what we need
    if tp.exists() and not missing:
        creds = Credentials.from_authorized_user_file(str(tp), union)
        if creds.valid:
            return creds
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                tp.write_text(creds.to_json())
                return creds
            except Exception as e:
                print(f"⚠️  Refresh failed for {account}: {e}", file=sys.stderr)
                print("   Re-running OAuth flow...", file=sys.stderr)

    # Path 2 & 3: need to (re-)authorize
    cs = client_secret_for(account)
    if missing and existing:
        print(f"🔑 New scopes required for {account}.", file=sys.stderr)
        print(f"   Adding: {missing}", file=sys.stderr)
        print(f"   Browser will open — authorize the additional permissions.", file=sys.stderr)
    else:
        print(f"🔑 Using OAuth client: {cs.name}", file=sys.stderr)

    flow = InstalledAppFlow.from_client_secrets_file(str(cs), union)
    creds = flow.run_local_server(
        port=0,
        prompt="consent",
        login_hint=account,
        access_type="offline",
        open_browser=True,
        authorization_prompt_message=(
            "🔑 Open this URL in your browser to authorize:\n{url}"
        ),
        success_message="✅ Auth complete — you can close this tab.",
    )
    tp.write_text(creds.to_json())
    return creds


def service(account: str, api: str, version: str, required_scopes: list[str]):
    """Convenience wrapper: get_credentials + build service in one call."""
    creds = get_credentials(account, required_scopes)
    return build(api, version, credentials=creds, cache_discovery=False)

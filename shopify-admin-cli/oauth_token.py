#!/usr/bin/env python3
"""
shopify-admin OAuth token helper
=================================
Starts a local HTTP server on port 3000, prints the authorization URL,
waits for the callback, exchanges the code for an access token, and
saves it to /tmp/shopify_token.json.

Usage:
    python3 oauth_token.py --shop piroaccessories.myshopify.com

After the token is printed, run:
    shopify-admin config add --store ALIAS --domain SHOP --token shpca_XXX
"""

import argparse
import http.server
import json
import pathlib
import threading
import urllib.parse
import urllib.request

PORT       = 3000
TOKEN_FILE = "/tmp/shopify_token.json"
_APP_FILE  = pathlib.Path.home() / ".shopify-admin" / "app.json"


def _load_app_credentials() -> tuple[str, str, str]:
    """Load client_id, client_secret, redirect_uri from ~/.shopify-admin/app.json."""
    if not _APP_FILE.exists():
        raise SystemExit(
            f"[!] App credentials not found at {_APP_FILE}\n"
            "    Create it with:\n"
            '    {\n'
            '      "client_id": "YOUR_CLIENT_ID",\n'
            '      "client_secret": "YOUR_CLIENT_SECRET",\n'
            '      "redirect_uri": "http://localhost:3000/callback"\n'
            '    }\n'
            "    Get these from: https://dev.shopify.com/dashboard/{ORG}/apps/{APP_ID}/settings"
        )
    with open(_APP_FILE) as f:
        creds = json.load(f)
    return (
        creds["client_id"],
        creds["client_secret"],
        creds.get("redirect_uri", "http://localhost:3000/callback"),
    )


CLIENT_ID, CLIENT_SECRET, REDIRECT_URI = _load_app_credentials()

SCOPES = ",".join([
    "read_customers", "write_customers",
    "read_price_rules", "write_price_rules",
    "write_draft_orders", "read_draft_orders",
    "read_markets",
    "read_orders", "write_orders",
    "read_products", "write_products",
    "read_publications", "write_publications",
])


def exchange_code(shop: str, code: str) -> dict:
    payload = json.dumps({
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code":          code,
    }).encode()
    req = urllib.request.Request(
        f"https://{shop}/admin/oauth/access_token",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def make_handler(shop: str, result: dict, server_ref: list):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            code = (params.get("code") or [None])[0]
            if not code:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"No code in callback")
                return

            print(f"\n[+] Code received ({code[:10]}...)", flush=True)
            try:
                data = exchange_code(shop, code)
            except Exception as exc:
                print(f"[!] Exchange failed: {exc}", flush=True)
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(exc).encode())
                return

            token = data.get("access_token", "")
            scope = data.get("scope", "")
            result["token"] = token
            result["scope"] = scope

            with open(TOKEN_FILE, "w") as f:
                json.dump({"shop": shop, "access_token": token, "scope": scope}, f, indent=2)

            print(f"\n{'='*60}", flush=True)
            print(f"  ACCESS TOKEN : {token}", flush=True)
            print(f"  Scope        : {scope}", flush=True)
            print(f"  Saved to     : {TOKEN_FILE}", flush=True)
            print(f"{'='*60}\n", flush=True)
            print(f"  Next step:", flush=True)
            print(f"  shopify-admin config add --store ALIAS \\", flush=True)
            print(f"    --domain {shop} \\", flush=True)
            print(f"    --token {token}", flush=True)
            print(f"\n{'='*60}\n", flush=True)

            self.send_response(200)
            self.end_headers()
            body = f"<h1>Token obtained!</h1><pre>Token: {token}\nScope: {scope}</pre><p>Close this tab.</p>"
            self.wfile.write(body.encode())

            threading.Thread(target=server_ref[0].shutdown, daemon=True).start()

        def log_message(self, *_):
            pass  # silence access log

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Shopify OAuth token helper for Adspubli CLI")
    parser.add_argument("--shop", required=True, help="myshopify domain, e.g. piroaccessories.myshopify.com")
    args = parser.parse_args()
    shop = args.shop.strip().rstrip("/")

    auth_url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&scope={urllib.parse.quote(SCOPES)}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&state=adspubli_{shop.split('.')[0]}"
    )

    print(f"\n{'='*60}", flush=True)
    print(f"  Shopify OAuth — Adspubli CLI", flush=True)
    print(f"  Store : {shop}", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"\n[1] Make sure the app is installed on this store first.", flush=True)
    print(f"    Install link: https://partners.shopify.com/3062121/apps/362282516481/distribution\n", flush=True)
    print(f"[2] Navigate to this URL in the browser session authenticated", flush=True)
    print(f"    as staff/owner of {shop}:\n", flush=True)
    print(f"    {auth_url}\n", flush=True)
    print(f"[3] Waiting for callback on http://localhost:{PORT}/callback ...\n", flush=True)

    result: dict = {}
    server_ref: list = [None]
    handler = make_handler(shop, result, server_ref)
    srv = http.server.HTTPServer(("localhost", PORT), handler)
    server_ref[0] = srv
    srv.serve_forever()


if __name__ == "__main__":
    main()

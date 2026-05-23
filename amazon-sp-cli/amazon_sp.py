#!/usr/bin/env python3
"""
amazon-sp — CLI directo para Amazon Selling Partner API (SP-API)
Adspubli · mcp-toolkits/repo/amazon-sp-cli/

Usa python-amazon-sp-api (saleweaver) bajo un venv aislado en .venv/.
Credenciales se leen desde .env.amazon en una de estas ubicaciones (primera que exista):

  1. ~/.env.amazon
  2. ~/Documents/Workspace/Clients/pirojewelry.com/.env.amazon

Formato del archivo .env.amazon:

  AMAZON_LWA_CLIENT_ID=amzn1.application-oa2-client.xxxxx
  AMAZON_LWA_CLIENT_SECRET=xxxxxxxxxxxx
  AMAZON_REFRESH_TOKEN=Atzr|IwEBIxxxxxxxx
  AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER     # opcional, default US

Uso:
  amazon-sp shop                # info de la cuenta seller, verificar conexion
  amazon-sp config show         # ver credenciales cargadas (enmascaradas)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ─── Config ────────────────────────────────────────────────────────────────────

ENV_LOCATIONS = [
    Path.home() / ".env.amazon",
    Path.home() / "Documents" / "Workspace" / "Clients" / "pirojewelry.com" / ".env.amazon",
]

DEFAULT_MARKETPLACE_ID = "ATVPDKIKX0DER"  # Amazon.com (US)


# ─── Env loader ────────────────────────────────────────────────────────────────

def load_env() -> dict:
    """Lee el primer .env.amazon que encuentre y devuelve un dict de variables."""
    for path in ENV_LOCATIONS:
        if path.exists():
            env: dict = {}
            for raw in path.read_text().splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
            env["_source"] = str(path)
            return env

    paths = "\n    ".join(str(p) for p in ENV_LOCATIONS)
    die(
        "No se encontro .env.amazon en ninguna ubicacion conocida:\n"
        f"    {paths}\n\n"
        "Crea uno con el formato:\n"
        "    AMAZON_LWA_CLIENT_ID=amzn1.application-oa2-client.xxxxx\n"
        "    AMAZON_LWA_CLIENT_SECRET=xxxxxxxxxxxx\n"
        "    AMAZON_REFRESH_TOKEN=Atzr|IwEBIxxxxxxxx\n"
        "    AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER     # opcional"
    )


def get_credentials(env: dict) -> dict:
    """Construye el dict de credenciales en el formato que espera python-amazon-sp-api."""
    required = [
        "AMAZON_LWA_CLIENT_ID",
        "AMAZON_LWA_CLIENT_SECRET",
        "AMAZON_REFRESH_TOKEN",
    ]
    missing = [k for k in required if not env.get(k)]
    if missing:
        die(
            f"Faltan variables en {env.get('_source','env')}:\n"
            f"    {', '.join(missing)}"
        )

    return {
        "lwa_app_id":        env["AMAZON_LWA_CLIENT_ID"],
        "lwa_client_secret": env["AMAZON_LWA_CLIENT_SECRET"],
        "refresh_token":     env["AMAZON_REFRESH_TOKEN"],
    }


def get_marketplace(env: dict):
    """Devuelve el enum Marketplaces correspondiente al marketplace ID configurado."""
    from sp_api.base import Marketplaces

    target_id = env.get("AMAZON_MARKETPLACE_ID", DEFAULT_MARKETPLACE_ID)

    for m in Marketplaces:
        if getattr(m, "marketplace_id", None) == target_id:
            return m

    eprint(
        f"  Aviso: marketplace ID '{target_id}' no reconocido por la libreria, "
        f"usando Marketplaces.US como fallback."
    )
    return Marketplaces.US


# ─── Helpers ───────────────────────────────────────────────────────────────────

def die(msg: str) -> None:
    print(f"\nError: {msg}\n", file=sys.stderr)
    sys.exit(1)


def eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def out_json(data) -> None:
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


def hr(label: str = "", width: int = 60) -> None:
    if label:
        print(f"\n  {label}")
    print(f"  {'─' * width}")


def require_sp_api() -> None:
    """Falla con un mensaje claro si python-amazon-sp-api no esta instalada."""
    try:
        import sp_api  # noqa: F401
    except ImportError:
        die(
            "python-amazon-sp-api no esta instalada.\n"
            "    Ejecuta el instalador del CLI:\n"
            "      bash ~/Documents/Workspace/mcp-toolkits/repo/amazon-sp-cli/install.sh\n"
            "    Esto crea un venv local con la libreria."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SHOP — info de la cuenta seller y verificacion de conexion
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_shop(args):
    require_sp_api()

    env         = load_env()
    creds       = get_credentials(env)
    marketplace = get_marketplace(env)

    from sp_api.api import Sellers
    from sp_api.base.exceptions import SellingApiException

    try:
        client = Sellers(credentials=creds, marketplace=marketplace)
        result = client.get_marketplace_participation()
    except SellingApiException as e:
        die(f"SP-API devolvio un error:\n    {e}")
    except Exception as e:
        die(f"No se pudo conectar con SP-API:\n    {type(e).__name__}: {e}")

    payload = result.payload or []

    if args.json:
        out_json(payload)
        return

    hr(f"Cuenta seller — {len(payload)} marketplace(s) activos")
    print(f"  Credenciales      : {env.get('_source','?')}")
    print(f"  Marketplace base  : {marketplace.name}  ({marketplace.marketplace_id})")
    print()

    if not payload:
        print("  (no se encontraron participaciones — verifica que la app este self-authorized)")
        return

    for p in payload:
        m    = p.get("marketplace")    or {}
        part = p.get("participation")  or {}

        name    = m.get("name", "?")
        country = m.get("countryCode", "?")
        mid     = m.get("id", "?")
        curr    = m.get("defaultCurrencyCode", "?")
        lang    = m.get("defaultLanguageCode", "?")
        domain  = m.get("domainName", "?")

        active   = part.get("isParticipating")
        sus      = part.get("hasSuspendedListings")

        marker_a = "✓ vendiendo"  if active else "✗ sin venta"
        marker_s = "  ⚠ suspendidos" if sus else ""

        print(f"  {name}  ({country})  —  {marker_a}{marker_s}")
        print(f"    Marketplace ID : {mid}")
        print(f"    Moneda         : {curr}     Idioma: {lang}")
        print(f"    Dominio        : {domain}")
        print()

    print("  ✓ Conexion OK")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG — mostrar credenciales cargadas (enmascaradas)
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_config_show(args):
    env    = load_env()
    masked = dict(env)
    for k, v in list(masked.items()):
        if k == "_source":
            continue
        if "SECRET" in k or "TOKEN" in k:
            masked[k] = (v[:8] + "..." + v[-4:]) if len(v) > 12 else "***"

    if args.json:
        out_json(masked)
        return

    hr("Credenciales cargadas")
    print(f"  Source : {masked.pop('_source','?')}")
    for k, v in masked.items():
        print(f"  {k:<28} = {v}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN / ARGPARSE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(
        prog="amazon-sp",
        description="CLI directo Amazon Selling Partner API · Adspubli",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  amazon-sp shop                 # info cuenta seller, verifica conexion
  amazon-sp config show          # ver credenciales cargadas (enmascaradas)

Credenciales se leen desde .env.amazon en (primera que exista):
  ~/.env.amazon
  ~/Documents/Workspace/Clients/pirojewelry.com/.env.amazon
        """,
    )
    p.add_argument("--json", "-j", action="store_true", help="Output en JSON puro")

    sub = p.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # ── shop ────────────────────────────────────────────────────────────────────
    sub.add_parser("shop", help="Info de cuenta seller y verificar conexion")

    # ── config ──────────────────────────────────────────────────────────────────
    cfg     = sub.add_parser("config", help="Configuracion local")
    cfg_sub = cfg.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")
    cfg_sub.add_parser("show", help="Ver credenciales cargadas (enmascaradas)")

    args = p.parse_args()
    cmd  = args.command
    sub_ = getattr(args, "subcommand", None)

    dispatch = {
        ("shop",   None):   cmd_shop,
        ("config", "show"): cmd_config_show,
    }

    fn = dispatch.get((cmd, sub_))
    if fn:
        fn(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()

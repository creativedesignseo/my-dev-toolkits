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
  amazon-sp shop                            # info de cuenta seller, verifica conexion
  amazon-sp config show                     # credenciales cargadas (enmascaradas)
  amazon-sp inventory                       # inventario FBA actual
  amazon-sp listings                        # todos los listings (Active+Inactive+Incomplete)
  amazon-sp orders --since 7daysAgo         # pedidos ultimos N dias
  amazon-sp pricing B0XXXXXXX               # tu precio + competencia + Buy Box
  amazon-sp catalog search "silver collar"  # busqueda en catalogo Amazon global
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ─── Config ────────────────────────────────────────────────────────────────────

ENV_LOCATIONS = [
    Path.home() / ".env.amazon",
    Path.home() / "Documents" / "Workspace" / "Clients" / "pirojewelry.com" / ".env.amazon",
]

DEFAULT_MARKETPLACE_ID = "ATVPDKIKX0DER"  # Amazon.com (US)

MARKETPLACE_ALIASES = {
    "US": "ATVPDKIKX0DER",
    "CA": "A2EUQ1WTGCTBG2",
    "MX": "A1AM78C64UM0Y8",
}


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


def resolve_marketplace(env: dict, alias: str | None = None):
    """
    Devuelve (Marketplaces enum, marketplace_id_string).

    Si se pasa un alias (US, CA, MX) lo usa; si no, lee AMAZON_MARKETPLACE_ID del .env.
    """
    from sp_api.base import Marketplaces

    if alias:
        mid = MARKETPLACE_ALIASES.get(alias.upper())
        if not mid:
            valid = ", ".join(MARKETPLACE_ALIASES)
            die(f"Marketplace '{alias}' desconocido. Validos: {valid}")
    else:
        mid = env.get("AMAZON_MARKETPLACE_ID", DEFAULT_MARKETPLACE_ID)

    for m in Marketplaces:
        if getattr(m, "marketplace_id", None) == mid:
            return m, mid

    eprint(f"  Aviso: marketplace ID '{mid}' no reconocido por la libreria, usando US.")
    return Marketplaces.US, mid


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


def short(text, n=60):
    if not text:
        return ""
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "…"


def amazon_marketplace_domain(marketplace_name: str) -> str:
    """Dominio amazon.X.com correspondiente a un Marketplaces enum name."""
    return {
        "US": "www.amazon.com",
        "CA": "www.amazon.ca",
        "MX": "www.amazon.com.mx",
        "ES": "www.amazon.es",
        "DE": "www.amazon.de",
        "FR": "www.amazon.fr",
        "IT": "www.amazon.it",
        "UK": "www.amazon.co.uk",
        "GB": "www.amazon.co.uk",
    }.get(marketplace_name, "www.amazon.com")


# ═══════════════════════════════════════════════════════════════════════════════
# SHOP — info de la cuenta seller y verificacion de conexion
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_shop(args):
    require_sp_api()

    env             = load_env()
    creds           = get_credentials(env)
    marketplace, _  = resolve_marketplace(env, getattr(args, "marketplace", None))

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
        m    = p.get("marketplace")   or {}
        part = p.get("participation") or {}

        name    = m.get("name", "?")
        country = m.get("countryCode", "?")
        mid     = m.get("id", "?")
        curr    = m.get("defaultCurrencyCode", "?")
        lang    = m.get("defaultLanguageCode", "?")
        domain  = m.get("domainName", "?")

        active  = part.get("isParticipating")
        sus     = part.get("hasSuspendedListings")

        marker_a = "✓ vendiendo" if active else "✗ sin venta"
        marker_s = "  ⚠ suspendidos" if sus else ""

        print(f"  {name}  ({country})  —  {marker_a}{marker_s}")
        print(f"    Marketplace ID : {mid}")
        print(f"    Moneda         : {curr}     Idioma: {lang}")
        print(f"    Dominio        : {domain}")
        print()

    print("  ✓ Conexion OK")


# ═══════════════════════════════════════════════════════════════════════════════
# INVENTORY — stock FBA actual
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_inventory(args):
    require_sp_api()

    env             = load_env()
    creds           = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    from sp_api.api import Inventories
    from sp_api.base.exceptions import SellingApiException

    try:
        client = Inventories(credentials=creds, marketplace=marketplace)
        result = client.get_inventory_summary_marketplace(
            details=True,
            granularityType="Marketplace",
            granularityId=mid,
            marketplaceIds=[mid],
        )
    except SellingApiException as e:
        die(f"SP-API devolvio un error:\n    {e}")
    except Exception as e:
        die(f"No se pudo conectar con SP-API:\n    {type(e).__name__}: {e}")

    payload    = result.payload or {}
    summaries  = payload.get("inventorySummaries", []) or []

    if args.json:
        out_json(summaries)
        return

    total_sellable = sum(
        (s.get("inventoryDetails") or {}).get("fulfillableQuantity", 0) or 0
        for s in summaries
    )
    with_stock = [s for s in summaries
                  if ((s.get("inventoryDetails") or {}).get("fulfillableQuantity") or 0) > 0]

    hr(f"Inventario FBA — {marketplace.name} — {len(summaries)} SKU(s) totales")
    print(f"  Vendible total : {total_sellable} unidades")
    print(f"  SKUs con stock : {len(with_stock)}")
    print()

    if not summaries:
        print("  (sin items en este marketplace)")
        return

    # Order: items with stock first
    summaries_sorted = sorted(
        summaries,
        key=lambda s: -((s.get("inventoryDetails") or {}).get("fulfillableQuantity") or 0),
    )

    print(f"  {'SKU':<22} {'ASIN':<12} {'Cond':<6} {'Sellable':>9}  Nombre")
    print(f"  {'─'*22} {'─'*12} {'─'*6} {'─'*9}  {'─'*40}")
    for s in summaries_sorted:
        sku   = short(s.get("sellerSku", "?"), 22)
        asin  = s.get("asin", "—") or "—"
        cond  = short(s.get("condition", "—"), 6)
        det   = s.get("inventoryDetails") or {}
        fulf  = det.get("fulfillableQuantity", 0) or 0
        name  = short(s.get("productName", ""), 40)
        print(f"  {sku:<22} {asin:<12} {cond:<6} {fulf:>9}  {name}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# LISTINGS — todos los listings via Reports API (TSV gzipped)
# ═══════════════════════════════════════════════════════════════════════════════

def _wait_for_report(reports_client, report_id, timeout_s=240, poll_s=10):
    """Polls get_report hasta DONE/CANCELLED/FATAL o timeout."""
    deadline = time.time() + timeout_s
    last     = None
    while time.time() < deadline:
        time.sleep(poll_s)
        resp = reports_client.get_report(report_id)
        last = resp.payload or {}
        status = last.get("processingStatus")
        eprint(f"  → status: {status}")
        if status in ("DONE", "CANCELLED", "FATAL"):
            return last
    die(f"Timeout esperando el report ({timeout_s}s). Ultimo status: {last}")


def cmd_listings(args):
    require_sp_api()

    env              = load_env()
    creds            = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    from sp_api.api import Reports
    from sp_api.base.reportTypes import ReportType
    from sp_api.base.exceptions import SellingApiException

    reports_client = Reports(credentials=creds, marketplace=marketplace)

    eprint("  → Solicitando report GET_MERCHANT_LISTINGS_ALL_DATA...")
    try:
        create_resp = reports_client.create_report(
            reportType=ReportType.GET_MERCHANT_LISTINGS_ALL_DATA.value,
            marketplaceIds=[mid],
        )
    except SellingApiException as e:
        die(f"create_report fallo:\n    {e}")

    report_id = (create_resp.payload or {}).get("reportId")
    if not report_id:
        die(f"create_report sin reportId: {create_resp.payload}")
    eprint(f"  → reportId: {report_id}")

    final = _wait_for_report(reports_client, report_id, timeout_s=240, poll_s=10)
    status = final.get("processingStatus")
    if status != "DONE":
        die(f"Report no completo (status={status}). Detalle: {final}")

    doc_id = final.get("reportDocumentId")
    if not doc_id:
        die("Report DONE pero sin reportDocumentId (puede que no haya datos).")
    eprint(f"  → documentId: {doc_id}")

    try:
        doc_resp = reports_client.get_report_document(doc_id)
    except SellingApiException as e:
        die(f"get_report_document fallo:\n    {e}")

    url         = (doc_resp.payload or {}).get("url")
    compression = (doc_resp.payload or {}).get("compressionAlgorithm")
    if not url:
        die("Document sin URL.")

    eprint("  → Descargando documento...")
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read()
    if compression == "GZIP":
        data = gzip.decompress(data)

    text   = data.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    rows   = list(reader)

    if args.json:
        out_json(rows)
        return

    # Group by status and fulfillment-channel
    by_status  = {}
    by_channel = {}
    for row in rows:
        st = (row.get("status") or "Unknown").strip()
        by_status.setdefault(st, []).append(row)
        ch = (row.get("fulfillment-channel") or "DEFAULT").strip()
        by_channel.setdefault(ch, []).append(row)

    hr(f"Listings — {marketplace.name} — {len(rows)} total")
    for st, items in sorted(by_status.items(), key=lambda kv: -len(kv[1])):
        print(f"  {st:14} : {len(items)}")
    print()
    print("  Por canal:")
    for ch, items in sorted(by_channel.items(), key=lambda kv: -len(kv[1])):
        print(f"    {ch:14} : {len(items)}")
    print()

    show_n = min(30, len(rows))
    print(f"  Detalle (primeros {show_n}):")
    print(f"  {'Status':<11} {'SKU':<22} {'ASIN':<12} {'Price':>7}  {'Qty':>4}  Nombre")
    print(f"  {'─'*11} {'─'*22} {'─'*12} {'─'*7}  {'─'*4}  {'─'*40}")
    for row in rows[:show_n]:
        sku   = short(row.get("seller-sku", "?"), 22)
        asin  = row.get("asin1", "—") or "—"
        price = row.get("price") or "—"
        qty   = row.get("quantity") or "—"
        st    = short(row.get("status", "?"), 11)
        name  = short(row.get("item-name") or "", 40)
        print(f"  {st:<11} {sku:<22} {asin:<12} {price:>7}  {qty:>4}  {name}")

    if len(rows) > show_n:
        print(f"\n  ... y {len(rows) - show_n} mas. Usa --json para todos.")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# ORDERS — pedidos recientes (sin PII por defecto)
# ═══════════════════════════════════════════════════════════════════════════════

_SINCE_MAP = {
    "7daysAgo":  7,
    "14daysAgo": 14,
    "30daysAgo": 30,
}


def cmd_orders(args):
    require_sp_api()

    env              = load_env()
    creds            = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    days = _SINCE_MAP.get(args.since, 7)
    created_after = (datetime.now(timezone.utc) - timedelta(days=days))\
        .strftime("%Y-%m-%dT%H:%M:%SZ")

    from sp_api.api import Orders
    from sp_api.base.exceptions import SellingApiException

    orders_client = Orders(credentials=creds, marketplace=marketplace)
    try:
        result = orders_client.get_orders(
            CreatedAfter=created_after,
            MarketplaceIds=[mid],
        )
    except SellingApiException as e:
        die(f"get_orders fallo:\n    {e}")

    payload    = result.payload or {}
    order_list = payload.get("Orders", []) or []

    if args.json:
        out_json(order_list)
        return

    hr(f"Pedidos — ultimos {days} dias — {marketplace.name} — {len(order_list)} encontrados")
    if not order_list:
        print(f"  Sin pedidos desde {created_after}.")
        return

    print(f"  {'OrderID':<22} {'Fecha':<10} {'Status':<18} {'Total':>10}  {'Items':>5}  Canal")
    print(f"  {'─'*22} {'─'*10} {'─'*18} {'─'*10}  {'─'*5}  {'─'*8}")
    for o in order_list:
        oid     = o.get("AmazonOrderId", "?")
        date    = (o.get("PurchaseDate", "") or "")[:10]
        status  = short(o.get("OrderStatus", "?"), 18)
        total   = o.get("OrderTotal") or {}
        amt     = total.get("Amount", "—")
        curr    = total.get("CurrencyCode", "")
        amt_str = f"{amt} {curr}".strip() if amt != "—" else "—"
        n_sh    = int(o.get("NumberOfItemsShipped") or 0)
        n_unsh  = int(o.get("NumberOfItemsUnshipped") or 0)
        nitems  = n_sh + n_unsh
        channel = short(o.get("FulfillmentChannel", "?"), 8)
        print(f"  {oid:<22} {date:<10} {status:<18} {amt_str:>10}  {nitems:>5}  {channel}")
    print()

    if args.details:
        print("  --- Buyer info (via Tokens / RDT) ---")
        _fetch_buyer_details(creds, marketplace, order_list)


def _fetch_buyer_details(creds, marketplace, order_list):
    """Para cada order, pide un RDT y consulta buyerInfo. NO scrapea direccion completa,
    solo nombre/email/zip — informacion minima para tracking interno."""
    from sp_api.api import Tokens, Orders
    from sp_api.base.exceptions import SellingApiException

    tokens_client = Tokens(credentials=creds, marketplace=marketplace)

    for o in order_list:
        oid = o.get("AmazonOrderId")
        if not oid:
            continue
        try:
            tk_resp = tokens_client.create_restricted_data_token(restrictedResources=[{
                "method":       "GET",
                "path":         f"/orders/v0/orders/{oid}/buyerInfo",
                "dataElements": ["buyerInfo"],
            }])
            rdt = (tk_resp.payload or {}).get("restrictedDataToken")
            if not rdt:
                eprint(f"    {oid}: no RDT")
                continue
            rdt_client = Orders(credentials=creds, marketplace=marketplace,
                                restricted_data_token=rdt)
            bi = (rdt_client.get_order_buyer_info(oid).payload) or {}
            email = bi.get("BuyerEmail", "—")
            name  = bi.get("BuyerName", "—")
            print(f"    {oid}: {name}  <{email}>")
        except SellingApiException as e:
            eprint(f"    {oid}: error {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PRICING — tu precio + competencia + Buy Box para un ASIN
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_pricing(args):
    require_sp_api()

    env              = load_env()
    creds            = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    asin = args.asin.strip().upper()
    if not (asin.startswith("B0") and len(asin) == 10):
        eprint(f"  Aviso: '{asin}' no parece un ASIN estandar (10 chars empezando por B0).")

    from sp_api.api import Products
    from sp_api.base.exceptions import SellingApiException

    products = Products(credentials=creds, marketplace=marketplace)

    try:
        result = products.get_item_offers(asin, item_condition="New")
    except SellingApiException as e:
        die(f"get_item_offers fallo:\n    {e}")

    payload = result.payload or {}
    summary = payload.get("Summary", {}) or {}
    offers  = payload.get("Offers", []) or []

    if args.json:
        out_json(payload)
        return

    domain = amazon_marketplace_domain(marketplace.name)
    hr(f"Pricing — ASIN {asin} — {marketplace.name}")
    print(f"  Producto         : https://{domain}/dp/{asin}")
    print(f"  Ofertas totales  : {summary.get('TotalOfferCount', '?')}")

    bbox = summary.get("BuyBoxPrices") or []
    if bbox:
        b = bbox[0]
        lp = b.get("ListingPrice", {})
        print(f"  Buy Box price    : {lp.get('Amount','?')} {lp.get('CurrencyCode','')}  "
              f"(condition={b.get('condition','?')})")
    else:
        print("  Buy Box price    : —  (sin Buy Box)")

    lowest = summary.get("LowestPrices") or []
    if lowest:
        lp = lowest[0].get("ListingPrice", {})
        ship = lowest[0].get("Shipping", {})
        print(f"  Lowest price     : {lp.get('Amount','?')} {lp.get('CurrencyCode','')} "
              f"+ {ship.get('Amount','0')} ship")
    else:
        print("  Lowest price     : —")

    print()
    n = min(5, len(offers))
    print(f"  Top {n} ofertas:")
    if not offers:
        print("  (sin ofertas visibles)")
        return
    print(f"  {'#':<2} {'Price':>9} {'+Ship':>7}  {'Cond':<6} {'FBA':<4} {'BBox':<5} {'Feedback':>9}")
    print(f"  {'─'*2} {'─'*9} {'─'*7}  {'─'*6} {'─'*4} {'─'*5} {'─'*9}")
    for i, o in enumerate(offers[:5], 1):
        lp     = o.get("ListingPrice", {})
        sh     = o.get("Shipping", {})
        price  = f"{lp.get('Amount','?')} {lp.get('CurrencyCode','')}"
        ship   = sh.get("Amount", "0")
        cond   = short(o.get("SubCondition") or o.get("Condition") or "New", 6)
        is_fba = "yes" if o.get("IsFulfilledByAmazon") else "no"
        is_bb  = "✓" if o.get("IsBuyBoxWinner") else ""
        fb     = (o.get("SellerFeedbackRating") or {}).get("FeedbackCount", "?")
        print(f"  {i:<2} {price:>9} {ship:>7}  {cond:<6} {is_fba:<4} {is_bb:<5} {fb:>9}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# CATALOG SEARCH — busqueda en el catalogo Amazon global
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_catalog_search(args):
    require_sp_api()

    env              = load_env()
    creds            = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    from sp_api.api import CatalogItems
    from sp_api.base.exceptions import SellingApiException

    catalog = CatalogItems(credentials=creds, marketplace=marketplace, version="2022-04-01")

    try:
        result = catalog.search_catalog_items(
            keywords=[args.query],
            marketplaceIds=[mid],
            includedData=["identifiers", "attributes", "summaries"],
            pageSize=10,
        )
    except SellingApiException as e:
        die(f"search_catalog_items fallo:\n    {e}")

    payload = result.payload or {}
    items   = payload.get("items", []) or []

    if args.json:
        out_json(items)
        return

    domain = amazon_marketplace_domain(marketplace.name)
    hr(f"Catalogo Amazon — '{args.query}' — {marketplace.name} — {len(items)} resultados")

    if not items:
        print("  (sin resultados — prueba keywords mas amplios)")
        return

    for i, item in enumerate(items[:10], 1):
        asin       = item.get("asin", "?")
        summaries  = item.get("summaries") or []
        s          = summaries[0] if summaries else {}
        brand      = s.get("brand", "—") or "—"
        title      = short(s.get("itemName") or "(sin titulo)", 80)
        print(f"  {i:>2}. [{asin}]  brand: {brand}")
        print(f"      {title}")
        print(f"      https://{domain}/dp/{asin}")
        print()


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

def _add_marketplace_flag(parser):
    parser.add_argument(
        "--marketplace", "-m",
        choices=list(MARKETPLACE_ALIASES.keys()),
        help="Marketplace a usar (default: el de AMAZON_MARKETPLACE_ID en .env.amazon)",
    )


def main():
    p = argparse.ArgumentParser(
        prog="amazon-sp",
        description="CLI directo Amazon Selling Partner API · Adspubli",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  amazon-sp shop                              # info cuenta seller
  amazon-sp inventory                         # stock FBA en marketplace base
  amazon-sp inventory --marketplace CA        # stock FBA en Canada
  amazon-sp listings                          # TODOS los listings (Active+Inactive+Incomplete)
  amazon-sp orders --since 7daysAgo           # pedidos ultimos 7 dias
  amazon-sp orders --since 30daysAgo --details # con buyer info via RDT (lento)
  amazon-sp pricing B0XXXXXXX                 # tu precio + competencia + Buy Box
  amazon-sp catalog search "silver necklace"  # top 10 catalogo Amazon
  amazon-sp config show                       # credenciales (enmascaradas)

Credenciales se leen desde .env.amazon en (primera que exista):
  ~/.env.amazon
  ~/Documents/Workspace/Clients/pirojewelry.com/.env.amazon
        """,
    )
    p.add_argument("--json", "-j", action="store_true", help="Output en JSON puro")

    sub = p.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # ── shop ───────────────────────────────────────────────────────────────────
    sp_shop = sub.add_parser("shop", help="Info de cuenta seller y verificar conexion")
    _add_marketplace_flag(sp_shop)

    # ── inventory ──────────────────────────────────────────────────────────────
    sp_inv = sub.add_parser("inventory", help="Stock FBA actual del marketplace")
    _add_marketplace_flag(sp_inv)

    # ── listings ───────────────────────────────────────────────────────────────
    sp_li = sub.add_parser("listings", help="Todos los listings (via Reports API, async)")
    _add_marketplace_flag(sp_li)

    # ── orders ─────────────────────────────────────────────────────────────────
    sp_or = sub.add_parser("orders", help="Pedidos recientes")
    _add_marketplace_flag(sp_or)
    sp_or.add_argument(
        "--since", default="7daysAgo",
        choices=list(_SINCE_MAP.keys()),
        help="Rango de tiempo (default 7daysAgo)",
    )
    sp_or.add_argument(
        "--details", action="store_true",
        help="Trae buyer info via RDT (PII — solo cuando es necesario, lento)",
    )

    # ── pricing ────────────────────────────────────────────────────────────────
    sp_pr = sub.add_parser("pricing", help="Pricing y Buy Box info para un ASIN")
    _add_marketplace_flag(sp_pr)
    sp_pr.add_argument("asin", metavar="ASIN", help="ASIN Amazon (ej: B0XXXXXXX)")

    # ── catalog ────────────────────────────────────────────────────────────────
    sp_cat     = sub.add_parser("catalog", help="Catalogo Amazon (busqueda global)")
    sp_cat_sub = sp_cat.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")
    sp_cat_s   = sp_cat_sub.add_parser("search", help="Buscar productos por keyword")
    _add_marketplace_flag(sp_cat_s)
    sp_cat_s.add_argument("query", metavar="QUERY", help="Keywords a buscar")

    # ── config ─────────────────────────────────────────────────────────────────
    sp_cfg     = sub.add_parser("config", help="Configuracion local")
    sp_cfg_sub = sp_cfg.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")
    sp_cfg_sub.add_parser("show", help="Ver credenciales cargadas (enmascaradas)")

    args = p.parse_args()
    cmd  = args.command
    sub_ = getattr(args, "subcommand", None)

    dispatch = {
        ("shop",      None):    cmd_shop,
        ("inventory", None):    cmd_inventory,
        ("listings",  None):    cmd_listings,
        ("orders",    None):    cmd_orders,
        ("pricing",   None):    cmd_pricing,
        ("catalog",   "search"): cmd_catalog_search,
        ("config",    "show"):  cmd_config_show,
    }

    fn = dispatch.get((cmd, sub_))
    if fn:
        fn(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()

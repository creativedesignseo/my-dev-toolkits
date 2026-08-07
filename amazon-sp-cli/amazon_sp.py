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
import hashlib
import io
import json
import mimetypes
import shutil
import subprocess
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

# Tipos comunes para reports list / feeds list por defecto.
# La API requiere reportTypes o feedTypes en cada llamada (no acepta consulta libre).
COMMON_REPORT_TYPES = [
    "GET_MERCHANT_LISTINGS_ALL_DATA",
    "GET_FLAT_FILE_OPEN_LISTINGS_DATA",
    "GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA",
    "GET_AMAZON_FULFILLED_SHIPMENTS_DATA_GENERAL",
    "GET_FLAT_FILE_ALL_ORDERS_DATA_BY_LAST_UPDATE_GENERAL",
    "GET_V1_SELLER_PERFORMANCE_REPORT",
]

COMMON_FEED_TYPES = [
    # Solo el feed moderno por defecto. Los legacy POST_PRODUCT_DATA, etc. estan
    # gated por rol y hacen fallar el batch entero con Unauthorized si no estan
    # autorizados. Para consultar uno especifico: amazon-sp feeds list --type X
    "JSON_LISTINGS_FEED",
]


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


def _guess_content_type(path: Path) -> str:
    """Adivina content-type HTTP por extension del archivo a subir."""
    return {
        ".tsv":  "text/tab-separated-values; charset=UTF-8",
        ".csv":  "text/csv; charset=UTF-8",
        ".xml":  "text/xml; charset=UTF-8",
        ".json": "application/json; charset=UTF-8",
        ".txt":  "text/plain; charset=UTF-8",
    }.get(path.suffix.lower(), "text/plain; charset=UTF-8")


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
# CATALOG GET — detalle completo de un ASIN en el catalogo Amazon
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_catalog_get(args):
    require_sp_api()

    env              = load_env()
    creds            = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    asin = args.asin.strip().upper()

    from sp_api.api import CatalogItems
    from sp_api.base.exceptions import SellingApiException

    catalog = CatalogItems(credentials=creds, marketplace=marketplace, version="2022-04-01")

    try:
        result = catalog.get_catalog_item(
            asin,
            marketplaceIds=[mid],
            includedData=[
                "identifiers", "attributes", "summaries",
                "salesRanks", "productTypes", "images",
            ],
        )
    except SellingApiException as e:
        die(f"get_catalog_item fallo:\n    {e}")

    payload = result.payload or {}

    if args.json:
        out_json(payload)
        return

    summaries = payload.get("summaries") or []
    s         = summaries[0] if summaries else {}
    domain    = amazon_marketplace_domain(marketplace.name)

    hr(f"Catalog item — {asin} — {marketplace.name}")
    print(f"  Brand          : {s.get('brand','—')}")
    print(f"  Title          : {short(s.get('itemName','—'), 90)}")
    print(f"  Manufacturer   : {s.get('manufacturer','—')}")
    print(f"  Color          : {s.get('color','—')}")
    print(f"  Size           : {s.get('size','—')}")
    print(f"  Model number   : {s.get('modelNumber','—')}")
    print(f"  Classification : {s.get('itemClassification','—')}")

    ptypes = payload.get("productTypes") or []
    if ptypes:
        pt_str = ", ".join(p.get("productType", "?") for p in ptypes[:3])
        print(f"  Product type   : {pt_str}")

    ranks = payload.get("salesRanks") or []
    if ranks:
        print()
        print("  Sales Ranks:")
        for r in ranks[:2]:
            for cr in (r.get("classificationRanks") or [])[:3]:
                print(f"    #{cr.get('rank','?'):<8} in {short(cr.get('title','?'), 70)}")
            for dr in (r.get("displayGroupRanks") or [])[:3]:
                print(f"    #{dr.get('rank','?'):<8} in {short(dr.get('title','?'), 70)}")

    images = payload.get("images") or []
    if images:
        first = images[0]
        imgs  = first.get("images") or []
        if imgs:
            print()
            print(f"  Imagen principal : {imgs[0].get('link','—')}")

    print()
    print(f"  Producto       : https://{domain}/dp/{asin}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# FEES — estimacion referral + FBA fees para un ASIN dado un precio
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_fees(args):
    require_sp_api()

    env              = load_env()
    creds            = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    asin     = args.asin.strip().upper()
    is_fba   = not args.no_fba
    currency = args.currency or "USD"

    from sp_api.api import ProductFees
    from sp_api.base.exceptions import SellingApiException

    fees_client = ProductFees(credentials=creds, marketplace=marketplace)

    try:
        result = fees_client.get_product_fees_estimate_for_asin(
            asin,
            price=args.price,
            shipping_price=args.shipping or 0,
            currency=currency,
            is_fba=is_fba,
            marketplace_id=mid,
        )
    except SellingApiException as e:
        die(f"get_product_fees_estimate_for_asin fallo:\n    {e}")

    payload    = result.payload or {}
    fee_result = payload.get("FeesEstimateResult") or {}
    estimate   = fee_result.get("FeesEstimate") or {}

    if args.json:
        out_json(payload)
        return

    if not estimate:
        err = fee_result.get("Error")
        if err:
            die(f"Amazon devolvio un error de fees:\n    "
                f"{err.get('Code','?')} — {err.get('Message','?')}")
        die("Sin estimate y sin error explicito. Revisa con --json.")

    total = estimate.get("TotalFeesEstimate") or {}
    items = estimate.get("FeeDetailList")    or []

    hr(f"Fees estimate — ASIN {asin} — {marketplace.name}")
    print(f"  Precio asumido : {args.price} {currency}")
    print(f"  Shipping       : {args.shipping or 0} {currency}")
    print(f"  Fulfillment    : {'FBA' if is_fba else 'MFN (Seller fulfilled)'}")
    print()
    print(f"  Total fees     : {total.get('Amount','?')} {total.get('CurrencyCode','')}")
    print()
    print("  Breakdown (FinalFee = lo realmente cobrado; entre parentesis el FeeAmount")
    print("  advertised si difiere por promos/discounts):")
    for fee in items:
        ft       = fee.get("FeeType","?")
        final    = fee.get("FinalFee") or {}
        advert   = fee.get("FeeAmount") or {}
        fin_amt  = final.get("Amount", "?")
        fin_curr = final.get("CurrencyCode", "")
        adv_amt  = advert.get("Amount", "?")

        note = ""
        if fin_amt != adv_amt and adv_amt not in ("?", None):
            note = f"  (advertised: {adv_amt})"

        print(f"    {ft:<32}  {fin_amt:>8} {fin_curr}{note}")

        # Subitems (eg. FBAFees → FBAWeightHandling, FBAPickAndPack, etc.)
        for sub in (fee.get("IncludedFeeDetailList") or []):
            st  = sub.get("FeeType","?")
            sa  = (sub.get("FinalFee") or sub.get("FeeAmount") or {}).get("Amount","?")
            sc  = (sub.get("FinalFee") or sub.get("FeeAmount") or {}).get("CurrencyCode","")
            print(f"      └ {st:<28}  {sa:>8} {sc}")

    try:
        net = float(args.price) - float(total.get("Amount", 0) or 0)
        margin_pct = (net / float(args.price)) * 100 if float(args.price) > 0 else 0
        print()
        print(f"  Neto despues de fees : {net:.2f} {currency}  "
              f"({margin_pct:.1f}% del revenue, sin contar COGS)")
    except (ValueError, TypeError):
        pass
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTS LIST — reports recientes generados (read-only)
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_reports_list(args):
    require_sp_api()

    env              = load_env()
    creds            = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    from sp_api.api import Reports
    from sp_api.base.exceptions import SellingApiException

    reports_client = Reports(credentials=creds, marketplace=marketplace)
    types = [args.type] if args.type else COMMON_REPORT_TYPES

    try:
        result = reports_client.get_reports(
            reportTypes=types,
            marketplaceIds=[mid],
            pageSize=min(args.limit or 20, 100),
        )
    except SellingApiException as e:
        die(f"get_reports fallo:\n    {e}")

    payload = result.payload or {}
    reports = payload.get("reports") or []

    if args.json:
        out_json(reports)
        return

    filter_label = args.type if args.type else f"{len(types)} tipos comunes"
    hr(f"Reports — {marketplace.name} — filtro: {filter_label} — {len(reports)} encontrados")

    if not reports:
        print("  (sin reports recientes para los tipos consultados)")
        if not args.type:
            print(f"  Tipos consultados: {', '.join(types)}")
        return

    print(f"  {'reportId':<14} {'Tipo':<48} {'Status':<12} Creado")
    print(f"  {'─'*14} {'─'*48} {'─'*12} {'─'*19}")
    for r in reports:
        rid = r.get("reportId", "?")
        rt  = short(r.get("reportType", "?"), 48)
        st  = short(r.get("processingStatus", "?"), 12)
        cr  = (r.get("createdTime", "") or "")[:19]
        print(f"  {rid:<14} {rt:<48} {st:<12} {cr}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# FEEDS LIST — feeds recientes submitidos (read-only)
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_feeds_list(args):
    require_sp_api()

    env              = load_env()
    creds            = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    from sp_api.api import Feeds
    from sp_api.base.exceptions import SellingApiException

    feeds_client = Feeds(credentials=creds, marketplace=marketplace)
    types = [args.type] if args.type else COMMON_FEED_TYPES

    try:
        result = feeds_client.get_feeds(
            feedTypes=types,
            marketplaceIds=[mid],
            pageSize=min(args.limit or 20, 100),
        )
    except SellingApiException as e:
        die(f"get_feeds fallo:\n    {e}")

    payload = result.payload or {}
    feeds   = payload.get("feeds") or []

    if args.json:
        out_json(feeds)
        return

    filter_label = args.type if args.type else f"{len(types)} tipos comunes"
    hr(f"Feeds — {marketplace.name} — filtro: {filter_label} — {len(feeds)} encontrados")

    if not feeds:
        print("  (sin feeds recientes para los tipos consultados)")
        if not args.type:
            print(f"  Tipos consultados: {', '.join(types)}")
        return

    print(f"  {'feedId':<14} {'Tipo':<36} {'Status':<12} Creado")
    print(f"  {'─'*14} {'─'*36} {'─'*12} {'─'*19}")
    for f in feeds:
        fid = f.get("feedId", "?")
        ft  = short(f.get("feedType", "?"), 36)
        st  = short(f.get("processingStatus", "?"), 12)
        cr  = (f.get("createdTime", "") or "")[:19]
        print(f"  {fid:<14} {ft:<36} {st:<12} {cr}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# FEEDS SUBMIT — DESTRUCTIVO: carga masiva. Requiere --confirm.
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_feeds_submit(args):
    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        die(f"Archivo no encontrado: {file_path}")
    if not file_path.is_file():
        die(f"No es un archivo regular: {file_path}")

    size = file_path.stat().st_size

    if not args.confirm:
        hr("feeds submit — DRY RUN  (sin --confirm)")
        print(f"  Archivo       : {file_path}")
        print(f"  Tamano        : {size:,} bytes")
        print(f"  Feed type     : {args.type}")
        print(f"  Content-type  : {args.content_type or _guess_content_type(file_path)}")
        print(f"  Marketplace   : {args.marketplace or '(default del .env)'}")
        print()
        print("  Para realmente submittear este feed:")
        mp = f" --marketplace {args.marketplace}" if args.marketplace else ""
        print(f"    amazon-sp feeds submit {file_path}{mp} \\")
        print(f"      --type {args.type} --confirm")
        print()
        print("  ATENCION: este comando MODIFICA tu cuenta Amazon (precios, stock,")
        print("  productos o imagenes segun el feed type). Verifica el archivo antes.")
        return

    # Real submit
    require_sp_api()
    env              = load_env()
    creds            = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    from sp_api.api import Feeds
    from sp_api.base.exceptions import SellingApiException

    feeds_client = Feeds(credentials=creds, marketplace=marketplace)
    content_type = args.content_type or _guess_content_type(file_path)

    eprint(f"  → Subiendo {file_path.name} ({size:,} bytes) como {args.type}")
    eprint(f"  → Content-type: {content_type}")

    try:
        with open(file_path, "rb") as f:
            doc_resp, feed_resp = feeds_client.submit_feed(
                feed_type=args.type,
                file=f,
                content_type=content_type,
                marketplaceIds=[mid],
            )
    except SellingApiException as e:
        die(f"submit_feed fallo:\n    {e}")

    feed_id = (feed_resp.payload or {}).get("feedId")
    doc_id  = (doc_resp.payload  or {}).get("feedDocumentId")

    hr("✓ Feed submitted")
    print(f"  feedId           : {feed_id}")
    print(f"  feedDocumentId   : {doc_id}")
    print(f"  Tipo             : {args.type}")
    print(f"  Marketplace      : {marketplace.name}")
    print()
    print("  Verificar status (puede tardar minutos en procesarse):")
    print(f"    amazon-sp feeds list --type {args.type}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# A+ CONTENT (Sprint 4) — modulos visuales para listings con Brand Registry
# ═══════════════════════════════════════════════════════════════════════════════
#
# Flujo tipico:
#   1. amazon-sp aplus upload-image foto.jpg   → uploadDestinationId
#   2. amazon-sp aplus template > my.json
#   3. (editar my.json con tus textos + uploadDestinationIds)
#   4. amazon-sp aplus create my.json           → contentReferenceKey (DRAFT)
#   5. amazon-sp aplus apply <KEY> --asin <ASIN>
#   6. amazon-sp aplus submit <KEY> --confirm   → Amazon revisa (24-72h)


APLUS_INCLUDED_DATA_FULL = ["METADATA", "CONTENTS"]


def _aplus_client(creds, marketplace):
    from sp_api.api import AplusContent
    return AplusContent(credentials=creds, marketplace=marketplace)


def cmd_aplus_list(args):
    require_sp_api()
    env             = load_env()
    creds           = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    from sp_api.base.exceptions import SellingApiException

    client = _aplus_client(creds, marketplace)
    try:
        result = client.search_content_documents(marketplaceId=mid)
    except SellingApiException as e:
        die(f"search_content_documents fallo:\n    {e}")

    payload = result.payload or {}
    docs    = payload.get("contentDocumentInfoList") or []

    if args.json:
        out_json(docs)
        return

    hr(f"A+ Content documents — {marketplace.name} — {len(docs)} encontrados")
    if not docs:
        print("  (cuenta sin A+ Content todavía. Crea uno con `amazon-sp aplus create`.)")
        return

    print(f"  {'contentReferenceKey':<32} {'Status':<14} {'Type':<10} Nombre")
    print(f"  {'─'*32} {'─'*14} {'─'*10} {'─'*40}")
    for d in docs:
        key  = short(d.get("contentReferenceKey", "?"), 32)
        st   = short(d.get("status", "?"), 14)
        ct   = short(d.get("contentType", "?"), 10)
        name = short(d.get("name", "?"), 40)
        print(f"  {key:<32} {st:<14} {ct:<10} {name}")
    print()


def cmd_aplus_get(args):
    require_sp_api()
    env             = load_env()
    creds           = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    from sp_api.base.exceptions import SellingApiException

    client = _aplus_client(creds, marketplace)
    try:
        result = client.get_content_document(
            args.doc_id,
            marketplaceId=mid,
            includedDataSet=APLUS_INCLUDED_DATA_FULL,
        )
    except SellingApiException as e:
        die(f"get_content_document fallo:\n    {e}")

    payload = result.payload or {}

    if args.json:
        out_json(payload)
        return

    metadata = payload.get("contentMetadata") or {}
    document = payload.get("contentDocument") or {}
    modules  = document.get("contentModuleList") or []

    hr(f"A+ Content {args.doc_id}")
    print(f"  Nombre        : {document.get('name','?')}")
    print(f"  Tipo          : {document.get('contentType','?')}")
    print(f"  SubTipo       : {document.get('contentSubType','—')}")
    print(f"  Locale        : {document.get('locale','?')}")
    print(f"  Status        : {metadata.get('status','?')}")
    print(f"  Last updated  : {(metadata.get('updateTime','') or '')[:19]}")
    print(f"  Modules       : {len(modules)}")
    for i, m in enumerate(modules, 1):
        mt = m.get("contentModuleType", "?")
        print(f"    {i}. {mt}")
    print()


def cmd_aplus_asins(args):
    require_sp_api()
    env             = load_env()
    creds           = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    from sp_api.base.exceptions import SellingApiException

    client = _aplus_client(creds, marketplace)
    try:
        result = client.list_content_document_asin_relations(
            args.doc_id,
            marketplaceId=mid,
            includedDataSet=["METADATA"],
        )
    except SellingApiException as e:
        die(f"list_content_document_asin_relations fallo:\n    {e}")

    payload  = result.payload or {}
    asin_set = payload.get("asinMetadataSet") or []

    if args.json:
        out_json(asin_set)
        return

    hr(f"ASINs ligados al document {args.doc_id} — {len(asin_set)}")
    if not asin_set:
        print("  (sin ASINs ligados — usa `amazon-sp aplus apply` para linkear)")
        return
    domain = amazon_marketplace_domain(marketplace.name)
    for a in asin_set:
        asin = a.get("asin", "?")
        bp   = a.get("badgeSet") or []
        st   = a.get("contentReferenceKey", "—")
        print(f"  {asin}   badges={','.join(bp) if bp else '—'}")
        print(f"    https://{domain}/dp/{asin}")
    print()


def _put_image_to_url(url: str, file_path: Path, content_type: str, content_md5: str) -> None:
    """PUT al presigned URL devuelto por createUploadDestination."""
    with open(file_path, "rb") as f:
        data = f.read()
    req = urllib.request.Request(
        url,
        data=data,
        method="PUT",
        headers={
            "Content-Type": content_type,
            "Content-MD5":  content_md5,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            if not (200 <= resp.status < 300):
                die(f"PUT a S3 fallo con status {resp.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:400]
        die(f"PUT a S3 fallo: HTTP {e.code}\n{body}")


def cmd_aplus_upload_image(args):
    require_sp_api()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        die(f"Archivo no encontrado: {file_path}")
    if file_path.stat().st_size == 0:
        die(f"Archivo vacio: {file_path}")

    # Adivinar content-type por extension
    ct, _ = mimetypes.guess_type(str(file_path))
    if not ct:
        ct = args.content_type or "image/jpeg"
    if args.content_type:
        ct = args.content_type

    # MD5 base64-encoded como exige Amazon
    import base64
    with open(file_path, "rb") as f:
        data = f.read()
    md5_b64 = base64.b64encode(hashlib.md5(data).digest()).decode()

    env             = load_env()
    creds           = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    from sp_api.api import Upload
    from sp_api.base.exceptions import SellingApiException

    upload_client = Upload(credentials=creds, marketplace=marketplace)

    # Paso 1: pedir destination + presigned URL.
    # El metodo upload_document de saleweaver hace solo este paso.
    eprint(f"  → Solicitando upload destination ({file_path.name}, {file_path.stat().st_size:,} bytes, {ct})")
    try:
        with open(file_path, "rb") as f:
            resp = upload_client.upload_document(
                resource="aplus",
                file=f,
                content_type=ct,
                contentMD5=md5_b64,
            )
    except SellingApiException as e:
        die(f"createUploadDestination fallo:\n    {e}")

    p = (resp.payload or {})
    upload_url = p.get("url")
    dest_id    = p.get("uploadDestinationId")
    if not upload_url or not dest_id:
        die(f"Respuesta sin url/uploadDestinationId:\n{p}")

    # Paso 2: PUT del archivo al presigned URL
    eprint("  → Subiendo archivo al destino S3...")
    _put_image_to_url(upload_url, file_path, ct, md5_b64)

    if args.json:
        out_json({"uploadDestinationId": dest_id, "url": upload_url})
        return

    hr("✓ Imagen subida")
    print(f"  uploadDestinationId : {dest_id}")
    print(f"  (usa este ID en el template A+ Content como 'uploadDestinationId')")
    print()


APLUS_TEMPLATE = {
    "contentDocument": {
        "name": "REEMPLAZA_NOMBRE_INTERNO",
        "contentType": "EBC",
        "locale": "en_US",
        "contentModuleList": [
            {
                "contentModuleType": "STANDARD_HEADER_IMAGE_TEXT",
                "standardHeaderImageText": {
                    "headline": {"value": "TÍTULO PRINCIPAL (max 150 chars)", "decoratorSet": []},
                    "block": {
                        "headline": {"value": "Subtitulo (50 chars)", "decoratorSet": []},
                        "body": {
                            "textList": [
                                {
                                    "text": {
                                        "value": "Parrafo de cuerpo. Describe el producto.",
                                        "decoratorSet": []
                                    }
                                }
                            ]
                        },
                        "image": {
                            "uploadDestinationId": "REEMPLAZA_CON_UPLOAD_DESTINATION_ID",
                            "imageCropSpecification": {
                                "size": {
                                    "width":  {"value": 970, "units": "pixels"},
                                    "height": {"value": 300, "units": "pixels"}
                                },
                                "offset": {
                                    "x": {"value": 0, "units": "pixels"},
                                    "y": {"value": 0, "units": "pixels"}
                                }
                            },
                            "altText": "Descripcion alt-text de la imagen header"
                        }
                    }
                }
            },
            {
                "contentModuleType": "STANDARD_PRODUCT_DESCRIPTION",
                "standardProductDescription": {
                    "body": {
                        "textList": [
                            {
                                "text": {
                                    "value": "Descripcion completa del producto. Reemplaza el campo description del listing tradicional.",
                                    "decoratorSet": []
                                }
                            }
                        ]
                    }
                }
            },
            {
                "contentModuleType": "STANDARD_TEXT",
                "standardText": {
                    "headline": {"value": "ALGO MÁS QUE QUIERAS DESTACAR", "decoratorSet": []},
                    "body": {
                        "textList": [
                            {
                                "text": {
                                    "value": "Otro bloque de texto adicional.",
                                    "decoratorSet": []
                                }
                            }
                        ]
                    }
                }
            }
        ]
    }
}


def cmd_aplus_template(args):
    """Imprime un template JSON valido para usar como base con `aplus create`."""
    print(json.dumps(APLUS_TEMPLATE, indent=2, ensure_ascii=False))


def cmd_aplus_create(args):
    require_sp_api()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        die(f"Archivo no encontrado: {file_path}")

    try:
        body = json.loads(file_path.read_text())
    except json.JSONDecodeError as e:
        die(f"JSON invalido en {file_path}: {e}")

    if "contentDocument" not in body:
        die("El JSON debe tener una clave 'contentDocument' al nivel raiz. "
            "Genera el formato base con: amazon-sp aplus template > base.json")

    # Detectar placeholders sin reemplazar (warning, no error duro)
    raw = file_path.read_text()
    placeholders = []
    if "REEMPLAZA_NOMBRE_INTERNO" in raw:
        placeholders.append("nombre")
    if "REEMPLAZA_CON_UPLOAD_DESTINATION_ID" in raw:
        placeholders.append("uploadDestinationId")
    if placeholders:
        eprint(f"  ⚠ El template aun tiene placeholders sin reemplazar: {', '.join(placeholders)}")
        eprint("    Amazon probablemente rechazara el draft o el approval. Continua bajo tu responsabilidad.")

    env             = load_env()
    creds           = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    from sp_api.base.exceptions import SellingApiException

    client = _aplus_client(creds, marketplace)
    try:
        result = client.create_content_document(marketplaceId=mid, body=body)
    except SellingApiException as e:
        die(f"create_content_document fallo:\n    {e}")

    payload = result.payload or {}
    key     = payload.get("contentReferenceKey")
    warns   = payload.get("warnings") or []

    if args.json:
        out_json(payload)
        return

    hr("✓ A+ Content document creado")
    print(f"  contentReferenceKey : {key}")
    print(f"  Status              : DRAFT")
    if warns:
        print()
        print("  Warnings de Amazon:")
        for w in warns:
            print(f"    [{w.get('code','?')}] {w.get('details','?')}")
    print()
    print("  Siguientes pasos:")
    print(f"    1. amazon-sp aplus apply {key} --asin <ASIN>")
    print(f"    2. amazon-sp aplus submit {key} --confirm")
    print()


def cmd_aplus_apply(args):
    require_sp_api()
    env             = load_env()
    creds           = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    asins = [a.strip().upper() for a in args.asin if a.strip()]
    if not asins:
        die("Debes pasar al menos un --asin")

    from sp_api.base.exceptions import SellingApiException

    client = _aplus_client(creds, marketplace)

    body = {
        "asinSet": asins,
    }

    try:
        result = client.post_content_document_asin_relations(
            args.doc_id,
            marketplaceId=mid,
            body=body,
        )
    except SellingApiException as e:
        die(f"post_content_document_asin_relations fallo:\n    {e}")

    payload = result.payload or {}

    if args.json:
        out_json(payload)
        return

    hr(f"✓ ASINs ligados al document {args.doc_id}")
    for asin in asins:
        print(f"  {asin}")
    warns = payload.get("warnings") or []
    if warns:
        print()
        print("  Warnings:")
        for w in warns:
            print(f"    [{w.get('code','?')}] {w.get('details','?')}")
    print()
    print("  Siguiente paso: submit a Amazon para approval")
    print(f"    amazon-sp aplus submit {args.doc_id} --confirm")
    print()


def cmd_aplus_submit(args):
    if not args.confirm:
        hr("aplus submit — DRY RUN  (sin --confirm)")
        print(f"  Document     : {args.doc_id}")
        print(f"  Marketplace  : {args.marketplace or '(default del .env)'}")
        print()
        print("  Para realmente submittear (Amazon empezara el review, 24-72h):")
        mp = f" --marketplace {args.marketplace}" if args.marketplace else ""
        print(f"    amazon-sp aplus submit {args.doc_id}{mp} --confirm")
        print()
        print("  ATENCION: tras submit, el documento entra en review y los ASINs")
        print("  ligados muestran el A+ Content publico cuando Amazon lo apruebe.")
        return

    require_sp_api()
    env             = load_env()
    creds           = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    from sp_api.base.exceptions import SellingApiException

    client = _aplus_client(creds, marketplace)
    try:
        result = client.post_content_document_approval_submission(
            args.doc_id,
            marketplaceId=mid,
        )
    except SellingApiException as e:
        die(f"post_content_document_approval_submission fallo:\n    {e}")

    if args.json:
        out_json(result.payload or {})
        return

    hr(f"✓ Submit a approval enviado — {args.doc_id}")
    print(f"  Amazon revisará el documento en 24-72h.")
    print(f"  Trackea con:")
    print(f"    amazon-sp aplus get {args.doc_id}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# SYNC — comparacion Shopify <-> Amazon (Sprint 3, read-only por defecto)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Detecta drift entre el catalogo Shopify (source of truth) y Amazon (FBA).
# Por defecto solo reporta. Con --emit-feed PATH escribe un JSON_LISTINGS_FEED
# que el usuario puede revisar y submittear con `amazon-sp feeds submit ... --confirm`.
#
# Importante: FBA stock NO se sincroniza numericamente — es stock fisico en
# warehouses de Amazon. Lo unico que el feed actualiza son precios (price drift).

def _pull_shopify_variants(store_alias: str | None) -> list[dict]:
    """Ejecuta `shopify-admin --json variant list` y devuelve la lista aplanada."""
    if not shutil.which("shopify-admin"):
        die(
            "shopify-admin no esta en PATH. Instala el CLI desde:\n"
            "    bash ~/Documents/Workspace/mcp-toolkits/repo/shopify-admin-cli/install.sh"
        )

    cmd = ["shopify-admin", "--json"]
    if store_alias:
        cmd.extend(["--store", store_alias])
    cmd.extend(["variant", "list", "--status", "ACTIVE", "--limit", "250"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
    except subprocess.CalledProcessError as e:
        die(f"shopify-admin fallo (exit {e.returncode}):\n{e.stderr[:600]}")
    except subprocess.TimeoutExpired:
        die("shopify-admin timeout (>120s)")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        die(f"Output de shopify-admin no es JSON valido: {e}\n{result.stdout[:300]}")

    if not isinstance(data, list):
        die(f"Output de shopify-admin no es una lista: {type(data).__name__}")
    return data


def _pull_amazon_inventory(creds: dict, marketplace, mid: str) -> list[dict]:
    """Inventario FBA actual."""
    from sp_api.api import Inventories
    client = Inventories(credentials=creds, marketplace=marketplace)
    result = client.get_inventory_summary_marketplace(
        details=True,
        granularityType="Marketplace",
        granularityId=mid,
        marketplaceIds=[mid],
    )
    return (result.payload or {}).get("inventorySummaries", []) or []


def _pull_amazon_listings(creds: dict, marketplace, mid: str) -> list[dict]:
    """
    Pull all listings via Reports async flow.
    Reutiliza la logica de cmd_listings (Reports → poll → download → TSV parse).
    """
    from sp_api.api import Reports
    from sp_api.base.reportTypes import ReportType
    from sp_api.base.exceptions import SellingApiException

    reports_client = Reports(credentials=creds, marketplace=marketplace)

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

    final = _wait_for_report(reports_client, report_id, timeout_s=240, poll_s=10)
    if final.get("processingStatus") != "DONE":
        die(f"Report no completo (status={final.get('processingStatus')})")

    doc_id = final.get("reportDocumentId")
    if not doc_id:
        return []  # empty report

    try:
        doc_resp = reports_client.get_report_document(doc_id)
    except SellingApiException as e:
        die(f"get_report_document fallo:\n    {e}")

    url         = (doc_resp.payload or {}).get("url")
    compression = (doc_resp.payload or {}).get("compressionAlgorithm")
    if not url:
        die("Document sin URL.")

    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read()
    if compression == "GZIP":
        data = gzip.decompress(data)

    text   = data.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    return list(reader)


def _compute_sync_drift(shopify_variants: list[dict],
                       amazon_inv: list[dict],
                       amazon_listings: list[dict]) -> dict:
    """
    Cruza los 3 datasets por SKU exacto y construye 4 buckets:
      - shopify_only:  SKU en Shopify pero NO en Amazon → oportunidad de listing
      - amazon_only:   SKU en Amazon pero NO en Shopify → orphan / SKU autogenerada
      - matched:       SKU en ambos → con price drift, status, qty
      - reactivation:  Subset de matched: Amazon=Inactive + Shopify tiene stock
    """
    # Diccionarios por SKU (filtrar vacios)
    s_by_sku = {v["sku"]: v for v in shopify_variants if v.get("sku")}
    a_inv_by_sku = {s["sellerSku"]: s for s in amazon_inv if s.get("sellerSku")}
    a_list_by_sku = {r.get("seller-sku"): r for r in amazon_listings if r.get("seller-sku")}

    s_skus = set(s_by_sku)
    a_skus = set(a_list_by_sku)
    in_both = s_skus & a_skus

    matched = []
    for sku in sorted(in_both):
        s = s_by_sku[sku]
        a_listing = a_list_by_sku[sku]
        a_inv     = a_inv_by_sku.get(sku, {})

        try:    s_price = float(s.get("price") or 0)
        except: s_price = 0.0
        try:    a_price_raw = a_listing.get("price")
        except: a_price_raw = None
        try:    a_price = float(a_price_raw) if a_price_raw else None
        except: a_price = None

        try:    s_qty = int(s.get("inventoryQuantity") or 0)
        except: s_qty = 0
        a_qty = ((a_inv.get("inventoryDetails") or {}).get("fulfillableQuantity") or 0)

        price_drift     = (a_price - s_price) if (a_price is not None) else None
        price_drift_pct = ((a_price - s_price) / s_price * 100) if (a_price and s_price > 0) else None

        matched.append({
            "sku":             sku,
            "shopify_title":   s.get("displayName") or s.get("productTitle") or "",
            "shopify_qty":     s_qty,
            "shopify_price":   s_price,
            "amazon_asin":     a_listing.get("asin1") or "",
            "amazon_status":   a_listing.get("status") or "",
            "amazon_qty":      a_qty,
            "amazon_price":    a_price,
            "price_drift":     price_drift,
            "price_drift_pct": price_drift_pct,
        })

    reactivation = [
        m for m in matched
        if m["amazon_status"] == "Inactive" and m["shopify_qty"] > 0
    ]

    return {
        "shopify_only": [s_by_sku[sku] for sku in sorted(s_skus - a_skus)],
        "amazon_only":  sorted(a_skus - s_skus),
        "matched":      matched,
        "reactivation": reactivation,
    }


def _print_sync_report(drift: dict, marketplace) -> None:
    matched      = drift["matched"]
    shopify_only = drift["shopify_only"]
    amazon_only  = drift["amazon_only"]
    reactivation = drift["reactivation"]

    hr(f"Sync Shopify ↔ Amazon ({marketplace.name})")
    print(f"  En ambos lados      : {len(matched):>4}")
    print(f"  Solo en Shopify     : {len(shopify_only):>4}  ← oportunidades de listing")
    print(f"  Solo en Amazon      : {len(amazon_only):>4}  ← orphan / SKU autogenerada")
    print(f"  Reactivacion        : {len(reactivation):>4}  ← Amazon Inactive + Shopify tiene stock")

    if not (matched or shopify_only or amazon_only):
        print("\n  Sin datos cruzables. Verifica que ambas tiendas estan poblando.")
        return

    # Matched: detalle con price drift
    if matched:
        with_drift = [m for m in matched if m["price_drift_pct"] is not None]
        big_drift  = [m for m in with_drift if abs(m["price_drift_pct"]) >= 5]
        print()
        print(f"  ── Matched ({len(matched)}, {len(big_drift)} con drift ≥5%) ──")
        print(f"  {'SKU':<22} {'Shopify':>9} {'Amazon':>9} {'Drift':>8}  Status      Title")
        print(f"  {'─'*22} {'─'*9} {'─'*9} {'─'*8}  {'─'*10}  {'─'*30}")
        for m in matched[:20]:
            sp = f"${m['shopify_price']:.2f}"
            ap = f"${m['amazon_price']:.2f}" if m['amazon_price'] is not None else "—"
            dp = f"{m['price_drift_pct']:+.1f}%" if m['price_drift_pct'] is not None else "—"
            st = short(m['amazon_status'], 10)
            ti = short(m['shopify_title'], 30)
            print(f"  {short(m['sku'],22):<22} {sp:>9} {ap:>9} {dp:>8}  {st:<10}  {ti}")
        if len(matched) > 20:
            print(f"  ... y {len(matched) - 20} mas (usa --json para todos)")

    # Reactivation
    if reactivation:
        print()
        print(f"  ── Reactivacion candidatos ({len(reactivation)}) ──")
        for m in reactivation[:10]:
            print(f"  {m['sku']:<24} ${m['shopify_price']:>7.2f}  "
                  f"Shopify stock: {m['shopify_qty']}  →  {short(m['shopify_title'], 40)}")

    # Shopify-only — sample
    if shopify_only:
        print()
        n = min(10, len(shopify_only))
        print(f"  ── Solo en Shopify (primeros {n} de {len(shopify_only)}) ──")
        for v in shopify_only[:n]:
            sku   = v.get("sku") or "—"
            qty   = v.get("inventoryQuantity") or 0
            price = v.get("price") or "?"
            name  = short(v.get("displayName") or v.get("productTitle") or "", 40)
            print(f"  {sku:<22} stock={qty:<5}  ${price:<7}  {name}")

    # Amazon-only — sample
    if amazon_only:
        print()
        n = min(10, len(amazon_only))
        print(f"  ── Solo en Amazon (primeros {n} de {len(amazon_only)}) ──")
        for sku in amazon_only[:n]:
            print(f"  {sku}")

    print()


def _write_listings_feed(drift: dict, feed_path: Path, marketplace_id: str,
                         seller_id: str, product_type: str,
                         min_drift_pct: float = 1.0) -> int:
    """
    Genera un JSON_LISTINGS_FEED con price patches para SKUs con drift de precio.

    Solo incluye items donde |price_drift_pct| >= min_drift_pct.
    El precio Shopify se trata como source of truth (se push a Amazon).

    Retorna el numero de mensajes en el feed.
    """
    messages = []
    msg_id = 0
    for m in drift["matched"]:
        if m.get("price_drift_pct") is None:
            continue
        if abs(m["price_drift_pct"]) < min_drift_pct:
            continue
        msg_id += 1
        messages.append({
            "messageId":     msg_id,
            "sku":           m["sku"],
            "operationType": "PATCH",
            "productType":   product_type,
            "patches": [{
                "op":    "replace",
                "path":  "/attributes/purchasable_offer",
                "value": [{
                    "marketplace_id": marketplace_id,
                    "currency":       "USD",
                    "our_price":      [{"schedule": [{"value_with_tax": m["shopify_price"]}]}],
                }],
            }],
        })

    feed_doc = {
        "header": {
            "sellerId":    seller_id,
            "version":     "2.0",
            "issueLocale": "en_US",
        },
        "messages": messages,
    }

    feed_path.parent.mkdir(parents=True, exist_ok=True)
    feed_path.write_text(json.dumps(feed_doc, indent=2))
    return len(messages)


def cmd_sync(args):
    require_sp_api()

    env              = load_env()
    creds            = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    eprint("  → Pulling Shopify variants (vía shopify-admin)...")
    s_variants = _pull_shopify_variants(args.shopify_store)
    eprint(f"  → {len(s_variants)} variantes Shopify ACTIVE")

    eprint("  → Pulling Amazon FBA inventory...")
    a_inv = _pull_amazon_inventory(creds, marketplace, mid)
    eprint(f"  → {len(a_inv)} SKUs FBA en {marketplace.name}")

    eprint("  → Pulling Amazon all listings (Reports async, ~30s)...")
    a_listings = _pull_amazon_listings(creds, marketplace, mid)
    eprint(f"  → {len(a_listings)} listings en Amazon")

    drift = _compute_sync_drift(s_variants, a_inv, a_listings)

    if args.json:
        out_json(drift)
        return

    _print_sync_report(drift, marketplace)

    if args.emit_feed:
        if not args.product_type:
            die("--emit-feed requiere --product-type (ej: BRACELET, NECKLACE, EARRING, RING).\n"
                "    El JSON_LISTINGS_FEED necesita un productType por mensaje. Para feeds\n"
                "    con varios tipos, genera uno por tipo.")

        feed_path = Path(args.emit_feed).expanduser().resolve()
        seller_id = env.get("AMAZON_SELLER_ID") or "__SET_AMAZON_SELLER_ID_IN_ENV__"

        n = _write_listings_feed(
            drift, feed_path, mid, seller_id, args.product_type,
            min_drift_pct=args.min_drift_pct,
        )

        print(f"  Feed con {n} mensajes escrito en:")
        print(f"    {feed_path}")
        if "__SET_" in seller_id:
            print()
            print("  ⚠ sellerId es placeholder. Define AMAZON_SELLER_ID en ~/.env.amazon:")
            print("    Seller Central → Settings → Account Info → Merchant Token")
        if n == 0:
            print()
            print(f"  (0 mensajes — ningun SKU tenia price drift >= {args.min_drift_pct}%)")
        else:
            print()
            print("  Para submittear (DESTRUCTIVO — actualiza precios en Amazon):")
            print(f"    amazon-sp feeds submit {feed_path} \\")
            print(f"      --type JSON_LISTINGS_FEED --confirm")
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

# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS — Search Query Performance + Sales & Traffic (Brand Analytics)
# ═══════════════════════════════════════════════════════════════════════════════

def _analytics_fetch(marketplace, mid, creds, report_type, start, end,
                     report_options=None, timeout_s=900, poll_s=10):
    """Crea un report analitico, espera a que termine y devuelve el JSON parseado.

    Devuelve None si termina DONE pero sin documento (= no hay datos para ese
    ASIN/periodo, que es distinto de un fallo).
    """
    from sp_api.api import Reports
    from sp_api.base.exceptions import SellingApiException

    rc = Reports(credentials=creds, marketplace=marketplace)

    kwargs = dict(
        reportType=report_type,
        marketplaceIds=[mid],
        dataStartTime=f"{start}T00:00:00Z",
        dataEndTime=f"{end}T23:59:59Z",
    )
    if report_options:
        kwargs["reportOptions"] = report_options

    try:
        resp = rc.create_report(**kwargs)
    except SellingApiException as e:
        die(f"create_report fallo:\n    {e}\n\n"
            f"    Recuerda: WEEK = domingo a sabado, MONTH = mes natural completo.\n"
            f"    Una peticion no puede cruzar dos periodos.")

    rid = (resp.payload or {}).get("reportId")
    if not rid:
        die(f"create_report sin reportId: {resp.payload}")
    eprint(f"  → reportId: {rid}  (los reports analiticos tardan 3-6 min)")

    deadline = time.time() + timeout_s
    last = {}
    while time.time() < deadline:
        last = rc.get_report(rid).payload or {}
        st = last.get("processingStatus")
        if st in ("DONE", "CANCELLED", "FATAL"):
            eprint(f"  → {st}")
            break
        time.sleep(poll_s)

    st = last.get("processingStatus")
    if st != "DONE":
        die(f"El report termino en {st or 'TIMEOUT'} (reportId {rid})")

    doc_id = last.get("reportDocumentId")
    if not doc_id:
        return None

    doc = rc.get_report_document(doc_id, download=True, decrypt=True)
    p = doc.payload
    body = p.get("document") if isinstance(p, dict) else p
    return json.loads(body) if isinstance(body, str) else body


def _money(x):
    """Los importes vienen como {'amount': N, 'currencyCode': 'USD'} o sueltos."""
    return x.get("amount") if isinstance(x, dict) else x


def cmd_sqp(args):
    """Search Query Performance — volumen real y embudo por consulta de busqueda."""
    require_sp_api()

    env              = load_env()
    creds            = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    eprint(f"  → Search Query Performance — {args.asin} — "
           f"{args.start} a {args.end} ({args.period})")

    data = _analytics_fetch(
        marketplace, mid, creds,
        "GET_BRAND_ANALYTICS_SEARCH_QUERY_PERFORMANCE_REPORT",
        args.start, args.end,
        {"asin": args.asin, "reportPeriod": args.period},
        timeout_s=args.timeout,
    )

    if data is None:
        hr(f"Search Query Performance — {args.asin} — {marketplace.name}")
        print("  (sin datos: el ASIN no aparecio en ninguna consulta ese periodo)")
        print("  Los datos salen con varios dias de retraso — prueba un periodo anterior.")
        print()
        return

    if args.json:
        out_json(data)
        return

    rows = data.get("dataByAsin", [])
    spec = data.get("reportSpecification", {})

    hr(f"Search Query Performance — {args.asin} — {marketplace.name}")
    print(f"  Periodo : {spec.get('dataStartTime')} a {spec.get('dataEndTime')}")
    print(f"  Consultas donde aparece el ASIN: {len(rows)}\n")

    if not rows:
        print("  (report vacio)\n")
        return

    parsed = []
    T = dict(imp=0, cl=0, ca=0, pu=0, mimp=0, mcl=0, mpu=0)
    for r in rows:
        q  = r.get("searchQueryData", {})
        i  = r.get("impressionData", {})
        c  = r.get("clickData", {})
        ca = r.get("cartAddData", {})
        pu = r.get("purchaseData", {})
        parsed.append((
            q.get("searchQuery", "?"),
            q.get("searchQueryVolume", 0),
            i.get("totalQueryImpressionCount", 0),
            i.get("asinImpressionCount", 0),
            c.get("asinClickCount", 0),
            pu.get("asinPurchaseCount", 0),
            _money(pu.get("totalMedianPurchasePrice")),
        ))
        T["imp"]  += i.get("asinImpressionCount", 0)
        T["cl"]   += c.get("asinClickCount", 0)
        T["ca"]   += ca.get("asinCartAddCount", 0)
        T["pu"]   += pu.get("asinPurchaseCount", 0)
        T["mimp"] += i.get("totalQueryImpressionCount", 0)
        T["mcl"]  += c.get("totalClickCount", 0)
        T["mpu"]  += pu.get("totalPurchaseCount", 0)

    parsed.sort(key=lambda x: -x[1])
    limit = args.limit or len(parsed)

    print(f"  {'CONSULTA':<46}{'Volumen':>10}{'ImpMercado':>12}{'ImpTuyas':>10}"
          f"{'Clics':>7}{'Compras':>9}{'PrecioMed':>11}")
    print(f"  {'─'*46}{'─'*10}{'─'*12}{'─'*10}{'─'*7}{'─'*9}{'─'*11}")
    for q, vol, mimp, aimp, clicks, purch, price in parsed[:limit]:
        pr = f"${price:.2f}" if price else "—"
        print(f"  {short(q, 45):<46}{vol:>10,}{mimp:>12,}{aimp:>10,}"
              f"{clicks:>7,}{purch:>9,}{pr:>11}")
    if limit < len(parsed):
        print(f"  ... y {len(parsed)-limit} consultas mas (usa --limit 0 para todas)")

    print(f"  {'─'*105}")
    ctr_t = (T["cl"]  / T["imp"]  * 100) if T["imp"]  else 0.0
    ctr_m = (T["mcl"] / T["mimp"] * 100) if T["mimp"] else 0.0
    share = (T["imp"] / T["mimp"] * 100) if T["mimp"] else 0.0
    print(f"  TUYO     impresiones={T['imp']:,}  clics={T['cl']:,}  "
          f"carritos={T['ca']:,}  compras={T['pu']:,}")
    print(f"  MERCADO  impresiones={T['mimp']:,}  clics={T['mcl']:,}  compras={T['mpu']:,}")
    print(f"  CTR tuyo={ctr_t:.2f}%   CTR mercado={ctr_m:.2f}%   "
          f"cuota de impresiones={share:.2f}%")
    print()


def cmd_traffic(args):
    """Sales & Traffic — sesiones, page views y conversion por dia y por ASIN."""
    require_sp_api()

    env              = load_env()
    creds            = get_credentials(env)
    marketplace, mid = resolve_marketplace(env, args.marketplace)

    eprint(f"  → Sales & Traffic — {args.start} a {args.end}")

    data = _analytics_fetch(
        marketplace, mid, creds,
        "GET_SALES_AND_TRAFFIC_REPORT",
        args.start, args.end,
        timeout_s=args.timeout,
    )

    if data is None:
        hr(f"Sales & Traffic — {marketplace.name}")
        print("  (sin datos para ese periodo)\n")
        return

    if args.json:
        out_json(data)
        return

    by_date = data.get("salesAndTrafficByDate", []) or []
    by_asin = data.get("salesAndTrafficByAsin", []) or []

    hr(f"Sales & Traffic — {marketplace.name} — {args.start} a {args.end}")

    if by_date:
        print(f"\n  POR DIA")
        print(f"  {'Fecha':<12}{'Ventas':>12}{'Uds':>6}{'Sesiones':>10}"
              f"{'PageViews':>11}{'BuyBox%':>9}")
        print(f"  {'─'*12}{'─'*12}{'─'*6}{'─'*10}{'─'*11}{'─'*9}")
        tv = tu = ts = tp = 0
        for r in by_date:
            s = r.get("salesByDate", {}); t = r.get("trafficByDate", {})
            v = _money(s.get("orderedProductSales")) or 0
            u = s.get("unitsOrdered", 0) or 0
            se = t.get("sessions", 0) or 0
            pv = t.get("pageViews", 0) or 0
            bb = t.get("buyBoxPercentage", 0) or 0
            tv += v; tu += u; ts += se; tp += pv
            print(f"  {r.get('date','?'):<12}${v:>11,.2f}{u:>6,}{se:>10,}{pv:>11,}{bb:>8.1f}%")
        print(f"  {'─'*60}")
        conv = (tu / ts * 100) if ts else 0.0
        print(f"  {'TOTAL':<12}${tv:>11,.2f}{tu:>6,}{ts:>10,}{tp:>11,}")
        print(f"  Conversion (uds/sesiones): {conv:.2f}%")

    if by_asin:
        print(f"\n  POR ASIN  ({len(by_asin)} con actividad)")
        print(f"  {'ASIN':<14}{'Sesiones':>10}{'PageViews':>11}{'Uds':>6}"
              f"{'Conv%':>8}{'Ventas':>13}")
        print(f"  {'─'*14}{'─'*10}{'─'*11}{'─'*6}{'─'*8}{'─'*13}")
        rows = sorted(by_asin,
                      key=lambda x: -(x.get("trafficByAsin", {}).get("sessions", 0) or 0))
        for r in rows[: (args.limit or len(rows))]:
            s = r.get("salesByAsin", {}); t = r.get("trafficByAsin", {})
            asin = r.get("childAsin") or r.get("parentAsin") or "?"
            conv = f"{t.get('unitSessionPercentage',0) or 0:.1f}%"
            ventas = f"${_money(s.get('orderedProductSales')) or 0:,.2f}"
            print(f"  {asin:<14}{t.get('sessions',0) or 0:>10,}"
                  f"{t.get('pageViews',0) or 0:>11,}{s.get('unitsOrdered',0) or 0:>6,}"
                  f"{conv:>8}{ventas:>13}")
    print()


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
  amazon-sp shop                                # info cuenta seller
  amazon-sp inventory                           # stock FBA en marketplace base
  amazon-sp inventory --marketplace CA          # stock FBA en Canada
  amazon-sp listings                            # TODOS los listings (async Reports)
  amazon-sp orders --since 7daysAgo             # pedidos ultimos 7 dias
  amazon-sp orders --since 30daysAgo --details  # con buyer info via RDT (lento)
  amazon-sp pricing B0XXXXXXX                   # tu precio + competencia + Buy Box
  amazon-sp catalog search "silver necklace"    # top 10 catalogo Amazon
  amazon-sp catalog get B0XXXXXXX               # detalle completo de un ASIN
  amazon-sp fees B0XXXXXXX --price 29.99        # estimacion referral + FBA fees
  amazon-sp reports list                        # reports historicos (read-only)
  amazon-sp feeds list                          # feeds recientes (read-only)
  amazon-sp feeds submit FILE --type X          # bulk feed (DESTRUCTIVO, requiere --confirm)
  amazon-sp sync                                # cruzar Shopify <-> Amazon (read-only)
  amazon-sp sync --emit-feed price.json \\
    --product-type BRACELET --min-drift-pct 5   # genera feed de price patches

  # A+ Content (Brand Registry, modulos visuales en la pagina de producto)
  amazon-sp aplus list                          # documentos A+ en tu cuenta
  amazon-sp aplus upload-image foto.jpg         # sube imagen, devuelve uploadDestinationId
  amazon-sp aplus template > my.json            # template base, editar
  amazon-sp aplus create my.json                # crea draft
  amazon-sp aplus apply <KEY> --asin <ASIN>     # linkea doc <-> ASIN
  amazon-sp aplus submit <KEY> --confirm        # envia a review Amazon (24-72h)

  # Analytics (Brand Analytics — requiere Brand Registry)
  amazon-sp sqp B0XXXXXXX 2026-07-26 2026-08-01   # volumen real y embudo por consulta
  amazon-sp sqp B0XXXXXXX 2026-07-01 2026-07-31 --period MONTH
  amazon-sp traffic 2026-07-26 2026-08-01         # sesiones y conversion por dia y ASIN
  amazon-sp traffic 2026-07-26 2026-08-01 --json  # crudo, para guardar

  Fechas: WEEK = domingo a sabado · MONTH = mes natural · QUARTER = trimestre.
  Una peticion no puede cruzar dos periodos. Los datos salen con dias de retraso
  y el report tarda 3-6 min en procesarse.

  amazon-sp config show                         # credenciales (enmascaradas)

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
    sp_cat     = sub.add_parser("catalog", help="Catalogo Amazon (search / get)")
    sp_cat_sub = sp_cat.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")
    sp_cat_s   = sp_cat_sub.add_parser("search", help="Buscar productos por keyword")
    _add_marketplace_flag(sp_cat_s)
    sp_cat_s.add_argument("query", metavar="QUERY", help="Keywords a buscar")

    sp_cat_g = sp_cat_sub.add_parser("get", help="Detalle completo de un ASIN")
    _add_marketplace_flag(sp_cat_g)
    sp_cat_g.add_argument("asin", metavar="ASIN", help="ASIN Amazon (ej: B0XXXXXXX)")

    # ── fees ───────────────────────────────────────────────────────────────────
    sp_fees = sub.add_parser("fees", help="Estimacion referral + FBA fees para un ASIN")
    _add_marketplace_flag(sp_fees)
    sp_fees.add_argument("asin", metavar="ASIN")
    sp_fees.add_argument("--price",    type=float, required=True,
                         help="Precio de venta asumido (ej: 29.99)")
    sp_fees.add_argument("--shipping", type=float, default=0.0,
                         help="Costo de envio asumido (default 0)")
    sp_fees.add_argument("--currency", default="USD", metavar="USD|MXN|CAD",
                         help="Moneda (default USD)")
    sp_fees.add_argument("--no-fba",   action="store_true",
                         help="Asumir MFN (seller-fulfilled). Default: FBA.")

    # ── reports ────────────────────────────────────────────────────────────────
    sp_rep     = sub.add_parser("reports", help="Reports historicos (read-only)")
    sp_rep_sub = sp_rep.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")
    sp_rep_l   = sp_rep_sub.add_parser("list", help="Listar reports recientes")
    _add_marketplace_flag(sp_rep_l)
    sp_rep_l.add_argument("--type", "-t", metavar="REPORT_TYPE",
                          help="Filtrar por tipo (default: tipos comunes)")
    sp_rep_l.add_argument("--limit", type=int, default=20, metavar="N",
                          help="Maximo de resultados (default 20, max 100)")

    # ── feeds ──────────────────────────────────────────────────────────────────
    sp_f     = sub.add_parser("feeds", help="Bulk feeds (list / submit)")
    sp_f_sub = sp_f.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")

    sp_f_l = sp_f_sub.add_parser("list", help="Listar feeds recientes")
    _add_marketplace_flag(sp_f_l)
    sp_f_l.add_argument("--type", "-t", metavar="FEED_TYPE",
                        help="Filtrar por tipo (default: tipos comunes)")
    sp_f_l.add_argument("--limit", type=int, default=20, metavar="N",
                        help="Maximo de resultados (default 20)")

    sp_f_s = sp_f_sub.add_parser(
        "submit",
        help="Submittear un feed (DESTRUCTIVO — requiere --confirm)",
    )
    _add_marketplace_flag(sp_f_s)
    sp_f_s.add_argument("file", metavar="FILE", help="Ruta al archivo a subir (TSV/CSV/XML/JSON)")
    sp_f_s.add_argument("--type", required=True, metavar="FEED_TYPE",
                        help="Tipo de feed (ej: POST_PRODUCT_DATA, JSON_LISTINGS_FEED)")
    sp_f_s.add_argument("--content-type", metavar="MIME",
                        help="Override content-type HTTP (default: inferido por extension)")
    sp_f_s.add_argument("--confirm", action="store_true",
                        help="Confirmar submit real. Sin esto el comando hace dry-run.")

    # ── aplus ──────────────────────────────────────────────────────────────────
    sp_ap     = sub.add_parser("aplus", help="A+ Content (modulos visuales, requiere Brand Registry)")
    sp_ap_sub = sp_ap.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")

    sp_ap_l = sp_ap_sub.add_parser("list", help="Listar A+ documents de la cuenta")
    _add_marketplace_flag(sp_ap_l)

    sp_ap_g = sp_ap_sub.add_parser("get", help="Detalle completo de un document")
    _add_marketplace_flag(sp_ap_g)
    sp_ap_g.add_argument("doc_id", metavar="DOC_ID", help="contentReferenceKey")

    sp_ap_as = sp_ap_sub.add_parser("asins", help="ASINs ligados a un document")
    _add_marketplace_flag(sp_ap_as)
    sp_ap_as.add_argument("doc_id", metavar="DOC_ID", help="contentReferenceKey")

    sp_ap_up = sp_ap_sub.add_parser("upload-image", help="Sube una imagen, devuelve uploadDestinationId")
    _add_marketplace_flag(sp_ap_up)
    sp_ap_up.add_argument("file", metavar="FILE", help="Ruta a la imagen (JPG/PNG recomendado)")
    sp_ap_up.add_argument("--content-type", metavar="MIME",
                          help="Override mime (default: inferido de la extension)")

    sp_ap_t = sp_ap_sub.add_parser("template", help="Imprime template JSON valido para `create`")

    sp_ap_c = sp_ap_sub.add_parser("create", help="Crea un draft A+ desde JSON")
    _add_marketplace_flag(sp_ap_c)
    sp_ap_c.add_argument("file", metavar="FILE", help="Path al JSON con la estructura del documento")

    sp_ap_ap = sp_ap_sub.add_parser("apply", help="Linkea un document a uno o mas ASINs")
    _add_marketplace_flag(sp_ap_ap)
    sp_ap_ap.add_argument("doc_id", metavar="DOC_ID", help="contentReferenceKey")
    sp_ap_ap.add_argument("--asin", action="append", required=True, metavar="ASIN",
                          help="ASIN a linkear (repetible: --asin A --asin B)")

    sp_ap_s = sp_ap_sub.add_parser(
        "submit",
        help="Submittea un document a Amazon para approval (DESTRUCTIVO — requiere --confirm)",
    )
    _add_marketplace_flag(sp_ap_s)
    sp_ap_s.add_argument("doc_id", metavar="DOC_ID", help="contentReferenceKey")
    sp_ap_s.add_argument("--confirm", action="store_true",
                         help="Confirma el submit real. Sin esto el comando hace dry-run.")

    # ── sync ───────────────────────────────────────────────────────────────────
    sp_sync = sub.add_parser(
        "sync",
        help="Cruzar catalogo Shopify ↔ Amazon (detectar drift, listings huerfanos, reactivacion)",
    )
    _add_marketplace_flag(sp_sync)
    sp_sync.add_argument("--shopify-store", metavar="ALIAS",
                         help="Store alias en shopify-admin (default: el default configurado)")
    sp_sync.add_argument("--emit-feed", metavar="PATH",
                         help="Escribe un JSON_LISTINGS_FEED con price patches para SKUs con drift. "
                              "NO submitea — usa amazon-sp feeds submit --confirm para eso.")
    sp_sync.add_argument("--product-type", metavar="TYPE",
                         help="Required con --emit-feed. ProductType Amazon (BRACELET, NECKLACE, etc.)")
    sp_sync.add_argument("--min-drift-pct", type=float, default=1.0, metavar="N",
                         help="Solo emite feed para SKUs con drift de precio >= N%% (default 1)")

    # ── config ─────────────────────────────────────────────────────────────────
    # ── sqp (Search Query Performance) ─────────────────────────────────────────
    sp_sqp = sub.add_parser(
        "sqp",
        help="Search Query Performance: volumen real y embudo por consulta (Brand Analytics)",
    )
    sp_sqp.add_argument("asin", help="ASIN (o varios separados por espacio, max 200 chars)")
    sp_sqp.add_argument("start", help="Inicio del periodo (YYYY-MM-DD)")
    sp_sqp.add_argument("end", help="Fin del periodo (YYYY-MM-DD)")
    sp_sqp.add_argument("--period", default="WEEK", choices=["WEEK", "MONTH", "QUARTER"],
                        help="WEEK = domingo a sabado (default)")
    sp_sqp.add_argument("--limit", type=int, default=25,
                        help="Maximo de consultas a mostrar (0 = todas, default 25)")
    sp_sqp.add_argument("--timeout", type=int, default=900,
                        help="Segundos de espera al report (default 900)")
    _add_marketplace_flag(sp_sqp)

    # ── traffic (Sales & Traffic) ──────────────────────────────────────────────
    sp_tr = sub.add_parser(
        "traffic",
        help="Sesiones, page views y conversion por dia y por ASIN",
    )
    sp_tr.add_argument("start", help="Inicio (YYYY-MM-DD)")
    sp_tr.add_argument("end", help="Fin (YYYY-MM-DD)")
    sp_tr.add_argument("--limit", type=int, default=25,
                       help="Maximo de ASINs a mostrar (0 = todos, default 25)")
    sp_tr.add_argument("--timeout", type=int, default=900,
                       help="Segundos de espera al report (default 900)")
    _add_marketplace_flag(sp_tr)

    sp_cfg     = sub.add_parser("config", help="Configuracion local")
    sp_cfg_sub = sp_cfg.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")
    sp_cfg_sub.add_parser("show", help="Ver credenciales cargadas (enmascaradas)")

    args = p.parse_args()
    cmd  = args.command
    sub_ = getattr(args, "subcommand", None)

    dispatch = {
        ("shop",      None):           cmd_shop,
        ("inventory", None):           cmd_inventory,
        ("listings",  None):           cmd_listings,
        ("orders",    None):           cmd_orders,
        ("pricing",   None):           cmd_pricing,
        ("catalog",   "search"):       cmd_catalog_search,
        ("catalog",   "get"):          cmd_catalog_get,
        ("fees",      None):           cmd_fees,
        ("reports",   "list"):         cmd_reports_list,
        ("feeds",     "list"):         cmd_feeds_list,
        ("feeds",     "submit"):       cmd_feeds_submit,
        ("aplus",     "list"):         cmd_aplus_list,
        ("aplus",     "get"):          cmd_aplus_get,
        ("aplus",     "asins"):        cmd_aplus_asins,
        ("aplus",     "upload-image"): cmd_aplus_upload_image,
        ("aplus",     "template"):     cmd_aplus_template,
        ("aplus",     "create"):       cmd_aplus_create,
        ("aplus",     "apply"):        cmd_aplus_apply,
        ("aplus",     "submit"):       cmd_aplus_submit,
        ("sync",      None):           cmd_sync,
        ("sqp",       None):           cmd_sqp,
        ("traffic",   None):           cmd_traffic,
        ("config",    "show"):         cmd_config_show,
    }

    fn = dispatch.get((cmd, sub_))
    if fn:
        fn(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()

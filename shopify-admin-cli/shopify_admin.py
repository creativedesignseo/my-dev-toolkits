#!/usr/bin/env python3
"""
shopify-admin — CLI directo para Shopify Admin GraphQL API
Adspubli · mcp-toolkits/repo/shopify-admin-cli/

Sin dependencias externas. Solo stdlib Python 3.8+.
Equivalente al gmail/ga4/gsc CLI pero para Shopify.

Uso:
  shopify-admin config add --store piro --domain piroaccessories.myshopify.com --token shpat_xxx
  shopify-admin company list
  shopify-admin company create --name "Boutique NY" --email "buyer@boutiqueny.com"
  shopify-admin catalog list
  shopify-admin pricelist create --name "Wholesale -40%" --discount 40
  shopify-admin market list
  shopify-admin product list --query "tag:wholesale"
  shopify-admin draft-order list
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# ─── Config ────────────────────────────────────────────────────────────────────

CONFIG_DIR  = Path.home() / ".shopify-admin"
CONFIG_FILE = CONFIG_DIR / "config.json"
API_VERSION = "2025-04"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {"stores": {}}
    with open(CONFIG_FILE) as f:
        return json.load(f)


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    CONFIG_FILE.chmod(0o600)  # solo lectura para el owner


def get_store(store_arg: str | None) -> dict:
    config = load_config()
    stores = config.get("stores", {})
    name   = store_arg or config.get("default")

    if not name:
        die("No hay store especificado. Usa --store o configura un default:\n"
            "  shopify-admin config default --store NOMBRE")

    if name not in stores:
        die(f"Store '{name}' no configurado.\n"
            f"  shopify-admin config add --store {name} "
            f"--domain DOMINIO.myshopify.com --token shpat_...")

    store = dict(stores[name])
    store["_name"] = name
    return store


# ─── HTTP / GraphQL ────────────────────────────────────────────────────────────

def gql(store: dict, query: str, variables: dict | None = None) -> dict:
    """Ejecuta un query/mutation GraphQL contra la Shopify Admin API."""
    domain  = store["domain"]
    token   = store["token"]
    url     = f"https://{domain}/admin/api/{API_VERSION}/graphql.json"
    payload = json.dumps({"query": query, **({"variables": variables} if variables else {})}).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "X-Shopify-Access-Token": token,
            "Content-Type":           "application/json",
            "Accept":                 "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:600]
        die(f"HTTP {e.code} desde Shopify:\n{body}")
    except urllib.error.URLError as e:
        die(f"No se pudo conectar a {domain}: {e.reason}")
    except TimeoutError:
        die("Timeout. La API de Shopify tardó demasiado.")

    if "errors" in data:
        for err in data["errors"]:
            eprint(f"  GraphQL error: {err.get('message', err)}")
        die("La operación GraphQL devolvió errores.")

    return data.get("data", {})


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


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_config_add(args):
    config = load_config()
    stores = config.setdefault("stores", {})
    domain = args.domain.replace("https://", "").replace("http://", "").rstrip("/")

    stores[args.store] = {
        "domain":  domain,
        "token":   args.token,
        "added":   datetime.now().isoformat(timespec="seconds"),
    }
    if not config.get("default"):
        config["default"] = args.store

    save_config(config)
    print(f"\n✓ Store '{args.store}' añadido → {domain}")
    if config["default"] == args.store:
        print("  (marcado como default automáticamente)")


def cmd_config_default(args):
    config = load_config()
    if args.store not in config.get("stores", {}):
        die(f"Store '{args.store}' no existe. Añádelo primero con config add.")
    config["default"] = args.store
    save_config(config)
    print(f"\n✓ Default → '{args.store}'")


def cmd_config_list(args):
    config  = load_config()
    stores  = config.get("stores", {})
    default = config.get("default", "")

    if not stores:
        print("\nNo hay stores configurados.")
        print("  shopify-admin config add --store NAME --domain DOMAIN.myshopify.com --token shpat_xxx")
        return

    hr("Stores configurados")
    for name, s in stores.items():
        marker = " ← default" if name == default else ""
        token  = s.get("token", "")
        masked = token[:10] + "..." if len(token) > 10 else "***"
        print(f"  {name}{marker}")
        print(f"    Dominio : {s['domain']}")
        print(f"    Token   : {masked}")
        print()


def cmd_config_show(args):
    config = load_config()
    masked = json.loads(json.dumps(config))  # deep copy
    for s in masked.get("stores", {}).values():
        t = s.get("token", "")
        s["token"] = (t[:10] + "..." + t[-4:]) if len(t) > 14 else "***"
    out_json(masked)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPANY
# ═══════════════════════════════════════════════════════════════════════════════

Q_COMPANY_LIST = """
query CompanyList($first: Int!, $after: String) {
  companies(first: $first, after: $after, sortKey: NAME) {
    nodes {
      id
      name
      createdAt
      mainContact {
        customer { email firstName lastName }
      }
      locations(first: 5) { nodes { id name } }
      contactCount
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

Q_COMPANY_GET = """
query CompanyGet($id: ID!) {
  company(id: $id) {
    id name note externalId createdAt updatedAt
    mainContact {
      id
      customer { id email firstName lastName phone }
    }
    locations(first: 20) {
      nodes {
        id name
        shippingAddress { address1 city province countryCode zip }
      }
    }
    contacts(first: 20) {
      nodes {
        id
        customer { email firstName lastName }
      }
    }
  }
}
"""

M_COMPANY_CREATE = """
mutation CompanyCreate($input: CompanyCreateInput!) {
  companyCreate(input: $input) {
    company {
      id name
      mainContact { id customer { email firstName lastName } }
      locations(first: 1) { nodes { id name } }
    }
    userErrors { field message code }
  }
}
"""


def cmd_company_list(args):
    store = get_store(args.store)
    data  = gql(store, Q_COMPANY_LIST, {"first": args.limit or 50})
    nodes = data.get("companies", {}).get("nodes", [])

    if not nodes:
        print("\n  No hay empresas B2B todavía.")
        return

    if args.json:
        out_json(nodes); return

    hr(f"Empresas B2B en '{store['_name']}' — {len(nodes)} encontradas")
    for c in nodes:
        mc   = (c.get("mainContact") or {}).get("customer") or {}
        locs = [l["name"] for l in c.get("locations", {}).get("nodes", [])]
        print(f"  {c['name']}")
        print(f"    ID        : {c['id']}")
        print(f"    Contacto  : {mc.get('email', '—')}")
        print(f"    Sucursales: {', '.join(locs) or '—'}")
        print(f"    Contactos : {c.get('contactCount', 0)}")
        print()


def cmd_company_get(args):
    store   = get_store(args.store)
    data    = gql(store, Q_COMPANY_GET, {"id": args.id})
    company = data.get("company")
    if not company:
        die(f"Empresa no encontrada: {args.id}")
    out_json(company)


def cmd_company_create(args):
    store = get_store(args.store)

    inp: dict = {"company": {"name": args.name}}

    if args.email:
        parts = (args.contact_name or "").strip().split(" ", 1)
        inp["companyContact"] = {
            "email":     args.email,
            "firstName": parts[0] if parts else "",
            "lastName":  parts[1] if len(parts) > 1 else "",
        }

    loc_name = args.location or "Principal"
    inp["companyLocation"] = {
        "name":                  loc_name,
        "billingSameAsShipping":  True,
        "shippingAddress": {
            "countryCode": (args.country or "US").upper(),
            "address1":    args.address or "TBD",
        },
    }

    data   = gql(store, M_COMPANY_CREATE, {"input": inp})
    result = data.get("companyCreate", {})
    errors = result.get("userErrors", [])

    if errors:
        for e in errors:
            eprint(f"  [{e.get('field','?')}] {e['message']}")
        die("No se pudo crear la empresa.")

    c    = result.get("company", {})
    mc   = (c.get("mainContact") or {}).get("customer") or {}
    locs = c.get("locations", {}).get("nodes", [])

    print(f"\n✓ Empresa creada: {c['name']}")
    print(f"  ID        : {c['id']}")
    if mc:
        print(f"  Contacto  : {mc.get('firstName','')} {mc.get('lastName','')} <{mc.get('email','')}>")
    for loc in locs:
        print(f"  Sucursal  : {loc['name']}  (ID: {loc['id']})")


# ═══════════════════════════════════════════════════════════════════════════════
# CATALOG
# ═══════════════════════════════════════════════════════════════════════════════

Q_CATALOG_LIST = """
query CatalogList($first: Int!) {
  catalogs(first: $first) {
    nodes {
      id title status
      ... on MarketCatalog {
        markets(first: 5) { nodes { id name } }
      }
      priceList {
        id name currency
        parent { adjustment { type value } }
      }
    }
  }
}
"""

M_CATALOG_CREATE = """
mutation CatalogCreate($input: CatalogCreateInput!) {
  catalogCreate(input: $input) {
    catalog { id title status }
    userErrors { field message code }
  }
}
"""


def cmd_catalog_list(args):
    store = get_store(args.store)
    data  = gql(store, Q_CATALOG_LIST, {"first": 10})
    nodes = data.get("catalogs", {}).get("nodes", [])

    if not nodes:
        print("\n  No hay catálogos B2B. Créalos en Admin → Productos → Catálogos.")
        return

    if args.json:
        out_json(nodes); return

    hr(f"Catálogos B2B ({len(nodes)}/3 máx en plan Basic)")
    for c in nodes:
        pl  = c.get("priceList") or {}
        adj = ((pl.get("parent") or {}).get("adjustment")) or {}
        t   = adj.get("type", "")
        v   = adj.get("value", 0)

        if "DECREASE" in t:   adj_str = f"-{v}%"
        elif "INCREASE" in t: adj_str = f"+{v}%"
        elif t:               adj_str = f"{t} {v}"
        else:                 adj_str = "sin ajuste"

        mkts    = c.get("markets", {}).get("nodes", []) if "markets" in c else []
        mkt_str = ", ".join(m["name"] for m in mkts) if mkts else "sin mercado asignado"

        print(f"  {c['title']}  [{c['status']}]")
        print(f"    ID         : {c['id']}")
        print(f"    Price list : {pl.get('name', '—')}  ({adj_str})")
        print(f"    Mercados   : {mkt_str}")
        print()


# ═══════════════════════════════════════════════════════════════════════════════
# PRICE LIST
# ═══════════════════════════════════════════════════════════════════════════════

Q_PRICELIST_LIST = """
query PriceListList($first: Int!) {
  priceLists(first: $first) {
    nodes {
      id name currency
      parent { adjustment { type value } }
    }
  }
}
"""

M_PRICELIST_CREATE = """
mutation PriceListCreate($input: PriceListCreateInput!) {
  priceListCreate(input: $input) {
    priceList {
      id name currency
      parent { adjustment { type value } }
    }
    userErrors { field message code }
  }
}
"""


def cmd_pricelist_list(args):
    store = get_store(args.store)
    data  = gql(store, Q_PRICELIST_LIST, {"first": 20})
    nodes = data.get("priceLists", {}).get("nodes", [])

    if not nodes:
        print("\n  No hay price lists.")
        return

    if args.json:
        out_json(nodes); return

    hr(f"Price Lists ({len(nodes)} encontradas)")
    for pl in nodes:
        adj = ((pl.get("parent") or {}).get("adjustment")) or {}
        t   = adj.get("type", "")
        v   = adj.get("value", 0)
        if "DECREASE" in t:   desc = f"-{v}% sobre precio base"
        elif "INCREASE" in t: desc = f"+{v}% sobre precio base"
        else:                 desc = f"precio fijo en {pl.get('currency','')}"
        print(f"  {pl['name']}  →  {desc}")
        print(f"    ID: {pl['id']}")
        print()


def cmd_pricelist_create(args):
    store = get_store(args.store)

    if args.discount and args.increase:
        die("Usa --discount O --increase, no ambos.")
    if not args.discount and not args.increase:
        die("Debes indicar --discount N (porcentaje de descuento) o --increase N.")

    if args.discount:
        adj_type  = "PERCENTAGE_DECREASE"
        adj_value = float(args.discount)
    else:
        adj_type  = "PERCENTAGE_INCREASE"
        adj_value = float(args.increase)

    inp = {
        "name":     args.name,
        "currency": args.currency or "USD",
        "parent":   {"adjustment": {"type": adj_type, "value": adj_value}},
    }

    data   = gql(store, M_PRICELIST_CREATE, {"input": inp})
    result = data.get("priceListCreate", {})
    errors = result.get("userErrors", [])

    if errors:
        for e in errors:
            eprint(f"  [{e.get('field','?')}] {e['message']}")
        die("No se pudo crear la price list.")

    pl  = result.get("priceList", {})
    adj = ((pl.get("parent") or {}).get("adjustment")) or {}
    t   = adj.get("type","")
    v   = adj.get("value","")
    print(f"\n✓ Price List creada: {pl['name']}")
    print(f"  ID      : {pl['id']}")
    print(f"  Moneda  : {pl.get('currency','')}")
    print(f"  Ajuste  : {'−' if 'DECREASE' in t else '+'}{v}% sobre precio retail")


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET
# ═══════════════════════════════════════════════════════════════════════════════

Q_MARKET_LIST = """
query MarketList($first: Int!) {
  markets(first: $first) {
    nodes {
      id name handle enabled primary
      regions(first: 3) {
        nodes {
          ... on MarketRegionCountry { name code }
        }
      }
    }
  }
}
"""


def cmd_market_list(args):
    store = get_store(args.store)
    data  = gql(store, Q_MARKET_LIST, {"first": 20})
    nodes = data.get("markets", {}).get("nodes", [])

    if not nodes:
        print("\n  No hay mercados. Activa Shopify Markets en Admin → Configuración.")
        return

    if args.json:
        out_json(nodes); return

    hr(f"Mercados Shopify ({len(nodes)} encontrados)")
    for m in nodes:
        status  = "✓ activo" if m.get("enabled") else "○ inactivo"
        primary = "  [primary]" if m.get("primary") else ""

        regions = [r.get("name","") for r in (m.get("regions",{}).get("nodes") or [])]
        reg_str = ", ".join(regions) if regions else "—"

        print(f"  {m['name']}{primary}  —  {status}")
        print(f"    Handle   : {m['handle']}")
        print(f"    Regiones : {reg_str}")
        print(f"    ID       : {m['id']}")
        print()


# ═══════════════════════════════════════════════════════════════════════════════
# DRAFT ORDER
# ═══════════════════════════════════════════════════════════════════════════════

Q_DRAFT_ORDER_LIST = """
query DraftOrderList($first: Int!) {
  draftOrders(first: $first, sortKey: UPDATED_AT, reverse: true) {
    nodes {
      id name status createdAt
      totalPrice
      customer { email firstName lastName }
      lineItems(first: 5) {
        nodes { title quantity originalUnitPrice }
      }
    }
  }
}
"""


def cmd_draft_order_list(args):
    store = get_store(args.store)
    data  = gql(store, Q_DRAFT_ORDER_LIST, {"first": args.limit or 20})
    nodes = data.get("draftOrders", {}).get("nodes", [])

    if not nodes:
        print("\n  No hay draft orders.")
        return

    if args.json:
        out_json(nodes); return

    hr(f"Draft Orders ({len(nodes)} recientes)")
    for o in nodes:
        cust    = o.get("customer") or {}
        cname   = f"{cust.get('firstName','')} {cust.get('lastName','')}".strip() or cust.get("email","sin cliente")
        items   = o.get("lineItems", {}).get("nodes", [])
        total   = o.get("totalPrice","0")
        created = (o.get("createdAt","") or "")[:10]

        print(f"  {o['name']}  [{o['status']}]  ${total}  {created}")
        print(f"    Cliente : {cname}")
        print(f"    Items   : {len(items)}")
        for item in items[:3]:
            print(f"             {item['quantity']}x {item['title']}  ${item['originalUnitPrice']}")
        print(f"    ID      : {o['id']}")
        print()


# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCT
# ═══════════════════════════════════════════════════════════════════════════════

Q_PRODUCT_LIST = """
query ProductList($first: Int!, $query: String) {
  products(first: $first, query: $query, sortKey: TITLE) {
    nodes {
      id title status totalInventory
      priceRangeV2 {
        minVariantPrice { amount currencyCode }
        maxVariantPrice { amount currencyCode }
      }
      tags
    }
    pageInfo { hasNextPage }
  }
}
"""


def cmd_product_list(args):
    store = get_store(args.store)
    data  = gql(store, Q_PRODUCT_LIST, {"first": args.limit or 30, "query": args.query or ""})
    nodes = data.get("products", {}).get("nodes", [])

    if not nodes:
        print("\n  No se encontraron productos.")
        return

    if args.json:
        out_json(nodes); return

    q_str = f" (filtro: '{args.query}')" if args.query else ""
    hr(f"Productos{q_str}  —  {len(nodes)} encontrados")
    for p in nodes:
        pr    = p.get("priceRangeV2") or {}
        minp  = (pr.get("minVariantPrice") or {}).get("amount","?")
        maxp  = (pr.get("maxVariantPrice") or {}).get("amount","?")
        price = f"${minp}" if minp == maxp else f"${minp}–${maxp}"
        tags  = ", ".join(p.get("tags",[])[:4]) or "—"
        stock = p.get("totalInventory","?")

        print(f"  {p['title']}  [{p['status']}]")
        print(f"    Precio : {price}    Stock: {stock}")
        print(f"    Tags   : {tags}")
        print(f"    ID     : {p['id']}")
        print()


# ═══════════════════════════════════════════════════════════════════════════════
# VARIANT — variantes con SKU, stock e información necesaria para sync externos
# ═══════════════════════════════════════════════════════════════════════════════

# Filtra a productos ACTIVE por defecto (los DRAFT/ARCHIVED rara vez interesan
# para sync con Amazon). Variants se devuelven aplanadas con el producto padre.
Q_VARIANT_LIST = """
query VariantList($first: Int!, $query: String, $variantsPer: Int!) {
  products(first: $first, query: $query, sortKey: TITLE) {
    nodes {
      id title status handle totalInventory
      variants(first: $variantsPer) {
        nodes {
          id sku title displayName price inventoryQuantity
          barcode
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def cmd_variant_list(args):
    store = get_store(args.store)

    # Por defecto filtramos status:active para no contaminar el output con drafts.
    q = args.query or ""
    if args.status:
        q_status = f"status:{args.status.lower()}"
        q = f"({q}) AND {q_status}" if q else q_status

    data  = gql(store, Q_VARIANT_LIST, {
        "first":       args.limit or 250,
        "query":       q,
        "variantsPer": 50,
    })
    products = data.get("products", {}).get("nodes", [])

    # Aplanar variantes
    rows = []
    for p in products:
        for v in (p.get("variants", {}).get("nodes") or []):
            rows.append({
                "sku":               v.get("sku") or "",
                "title":             v.get("title") or "",
                "displayName":       v.get("displayName") or "",
                "price":             v.get("price"),
                "inventoryQuantity": v.get("inventoryQuantity"),
                "barcode":           v.get("barcode") or "",
                "variantId":         v.get("id"),
                "productId":         p.get("id"),
                "productTitle":      p.get("title"),
                "productStatus":     p.get("status"),
                "productHandle":     p.get("handle"),
            })

    if args.json:
        out_json(rows); return

    n_with_sku = sum(1 for r in rows if r["sku"])

    filter_str = f" (filtro: '{args.query}')" if args.query else ""
    hr(f"Variantes {args.status or 'todas'}{filter_str}  —  "
       f"{len(rows)} total ({n_with_sku} con SKU)")

    if not rows:
        print("  No se encontraron variantes.")
        return

    print(f"  {'SKU':<24} {'Stock':>6}  {'Precio':>9}  Nombre")
    print(f"  {'─'*24} {'─'*6}  {'─'*9}  {'─'*40}")
    for r in rows:
        sku   = (r["sku"] or "—")[:24]
        qty   = r["inventoryQuantity"]
        qty_s = f"{qty:>6}" if qty is not None else "     —"
        price = r["price"] or "—"
        name  = (r["displayName"] or r["productTitle"] or "")[:40]
        print(f"  {sku:<24} {qty_s}  ${price:>8}  {name}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# SHOP INFO (diagnóstico / verificación de conexión)
# ═══════════════════════════════════════════════════════════════════════════════

Q_SHOP_INFO = """
query ShopInfo {
  shop {
    name myshopifyDomain plan { displayName }
    currencyCode
    primaryDomain { url }
  }
}
"""


def cmd_shop_info(args):
    store = get_store(args.store)
    data  = gql(store, Q_SHOP_INFO)
    shop  = data.get("shop", {})

    if args.json:
        out_json(shop); return

    hr(f"Tienda conectada: '{store['_name']}'")
    print(f"  Nombre  : {shop.get('name','?')}")
    print(f"  Dominio : {shop.get('myshopifyDomain','?')}")
    print(f"  URL     : {(shop.get('primaryDomain') or {}).get('url','?')}")
    print(f"  Plan    : {(shop.get('plan') or {}).get('displayName','?')}")
    print(f"  Moneda  : {shop.get('currencyCode','?')}")
    print()
    print("  ✓ Conexión OK")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN / ARGPARSE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(
        prog="shopify-admin",
        description="CLI directo Shopify Admin GraphQL API · Adspubli",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  shopify-admin config add --store piro --domain piroaccessories.myshopify.com --token shpat_xxx
  shopify-admin shop
  shopify-admin company list
  shopify-admin company create --name "Boutique NY" --email buyer@boutiqueny.com
  shopify-admin pricelist create --name "Wholesale -40%" --discount 40
  shopify-admin catalog list
  shopify-admin market list
  shopify-admin draft-order list
  shopify-admin product list --query "tag:wholesale"
        """,
    )
    p.add_argument("--store", "-s", metavar="NAME", help="Store a usar (nombre configurado)")
    p.add_argument("--json",  "-j", action="store_true", help="Output en JSON puro")

    sub = p.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # ── config ──────────────────────────────────────────────────────────────────
    cfg = sub.add_parser("config", help="Gestionar stores y tokens")
    cfg_sub = cfg.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")

    cfg_add = cfg_sub.add_parser("add", help="Añadir store")
    cfg_add.add_argument("--store",  required=True, metavar="NAME")
    cfg_add.add_argument("--domain", required=True, metavar="DOMAIN.myshopify.com")
    cfg_add.add_argument("--token",  required=True, metavar="shpat_xxx")

    cfg_def = cfg_sub.add_parser("default", help="Cambiar store por defecto")
    cfg_def.add_argument("--store", required=True, metavar="NAME")

    cfg_sub.add_parser("list",  help="Listar stores configurados")
    cfg_sub.add_parser("show",  help="Ver config completa (tokens enmascarados)")

    # ── shop ─────────────────────────────────────────────────────────────────────
    sub.add_parser("shop", help="Info de la tienda y verificar conexión")

    # ── company ──────────────────────────────────────────────────────────────────
    cmp = sub.add_parser("company", help="Gestionar empresas B2B")
    cmp_sub = cmp.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")

    cmp_ls = cmp_sub.add_parser("list", help="Listar empresas")
    cmp_ls.add_argument("--limit", type=int, default=50)

    cmp_get = cmp_sub.add_parser("get", help="Ver empresa por ID")
    cmp_get.add_argument("--id", required=True, metavar="GID")

    cmp_cr = cmp_sub.add_parser("create", help="Crear empresa B2B")
    cmp_cr.add_argument("--name",         required=True, help="Nombre de la empresa")
    cmp_cr.add_argument("--email",        metavar="EMAIL",  help="Email del contacto principal")
    cmp_cr.add_argument("--contact-name", metavar="NOMBRE", help="Nombre completo del contacto")
    cmp_cr.add_argument("--location",     metavar="NOMBRE", help="Nombre de la sucursal (default: Principal)")
    cmp_cr.add_argument("--country",      metavar="CC", default="US", help="Codigo de pais ISO (default: US)")
    cmp_cr.add_argument("--address",      metavar="ADDR", default="TBD", help="Direccion (default: TBD)")

    # ── catalog ───────────────────────────────────────────────────────────────────
    cat = sub.add_parser("catalog", help="Ver catálogos B2B")
    cat_sub = cat.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")
    cat_sub.add_parser("list", help="Listar catálogos activos")

    # ── pricelist ─────────────────────────────────────────────────────────────────
    pl = sub.add_parser("pricelist", help="Gestionar price lists")
    pl_sub = pl.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")
    pl_sub.add_parser("list", help="Listar price lists")

    pl_cr = pl_sub.add_parser("create", help="Crear price list")
    pl_cr.add_argument("--name",     required=True)
    pl_cr.add_argument("--discount", type=float, metavar="N", help="Porcentaje descuento (ej: 40 = menos 40 pct)")
    pl_cr.add_argument("--increase", type=float, metavar="N", help="Porcentaje aumento (ej: 10 = mas 10 pct)")
    pl_cr.add_argument("--currency", default="USD", metavar="USD|EUR|...")

    # ── market ────────────────────────────────────────────────────────────────────
    mkt = sub.add_parser("market", help="Ver mercados Shopify")
    mkt_sub = mkt.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")
    mkt_sub.add_parser("list", help="Listar mercados")

    # ── draft-order ───────────────────────────────────────────────────────────────
    do = sub.add_parser("draft-order", help="Ver draft orders B2B")
    do_sub = do.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")
    do_ls = do_sub.add_parser("list", help="Listar draft orders recientes")
    do_ls.add_argument("--limit", type=int, default=20)

    # ── product ───────────────────────────────────────────────────────────────────
    prod = sub.add_parser("product", help="Ver productos")
    prod_sub = prod.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")
    prod_ls = prod_sub.add_parser("list", help="Listar productos")
    prod_ls.add_argument("--query", "-q", metavar="QUERY",
                         help="Filtro Shopify (ej: 'tag:wholesale' o 'title:collar')")
    prod_ls.add_argument("--limit", type=int, default=30)

    # ── variant ──────────────────────────────────────────────────────────────────
    var = sub.add_parser("variant", help="Ver variantes (SKU + stock + precio)")
    var_sub = var.add_subparsers(dest="subcommand", required=True, metavar="SUBCOMMAND")
    var_ls = var_sub.add_parser("list", help="Listar variantes aplanadas con SKU/stock")
    var_ls.add_argument("--query", "-q", metavar="QUERY",
                        help="Filtro Shopify a productos (ej: 'tag:wholesale')")
    var_ls.add_argument("--status", metavar="STATUS", default="ACTIVE",
                        choices=["ACTIVE", "DRAFT", "ARCHIVED", ""],
                        help="Filtrar por status del producto padre (default ACTIVE, '' = todos)")
    var_ls.add_argument("--limit", type=int, default=250,
                        help="Maximo de productos a recuperar (default 250)")

    # ─────────────────────────────────────────────────────────────────────────────
    args = p.parse_args()
    cmd  = args.command
    sub_ = getattr(args, "subcommand", None)

    dispatch = {
        ("config",       "add"):     cmd_config_add,
        ("config",       "default"): cmd_config_default,
        ("config",       "list"):    cmd_config_list,
        ("config",       "show"):    cmd_config_show,
        ("shop",         None):      cmd_shop_info,
        ("company",      "list"):    cmd_company_list,
        ("company",      "get"):     cmd_company_get,
        ("company",      "create"):  cmd_company_create,
        ("catalog",      "list"):    cmd_catalog_list,
        ("pricelist",    "list"):    cmd_pricelist_list,
        ("pricelist",    "create"):  cmd_pricelist_create,
        ("market",       "list"):    cmd_market_list,
        ("draft-order",  "list"):    cmd_draft_order_list,
        ("product",      "list"):    cmd_product_list,
        ("variant",      "list"):    cmd_variant_list,
    }

    fn = dispatch.get((cmd, sub_))
    if fn:
        fn(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()

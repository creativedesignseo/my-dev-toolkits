# amazon-sp — CLI directo Amazon SP-API

CLI de línea de comandos para Amazon Selling Partner API, siguiendo el mismo
patrón que `shopify-admin-cli/` y los demás CLIs de Adspubli (`gmail`, `ga4`,
`gsc`, `gtm`).

A diferencia de `shopify-admin` (stdlib puro), este CLI usa la librería
[`python-amazon-sp-api`](https://github.com/saleweaver/python-amazon-sp-api)
porque la firma AWS de SP-API + el flow de refresh LWA + paginación son
demasiado boilerplate para reimplementarlos a mano. La librería vive en un
**venv aislado en `.venv/`** (no contamina el sistema).

## Arquitectura

```
~/.local/bin/amazon-sp          ← wrapper bash (instalado por install.sh)
    └→ amazon-sp-cli/.venv/bin/python3 amazon_sp.py

~/.env.amazon                   ← credenciales LWA (gitignored, NUNCA en repo)
  o fallback:
~/Documents/Workspace/Clients/pirojewelry.com/.env.amazon
```

## Instalación

```bash
cd ~/Documents/Workspace/mcp-toolkits/repo/amazon-sp-cli
bash install.sh
```

Esto:
1. Crea `./.venv/` con `python-amazon-sp-api` instalada
2. Escribe `~/.local/bin/amazon-sp` apuntando al script

## Credenciales

Crear `~/.env.amazon` (o el equivalente en pirojewelry.com) con:

```
AMAZON_LWA_CLIENT_ID=amzn1.application-oa2-client.xxxxx
AMAZON_LWA_CLIENT_SECRET=xxxxxxxxxxxx
AMAZON_REFRESH_TOKEN=Atzr|IwEBIxxxxxxxx
AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER
```

El refresh token se obtiene haciendo **self-authorize** en Seller Central →
Developer Console → tu app → "Authorize". Es perpetuo (no caduca salvo
revocación manual).

Marketplace IDs comunes:
- `ATVPDKIKX0DER` — Amazon.com (US)
- `A2EUQ1WTGCTBG2` — Amazon.ca (CA)
- `A1AM78C64UM0Y8` — Amazon.com.mx (MX)
- `A1PA6795UKMFR9` — Amazon.de (DE)
- `A1RKKUPIHCS9HS` — Amazon.es (ES)

## Comandos

| Comando | Para qué | API SP-API |
|---|---|---|
| `amazon-sp shop` | Info cuenta seller + marketplaces activos (verifica conexión) | `Sellers.get_marketplace_participation` |
| `amazon-sp inventory` | Stock FBA actual del marketplace base | `Inventories.get_inventory_summary_marketplace` |
| `amazon-sp listings` | TODOS los listings (Active+Inactive+Incomplete), via Reports async | `Reports` + `GET_MERCHANT_LISTINGS_ALL_DATA` |
| `amazon-sp orders --since N` | Pedidos últimos N días (sin PII por defecto) | `Orders.get_orders` |
| `amazon-sp orders --details` | Idem + buyer info via RDT (PII, opt-in) | `Tokens.create_restricted_data_token` |
| `amazon-sp pricing ASIN` | Tu precio + competencia + Buy Box winner | `Products.get_item_offers` |
| `amazon-sp catalog search "query"` | Top 10 catálogo Amazon global por keyword | `CatalogItems v2022-04-01.search_catalog_items` |
| `amazon-sp catalog get ASIN` | Detalle completo de un ASIN (brand, BSR, image, attrs) | `CatalogItems v2022-04-01.get_catalog_item` |
| `amazon-sp fees ASIN --price N` | Estimación referral + FBA fees (con breakdown FinalFee vs advertised) | `ProductFees.get_product_fees_estimate_for_asin` |
| `amazon-sp reports list` | Reports recientes (filtrado por tipos comunes) | `Reports.get_reports` |
| `amazon-sp feeds list` | Feeds recientes (default `JSON_LISTINGS_FEED`) | `Feeds.get_feeds` |
| `amazon-sp feeds submit FILE --type X --confirm` | **DESTRUCTIVO**. Bulk feed. Sin `--confirm` = dry-run. | `Feeds.submit_feed` |
| `amazon-sp config show` | Credenciales cargadas (enmascaradas) | — |

Flags globales:
- `--json` (`-j`) → output JSON crudo para piping (`jq`, scripts, etc.)
- `--marketplace US|CA|MX` (`-m`) → override del marketplace base. Por defecto usa `AMAZON_MARKETPLACE_ID` del `.env`.

### Ejemplos de output real

> Producción — Dream Beauty Jewelry LLC, validado 23 mayo 2026.

**`amazon-sp shop`** — los 3 marketplaces consumer-facing + 3 stores internos MCF:

```
  Cuenta seller — 6 marketplace(s) activos
  Credenciales      : /Users/aimac/.env.amazon
  Marketplace base  : US  (ATVPDKIKX0DER)

  Amazon.com (US)  —  ✓ vendiendo
    Marketplace ID : ATVPDKIKX0DER     Moneda: USD     Dominio: www.amazon.com
  Amazon.ca (CA)  —  ✓ vendiendo
  Amazon.com.mx (MX)  —  ✓ vendiendo
  ...

  ✓ Conexion OK
```

> Los 3 stores internos (`sim1/siprod/sidevo`) son endpoints internos de
> Multi-Channel Fulfillment y aparecen por defecto en cualquier seller account.
> Se ignoran para research y operativa de listings.

**`amazon-sp inventory`** — 20 SKUs, 1 con stock real:

```
  Inventario FBA — US — 20 SKU(s) totales
  Vendible total : 5 unidades
  SKUs con stock : 1

  SKU                    ASIN         Cond    Sellable  Nombre
  DBJ-HRT-GLD-WHT-001    B0GTNLGYB8   NewIt…         5  14K Gold Filled Heart Chain Bracelet…
  12-8P7H-1HZ9           B0GYGKGMVY   NewIt…         0  Women's Two-Tone X Accent Bangle Bra…
  ...
```

**`amazon-sp listings`** — Reports async, ~30s de polling:

```
  → Solicitando report GET_MERCHANT_LISTINGS_ALL_DATA...
  → reportId: 110885020596
  → status: IN_PROGRESS
  → status: DONE
  → Descargando documento...

  Listings — US — 17 total
  Inactive       : 12
  Incomplete     : 4
  Active         : 1
  Por canal:
    AMAZON_NA      : 16
    DEFAULT        : 1
```

**`amazon-sp orders --since 30daysAgo`**:

```
  Pedidos — ultimos 30 dias — US — 2 encontrados
  OrderID                Fecha      Status                  Total  Items  Canal
  111-8467663-9401013    2026-04-23 Shipped             32.09 USD      1  AFN
  114-2255413-9677036    2026-05-05 Shipped             31.94 USD      1  AFN
```

`AFN` = Amazon Fulfillment Network (FBA). `MFN` sería seller-fulfilled.

**`amazon-sp pricing B0GTNLGYB8`**:

```
  Pricing — ASIN B0GTNLGYB8 — US
  Producto         : https://www.amazon.com/dp/B0GTNLGYB8
  Ofertas totales  : 1
  Buy Box price    : 29.99 USD  (condition=New)
  Lowest price     : 29.99 USD + 0.0 ship

  Top 1 ofertas:
  #      Price   +Ship  Cond   FBA  BBox   Feedback
  1  29.99 USD     0.0  new    yes  ✓             1
```

**`amazon-sp catalog search "silver heart bracelet"`**:

```
  Catalogo Amazon — 'silver heart bracelet' — US — 10 resultados
   1. [B0C9M1TND3]  brand: PANDORA
      PANDORA Heart Clasp Snake Chain Bracelet…
      https://www.amazon.com/dp/B0C9M1TND3
   2. [B01N360YYH]  brand: Amberta
      Amberta Women's 925 Sterling Silver Heart Bracelet…
   ...
```

**`amazon-sp catalog get B0GTNLGYB8`** — detalle completo del ítem:

```
  Catalog item — B0GTNLGYB8 — US
  Brand          : Dream Beauty Jewelry
  Title          : 14K Gold Filled Heart Chain Bracelet for Women…
  Manufacturer   : Dream Beauty Jewelry
  Color          : Gold
  Product type   : BRACELET

  Sales Ranks:
    #4562     in Women's Link Charm Bracelets
    #3394174  in Clothing, Shoes & Jewelry

  Imagen principal : https://m.media-amazon.com/images/I/51KQ3RBMAiL.jpg
```

**`amazon-sp fees B0GTNLGYB8 --price 29.99`** — total fees + breakdown FinalFee vs advertised:

```
  Fees estimate — ASIN B0GTNLGYB8 — US
  Precio asumido : 29.99 USD     Fulfillment: FBA
  Total fees     : 6.52 USD

  Breakdown (FinalFee = lo realmente cobrado):
    ReferralFee                       6.0 USD
    FBAFees                           0.52 USD  (advertised: 3.86)
      └ FBAPickAndPack                0.52 USD

  Neto despues de fees : 23.47 USD  (78.3% del revenue, sin contar COGS)
```

> En el momento del test el `FBAFees.FinalFee` ($0.52) es mucho menor que el `FeeAmount`
> advertised ($3.86) — Amazon estaba en una promo que dejaba solo el FBA Pick & Pack.
> El CLI muestra ambos para que sepas si un cambio en la promo te haría subir los fees.

**`amazon-sp reports list`** — históricos del seller, filtrados por tipos comunes:

```
  Reports — US — filtro: 6 tipos comunes — 20 encontrados
  reportId       Tipo                                       Status   Creado
  110885020596   GET_MERCHANT_LISTINGS_ALL_DATA             DONE     2026-05-23T12:16:05
  110881020596   GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA    DONE     2026-05-23T09:44:47
  ...
```

**`amazon-sp feeds submit FILE --type X`** — dry-run por defecto, requiere `--confirm`:

```
  feeds submit — DRY RUN  (sin --confirm)
  Archivo       : /tmp/test.json
  Tamano        : 9 bytes
  Feed type     : JSON_LISTINGS_FEED

  Para realmente submittear este feed:
    amazon-sp feeds submit /tmp/test.json --type JSON_LISTINGS_FEED --confirm

  ATENCION: este comando MODIFICA tu cuenta Amazon …
```

## Próximos comandos planificados

- `amazon-sp inventory sync --from shopify` — sync Shopify ↔ FBA stock
- `amazon-sp pricing autorepricer --rules pricing.yaml` — reglas de repricing
- `amazon-sp reports request <type>` / `get <id>` — descarga ad-hoc de reports
- `amazon-sp orders cancel` (gated por `--confirm`) — cancelación de pedidos
- AWS SQS + Notifications API — webhooks en tiempo real cuando volumen > 10/día

## Troubleshooting

**`python-amazon-sp-api no esta instalada`**
→ Ejecutar `bash install.sh` para crear el venv.

**`No se encontro .env.amazon`**
→ Crear el archivo en `~/.env.amazon` con las 4 variables requeridas. Ver
sección "Credenciales".

**`SellingApiException: Access to requested resource is denied`**
→ La app no está self-authorized para esa cuenta, o los scopes/roles que
solicitaste en SPP no están aprobados. Verificar en
[Developer Console](https://sellercentral.amazon.com/developer/applications).

**`InvalidGrant: The request is missing a required parameter` (refresh token)**
→ El refresh token está mal copiado (suele empezar por `Atzr|IwEBI...`).
Regenerar haciendo self-authorize de nuevo.

---
name: shopify-admin
description: |
  Use this skill for ANY task involving Shopify store data via Admin GraphQL API:
  products, customers, orders, draft orders, companies (B2B), catalogs, price lists,
  markets, and publications. Uses the `shopify-admin` CLI — direct HTTP to Shopify's
  official Admin API, zero dependencies, no server process, never crashes.
  Triggers when the user wants to query or mutate Shopify store data
  programmatically without touching the theme (use `shopify` CLI for themes).
---

# shopify-admin CLI — Adspubli Toolkit

## Qué es y por qué NO es un MCP

`shopify-admin` es una **herramienta de acceso directo a la Admin GraphQL API oficial
de Shopify**. No es un MCP, no es un servidor, no tiene protocolo intermedio.

```
shopify-admin product list
        ↓
  python3 shopify_admin.py   (proceso puntual, vive 200ms y muere)
        ↓
  POST /admin/api/2025-04/graphql.json   ← llamada HTTP directa
  Header: X-Shopify-Access-Token: shpca_...
        ↓
  Admin GraphQL API de Shopify   ← la misma API que usa el propio admin.shopify.com
```

### CLI directo vs MCP — diferencia arquitectónica

| | MCP server | `shopify-admin` CLI |
|---|---|---|
| **Proceso** | Servidor persistente (Node/Python corriendo siempre) | Proceso puntual — arranca, ejecuta, termina |
| **Protocolo** | JSON-RPC sobre stdio/SSE — capa extra de traducción | HTTP directo al API — sin intermediario |
| **Fallos** | Se cuelga, pierde conexión, hay que reiniciarlo | No hay servidor que falle — o funciona o da error claro |
| **Auth** | El MCP gestiona su propio auth (fuente de bugs) | Token en `~/.shopify-admin/config.json` — simple y transparente |
| **Debug** | Opaco — no ves qué GraphQL envía realmente | `--json` muestra la respuesta cruda del API |
| **Composable** | Solo funciona como tool de Claude | Pipe a `jq`, bash scripts, cron, CI/CD |
| **Portabilidad** | Necesita configuración por proyecto en MCP settings | Un binario en `~/.local/bin/` — funciona en cualquier terminal |
| **Dependencias** | Node.js runtime + npm packages | Python stdlib puro — `urllib`, `json`, `argparse` |

### Comparación de potencia real

```bash
# Con MCP: dependes de que el server esté corriendo, que Claude lo invoque bien,
# que el protocolo no falle, que el schema del MCP cubra lo que necesitas.

# Con shopify-admin: control total, sin intermediarios
shopify-admin product list --query "tag:wholesale" --json | jq '.[] | .id'
shopify-admin draft-order list --json | jq '[.[] | select(.status=="OPEN")]'
shopify-admin pricelist create --name "B2B -40%" --discount 40
```

---

## Los dos CLIs de Shopify — mapa completo

| CLI | Para qué | Autenticación | Alcance |
|-----|----------|---------------|---------|
| **`shopify`** (CLI oficial Shopify) | Temas: `theme push/pull/dev`, scaffold de apps | Partners OAuth (tu cuenta) | Global — cualquier tienda colaboradora |
| **`shopify-admin`** (cliente directo Admin API) | Datos: productos, pedidos, B2B, catálogos, markets | Token `shpca_` por tienda | Por tienda — cada store tiene su token |

El `shopify` CLI oficial **no hace queries de datos** (solo opera archivos de tema).
El `shopify-admin` **no toca el tema** (solo datos vía API).

Shopify no provee un CLI de datos oficial — provee el API REST/GraphQL y cada integración
decide cómo accederlo. `shopify-admin` es ese cliente, construido sobre el estándar oficial.

---

## Arquitectura del CLI

```
~/.local/bin/shopify-admin          ← wrapper bash (instalado por install.sh)
    └→ ~/Documents/Workspace/mcp-toolkits/repo/shopify-admin-cli/shopify_admin.py

~/.shopify-admin/config.json        ← tokens por tienda (chmod 600, fuera de git)
```

**App en Partners:** "Adspubli CLI"
- Org ID: `130399301`
- App ID: `362282516481`
- Client ID: `15c6efc234029ee959a53a3bafc5621c`
- Client Secret: stored in `~/.shopify-admin/app.json` (never commit — get from Dev Dashboard → Settings)
- Dev Dashboard: https://dev.shopify.com/dashboard/130399301/apps/362282516481
- Partners (distribución): https://partners.shopify.com/3062121/apps/362282516481/distribution
- Versión activa: `adspubli-cli-4` — incluye `redirect_uri = http://localhost:3000/callback`
- API version: `2025-04`

**Formato del token:** `shpca_` (OAuth custom app token, no caduca salvo revocación)

**Scopes configurados:**
```
read_customers, write_customers,
read_price_rules, write_price_rules,
write_draft_orders, read_draft_orders,
read_markets,
read_orders, write_orders,
read_products, write_products,
read_publications, write_publications
```

> **Scopes NO incluidos (requieren store owner):**
> `read_companies`, `write_companies` — para B2B Companies, hay que pedirle a Ana
> (pirojewelry@gmail.com) que instale la app ella misma o que otorgue permiso staff.

---

## Tiendas configuradas

| Alias | Dominio | Token |
|-------|---------|-------|
| `piro` (default) | piroaccessories.myshopify.com | `shpca_c229b859...` |

Ver/añadir: `shopify-admin config list`

---

## Comandos de uso diario

```bash
# Info de la tienda
shopify-admin shop [--store piro]

# Productos
shopify-admin product list [--limit 20] [--query "tag:wholesale"]

# Mercados
shopify-admin market list

# Catálogos B2B
shopify-admin catalog list

# Price lists
shopify-admin pricelist list
shopify-admin pricelist create --name "Wholesale -40%" --discount 40

# Empresas B2B (requiere write_companies)
shopify-admin company list
shopify-admin company create --name "Acme Corp" --email buyer@acme.com

# Draft orders
shopify-admin draft-order list [--limit 20]

# Config
shopify-admin config list
shopify-admin config show [--store piro]
shopify-admin config default --store X
```

Todos los comandos aceptan `--json` para salida en JSON crudo.

---

## FAST PATH — conectar una tienda nueva (~10 min)

Esto es lo que hay que hacer cada vez que se quiera añadir una tienda nueva
al `shopify-admin` CLI. La app "Adspubli CLI" ya está creada — solo hay que
instalarla en la nueva tienda y obtener el token.

### Prerrequisitos (ya hechos, no repetir)
- [x] App "Adspubli CLI" creada en Partners Dev Dashboard
- [x] Redirect URI `http://localhost:3000/callback` registrado en versión activa
- [x] Script OAuth en `shopify-admin-cli/oauth_token.py`

### Pasos por tienda nueva

**Paso 1 — Generar enlace de instalación**
1. Ir a https://partners.shopify.com/3062121/apps/362282516481/distribution
2. En "Distribución personalizada" → escribir el dominio nuevo (ej: `nuevatienda.myshopify.com`)
3. Click "Generar enlace" → confirmar en el modal
4. Copiar el enlace generado

**Paso 2 — Instalar la app en la tienda**
1. Abrir el enlace → seleccionar la tienda en el picker de Shopify
2. Click "Instalar" en la pantalla de permisos

**Paso 3 — Obtener el token (OAuth local)**
```bash
# En una terminal, lanza el servidor OAuth:
python3 ~/Documents/Workspace/mcp-toolkits/repo/shopify-admin-cli/oauth_token.py \
  --shop nuevatienda.myshopify.com

# El script imprime una URL. Ábrela en el browser donde estés autenticado
# como staff/owner de la tienda. Shopify redirige a localhost:3000 y el
# script imprime el token shpca_xxx y lo guarda en /tmp/shopify_token.json
```

**Paso 4 — Registrar en el CLI**
```bash
shopify-admin config add \
  --store ALIAS \
  --domain nuevatienda.myshopify.com \
  --token shpca_XXXXXX
```

**Paso 5 — Verificar**
```bash
shopify-admin shop --store ALIAS
# → debe mostrar nombre, plan, moneda
```

---

## Proceso completo de creación de app (referencia histórica)

> Solo necesario si la app "Adspubli CLI" se pierde o hay que recrearla desde cero.
> En condiciones normales NO hay que repetir esto.

### 1. Crear la app en Dev Dashboard
- URL: https://dev.shopify.com/dashboard/{ORG_ID}/apps/new
- Tipo: Custom app (no public)
- Nombre: "Adspubli CLI"

### 2. Crear primera versión con los scopes
En Dev Dashboard → Versiones → Nueva versión:
```toml
name = "Adspubli CLI"
[access_scopes]
scopes = "read_customers,write_customers,read_price_rules,write_price_rules,write_draft_orders,read_draft_orders,read_markets,read_orders,write_orders,read_products,write_products,read_publications,write_publications"
redirect_urls = ["http://localhost:3000/callback"]
[app_url]
url = "https://example.com"
```
- Publicar la versión

### 3. Configurar distribución personalizada
- Partners Dashboard → App → Distribución
- Seleccionar "Distribución personalizada"
- Confirmar (acción irreversible)
- Generar enlace para la primera tienda

### 4. Instalar y obtener token (ver Fast Path paso 2–5)

### Notas importantes
- **Scopes de companies** (`read_companies`, `write_companies`): los bloqueó Shopify
  para colaboradores. Solo el store owner puede instalar la app si se incluyen estos scopes.
  Para la fase B2B de Piro, cuando Ana (pirojewelry@gmail.com) esté disponible:
  1. Crear nueva versión añadiendo `read_companies,write_companies` a los scopes
  2. Pedirle a Ana que genere una nueva instalación desde el enlace
  3. Hacer el OAuth flow de nuevo para obtener token con estos scopes adicionales
- **Token `shpca_` vs `shpat_`**: `shpca_` es OAuth (nuestra app), `shpat_` es
  legacy private app. Ambos funcionan con `X-Shopify-Access-Token: {token}`.
- **Plan Basic limits**: máximo 3 MarketCatalogs activos para B2B.
- El CLI usa `urllib` puro (stdlib) — no requiere venv ni pip.

---

## Estado B2B Piro Jewelry (13 mayo 2026)

| Item | Estado |
|------|--------|
| Shopify Markets | ✅ Activo (International + United States) |
| MarketCatalogs B2B | 2/3 usados — queda 1 slot |
| Price lists | 2 (sin descuento real aún) |
| Companies B2B formales | ❌ 0 — pendiente scopes con Ana |
| Actividad wholesale real | ✅ 20+ draft orders a clientes recurrentes |
| Token CLI activo | ✅ `shpca_c229b859...` |

**Clientes B2B existentes identificados** (por draft orders):
- Yelitza Sanchez — ~$280–305/pedido
- Alejandra La Tejana — ~$300–354/pedido
- Liseth Romero — ~$374/pedido
- Soraya Covarrubia — ~$151–272/pedido
- Abigail Canales — ~$106–400/pedido
- JANET ESTRELLA — ~$98–190/pedido

---

## Troubleshooting

**`Field 'catalog' doesn't exist on type 'Market'`**
→ Ese campo no existe en la API 2025-04. Ya corregido en `adspubli-cli-4` (eliminado del query).

**`GraphQL error: Access denied for ...`**
→ El scope requerido no está en el token. Ver scopes actuales:
```bash
curl -s -X POST https://piroaccessories.myshopify.com/admin/api/2025-04/graphql.json \
  -H "X-Shopify-Access-Token: $(shopify-admin config show --store piro | grep token)" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ shop { name } }"}' | python3 -m json.tool
```

**`ValueError: badly formed help string` en Python 3.14**
→ Causado por `%%` en strings de argparse. Usar texto plano sin `%`.

**Token expirado / revocado**
→ Repetir el Fast Path paso 3–4 para regenerar. La app en Partners no hay que tocarla.

**Puerto 3000 ocupado**
```bash
kill $(lsof -ti:3000) 2>/dev/null
```

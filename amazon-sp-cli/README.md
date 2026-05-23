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

```bash
amazon-sp shop                   # info de la cuenta seller — verifica conexion
amazon-sp config show            # ver credenciales cargadas (enmascaradas)
amazon-sp shop --json            # output JSON crudo para piping
```

`amazon-sp shop` llama a `Sellers.get_marketplace_participation()`, que es el
endpoint canónico para confirmar que las credenciales son válidas y ver en qué
marketplaces participa el seller.

### Ejemplo de output real

Primer call exitoso en producción — Dream Beauty Jewelry LLC, 23 mayo 2026:

```
  Cuenta seller — 6 marketplace(s) activos
  ────────────────────────────────────────────────────────────
  Credenciales      : /Users/aimac/.env.amazon
  Marketplace base  : US  (ATVPDKIKX0DER)

  Amazon.com (US)  —  ✓ vendiendo
    Marketplace ID : ATVPDKIKX0DER
    Moneda         : USD     Idioma: en_US
    Dominio        : www.amazon.com

  Amazon.ca (CA)  —  ✓ vendiendo
    Marketplace ID : A2EUQ1WTGCTBG2
    ...

  Amazon.com.mx (MX)  —  ✓ vendiendo
    Marketplace ID : A1AM78C64UM0Y8
    ...

  ✓ Conexion OK
```

> **Nota sobre los 6 marketplaces:** la API devuelve 3 marketplaces públicos
> (US, CA, MX) **más 3 stores internos** de Amazon (sim1/siprod/sidevo) que
> corresponden al **Multi-Channel Fulfillment** y aparecen por defecto en
> cualquier cuenta seller. Se pueden ignorar para research y operativa de
> listings — solo importan los marketplaces consumer-facing.

## Estado actual

Este CLI está en **fase 1 (bootstrap)**. Solo el comando `shop` está
implementado para validar end-to-end que el self-authorize + refresh token
funcionan. Próximos comandos planificados (ver
`Clients/pirojewelry.com/09_AMAZON/07_implementation-plan.md`):

- `amazon-sp catalog search <keywords>`
- `amazon-sp catalog get <ASIN>`
- `amazon-sp listings list / get`
- `amazon-sp inventory levels`
- `amazon-sp orders --since 7daysAgo`
- `amazon-sp reports request / list / get`

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

# 📋 Historial de cambios (Changelog)

Todos los cambios notables de este repositorio se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto se adhiere a [Versionado Semántico](https://semver.org/lang/es/).

> **Cómo leer este archivo**:
> - 🟢 **Añadido** = cosas nuevas
> - 🔄 **Cambiado** = mejoras o reorganizaciones
> - 🛠️ **Arreglado** = bugs corregidos
> - ⚰️ **Deprecado** = funciones que dejan de usarse pero se conservan
> - ❌ **Eliminado** = funciones borradas
> - 🔐 **Seguridad** = parches de seguridad

---

## [Sin publicar]

### Planeado
- `ads` CLI Python dentro de `google-apis/` para Google Ads (sustituye Playwright).
- Migración progresiva de los MCP de Node.js (`google-ads-manager`, `google-analytics-manager`, `google-tag-manager`, `google-merchant-manager`) al patrón de `google-apis/`.
- Toolkit de SEO (auditorías técnicas, Lighthouse batch).
- Scripts de deployment a Netlify / Vercel.
- Más skills puras en `skills/`: posiblemente `seo-audit`, `client-onboarding`, `stripe-integration-audit`.
- Workflow GitHub Actions para validar frontmatter de skills en PR.
- Documentación de `amazon-sp-cli/` en README maestro (pendiente desde mayo).

---

## [2.2.0] — 27 de mayo de 2026

> Estreno de la sección **`skills/`** del repo: skills puras de Claude Code (sin CLI ejecutable detrás), distribuibles vía `npx skills add`. Añadida licencia MIT.

### 🟢 Añadido

- **`skills/saas-audit/`** — Skill de auditoría production-readiness para SaaS. Orquesta 13 sub-agentes en paralelo (architecture, security, payments, database, admin, UI/UX, QA, SEO/perf, deploy, stack, legal + orchestrator + reporter) y produce `AUDIT_REPORT.md` con un Production Readiness Score 0-100 ponderado por área, hallazgos P0-P3 y roadmap por fases. Soporta tres modos (`full` / `quick` / `focus`). 18 archivos (~148KB).
- **`skills/README.md`** — Documentación de la nueva sección, explica diferencia entre skills puras (en `skills/`) vs skills que acompañan a un CLI (en la carpeta del propio CLI).
- **`LICENSE`** — MIT License explícita. Permite el uso público y reutilización del contenido del repo.

### 🔄 Cambiado

- **README.md**: nueva sección "🤖 Skills — Claude Code skills" tras "Inteligencia Artificial", con tabla de skills disponibles, comandos de instalación y enlaces. Tabla de "Vista rápida" actualizada para incluir `skills/`.

### 🔗 Distribución pública

Con esta versión, las skills puras del repo pueden instalarse desde cualquier proyecto Claude Code con:

```bash
npx skills add creativedesignseo/my-dev-toolkits --skill saas-audit -g
```

Es la primera versión del repo orientada explícitamente al ecosistema [skills.sh](https://skills.sh/).

---

## [2.1.0] — 12 de mayo de 2026 (tarde)

> Ampliación del paquete `google-apis/` con dos CLIs más: GA4 y Search Console.
> El módulo de OAuth se refactoriza para soportar **scopes incrementales** (el token
> se va ampliando según se necesite, sin romper lo ya autorizado).

### 🟢 Añadido

- **`google-apis/_auth.py`** — módulo compartido de autenticación OAuth 2.0.
  - Registro centralizado de scopes (`SCOPES` dict).
  - Función `get_credentials(account, required_scopes)` que detecta scopes faltantes
    y re-lanza el OAuth flow con la UNIÓN de lo ya granted + lo nuevo.
  - Función `service(account, api, version, scopes)` para construir cualquier servicio Google.
- **`google-apis/ga4_cli.py`** — CLI para Google Analytics 4.
  - `ga4 login` — autoriza scopes `analytics.readonly`.
  - `ga4 list-accounts` — lista todas las cuentas GA accesibles.
  - `ga4 list-properties [--account-id N]` — lista propiedades GA4 (iterando cuenta por cuenta).
  - `ga4 report` — reportes históricos con métricas/dimensiones libres, rango de fechas, orden y límite.
  - `ga4 realtime` — usuarios activos en los últimos ~30 min.
  - Salida con tabla bonita por defecto, JSON con `--json`.
- **`google-apis/gsc_cli.py`** — CLI para Search Console.
  - `gsc login` — autoriza scopes `webmasters.readonly`.
  - `gsc list-sites` — todos los sitios verificados (con nivel de permiso: owner / full / restricted / unverified).
  - `gsc queries` — top palabras clave con clics, impresiones, CTR, posición.
  - `gsc pages` — top páginas con las mismas métricas.
  - `gsc positions --keywords X,Y,Z` — posición media de keywords concretas.
  - Soporte de fechas relativas (`30daysAgo`, `today`, `yesterday`).
- **`google-apis/bin/ga4`** y **`google-apis/bin/gsc`** — wrappers bash.
- Symlinks globales `~/.local/bin/ga4` y `~/.local/bin/gsc`.

### 🔄 Cambiado

- **`gmail_cli.py`** refactorizado para importar el módulo `_auth.py` compartido (sin cambios funcionales).
- README de `google-apis/` ampliado con secciones GA4 y GSC.
- `~/.claude/CLAUDE.md` y `~/.claude/skills/google-apis/SKILL.md` actualizados — la skill ahora reconoce los 3 CLIs.

### 🔐 Seguridad

- Token de `creativedesignseo@gmail.com` autorizado con scopes `analytics.readonly` + `webmasters.readonly`. El refresh es automático.
- Verificado: ningún `client_secret*.json` ni `token*.json` entra al stage.

### ✅ Validación con datos reales

- GA4 lista 39 cuentas accesibles (incluyendo cliente "vaciado de pisos elrecolector.es", property `534094689`).
- Reporte 7 días de Trayec: 107 sesiones Paid Search, 0 conversiones — confirma diagnóstico previo.
- Search Console lista 17 sitios verificados (incluyendo `sc-domain:elrecolector.es` con permiso Owner).

---

## [2.0.0] — 12 de mayo de 2026

> Lanzamiento mayor: nueva arquitectura **CLI directo** que sustituye al patrón MCP-server para Gmail, más reorganización completa de la documentación.

### 🟢 Añadido

- **`google-apis/`** — nuevo paquete Python que se conecta directamente a las APIs de Google sin pasar por un servidor MCP intermediario.
  - CLI `gmail` con subcomandos `login`, `whoami`, `draft`, `send`, `list`, `read`.
  - Soporte multi-cuenta vía mapa `accounts.json` (email → proyecto Google Cloud).
  - Soporte para alias "Send as" de Google Workspace mediante flag `--from`.
  - **Soporte de adjuntos** (los antiguos MCPs no podían enviar PDFs ni imágenes).
  - Tokens OAuth con auto-refresh — sin re-logins manuales.
  - Wrapper `bin/gmail` instalable globalmente con symlink en `~/.local/bin/gmail`.
- **`deprecated/`** — nueva carpeta donde se archivan herramientas que ya no se usan pero se conservan como referencia.
- **README maestro en castellano** — totalmente reescrito, organizado por categorías, con tabla maestra, glosario para no-técnicos y guías de inicio rápido.
- **CHANGELOG completo en castellano** — este archivo.

### 🔄 Cambiado

- `.gitignore` reforzado para cubrir `**/client_secret*.json`, `**/token*.json`, `**/credentials/tokens/`, `**/.venv/`, `**/refresh_token.json`, `**/workspace_token.json`. Defensa en profundidad: no basta con confiar en patrones genéricos.
- Reorganización visual y de categorías del README principal.

### ⚰️ Deprecado

- **`google-gmail-manager/`** — servidor MCP de Gmail escrito en Node.js. Causaba errores 403 recurrentes que requerían reconexión manual. Movido a `deprecated/google-gmail-manager/`. **Sustituido por `google-apis/` (CLI `gmail`).**
- **`gmail-mcp/`** — wrapper sobre el paquete público `@shinzolabs/gmail-mcp`. Mismos problemas de fiabilidad. Movido a `deprecated/gmail-mcp/`. **Sustituido por `google-apis/` (CLI `gmail`).**

### 🔐 Seguridad

- Auditoría completa del histórico de git: **ninguna credencial filtrada en commits previos**.
- Nuevos patrones de `.gitignore` documentados en el README (sección Seguridad).
- Documentación explícita sobre cómo verificar protección antes de commitear (`git check-ignore`).

---

## [1.1.0] — 24 de febrero de 2026

> Tanda de servidores MCP para el stack de marketing digital de Google.

### 🟢 Añadido

- **`google-merchant-manager/`** — servidor MCP para Google Merchant Center API.
  - `list_products` — listar inventario activo por Merchant ID.
  - `get_product` — detalle de producto individual.
- **`google-tag-manager/`** — servidor MCP para Google Tag Manager API v2 (46 herramientas).
  - Lectura y actualización dinámica de tags, triggers y variables.
  - Auto-vínculo de workspace activo.
  - Publicación de versiones.
- **`google-analytics-manager/`** — servidor MCP para Google Analytics 4.
  - `list_accounts`, `list_properties`.
  - Generación de reportes estándar.
  - `create_conversion_event` para registrar eventos clave programáticamente.
- **`google-ads-manager/`** — servidor MCP para Google Ads API.
  - Lectura de campañas, grupos de anuncios, palabras clave.
  - Métricas (clics, impresiones, coste, CTR).

### 🔄 Cambiado

- Estructura del README maestro para incluir los nuevos toolkits.

---

## [1.0.1] — 3 de febrero de 2026

### 🟢 Añadido

- **`shopify-admin-mcp/`** — servidor MCP en TypeScript para Shopify Admin GraphQL API.
  - `search_products` con sintaxis de búsqueda de Shopify.
  - `create_product_with_variants` para crear productos completos.
  - `update_inventory` para ajustar stock por ubicación.
- **`gemini-cli-tools/`** — directorio inicial (placeholder) para configuraciones y prompts del Gemini CLI.

### 🔄 Cambiado

- Marketing toolkits consolidados en este repositorio (antes estaban dispersos).

---

## [1.0.0] — 26 de diciembre de 2025

> 🎉 Lanzamiento inicial del repositorio.

### 🟢 Añadido

- **`image-optimizer/`** — toolkit de optimización de imágenes web.
  - Script `convert-to-webp.js` — conversión automática PNG/JPG → WebP.
  - Script `optimize-images.js` — optimización en lote con Sharp (C++).
  - Script `clean-duplicates.js` — detección y limpieza de duplicados.
  - Documentación completa (README, INSTALLATION, USAGE, EXAMPLES, FAQ).
  - Plantilla de configuración de Vite.
- Estructura inicial del repositorio: `README.md`, `CHANGELOG.md`, `.gitignore`.

### Métricas probadas (en proyecto BaLo Restaurant)

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| Tamaño total | 37 MB | 1.5 MB | **96 %** |
| Tiempo de carga (4G) | 30 s | 1.2 s | **96 %** |
| Calidad visual | 100 % | 99.9 % | Imperceptible |

---

## 📐 Guía de versionado

Este proyecto usa **[Versionado Semántico](https://semver.org/lang/es/)**: `MAYOR.MENOR.PARCHE`.

| Tipo | Cuándo se incrementa | Ejemplo |
|------|----------------------|---------|
| **MAYOR** (X.0.0) | Cambios incompatibles con versiones anteriores. Reorganizaciones grandes. | 1.x.x → 2.0.0 |
| **MENOR** (1.X.0) | Nuevas funciones que no rompen lo anterior. | 1.0.x → 1.1.0 |
| **PARCHE** (1.0.X) | Solo correcciones de bugs. | 1.0.0 → 1.0.1 |

### Convenciones de mensajes de commit

Usamos [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/):

- `feat:` — nueva funcionalidad
- `fix:` — corrección de un bug
- `docs:` — solo cambios de documentación
- `refactor:` — cambios de código sin alterar funcionalidad
- `chore:` — tareas de mantenimiento
- `deprecate:` — marcar algo como obsoleto

---

**Última actualización**: 12 de mayo de 2026

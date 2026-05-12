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
- CLIs Python siblings dentro de `google-apis/` para Google Analytics 4 (`ga4`), Search Console (`gsc`) y Google Ads (`ads`).
- Migración progresiva de los MCP de Node.js (`google-ads-manager`, `google-analytics-manager`, `google-tag-manager`, `google-merchant-manager`) al patrón de `google-apis/`.
- README pendiente dentro de `google-merchant-manager/`.
- Toolkit de SEO (auditorías técnicas, Lighthouse batch).
- Scripts de deployment a Netlify / Vercel.

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

# 🛍️ Google Merchant Center MCP Server

**Tipo**: MCP Server Node.js
**Estado**: 🟢 En producción
**Pertenece a**: [my-dev-toolkits](../README.md)

---

## 🎯 Qué hace

Servidor **MCP (Model Context Protocol)** que conecta con la **Google Content API for Shopping** — la API que gestiona los productos que aparecen en Google Shopping a través de **Merchant Center**.

Permite a una IA (Claude, Cursor, Antigravity) consultar el catálogo de productos de cualquier cuenta de Merchant Center a la que tengas acceso.

---

## 🛠️ Herramientas disponibles

| Tool | Para qué sirve |
|------|----------------|
| `list_products` | Lista el inventario activo de un Merchant ID concreto. |
| `get_product` | Obtiene el detalle completo de un producto por su ID. |

---

## 🚀 Instalación

### 1. Dependencias

```bash
cd google-merchant-manager
npm install
```

### 2. Credenciales

Necesitas un **OAuth 2.0 Client ID** desde Google Cloud Console del proyecto que tiene acceso al Merchant Center:

1. https://console.cloud.google.com/apis/credentials
2. Habilita la **Content API for Shopping**
3. Crea credenciales OAuth → tipo "Desktop"
4. Descarga `credentials.json` y guárdalo en la raíz de este toolkit

### 3. Obtener Refresh Token

```bash
npm run auth   # o: node get-refresh-token.js
```

Esto abrirá el navegador, te pedirá autorizar, y guardará un `token.json` (gitignored).

---

## 🔌 Conectar a un cliente MCP

Añade este bloque a tu `mcp_config.json` (Claude Code, Antigravity, Cursor, etc.):

```json
{
  "mcpServers": {
    "google-merchant": {
      "command": "node",
      "args": ["/RUTA/COMPLETA/A/google-merchant-manager/mcp-server.js"]
    }
  }
}
```

---

## 🔐 Seguridad

`credentials.json`, `token.json` y cualquier `*.yaml` están protegidos por el `.gitignore` del repo. Nunca subas estos archivos a un repositorio público.

---

## 🗺️ Roadmap (a futuro)

Esta herramienta se migrará a un CLI Python dentro de [`../google-apis/`](../google-apis/) siguiendo el patrón establecido — más fiable y sin depender del protocolo MCP.

Cuando ocurra, este toolkit se moverá a `../deprecated/`.

---

📁 Volver al [README principal](../README.md)

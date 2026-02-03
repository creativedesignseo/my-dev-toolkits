# 🎯 Google Ads MCP Server Core (Node.js)

Este es un servidor MCP (Model Context Protocol) robusto y optimizado para conectar **Antigravity**, **Cursor** o cualquier cliente MCP con la API de Google Ads sin las complicaciones del entorno experimental de Python.

## 🚀 Ventajas sobre la versión oficial
- **100% Node.js:** Más estable en entornos Windows/Mac sin dependencias complejas.
- **Herramientas de Alto Nivel:** No hace falta que la IA invente queries complejas, ya tiene funciones dedicadas para campañas, métricas, adgroups y keywords.
- **Gestión de OAuth integrada:** Incluye un script propio para obtener el `refresh_token` de forma visual.

## 🛠️ Instalación

1. **Clona este repositorio:**
   ```bash
   git clone https://github.com/creativedesignseo/google-ads-mcp-nodejs.git
   cd google-ads-mcp-nodejs
   ```

2. **Instala dependencias:**
   ```bash
   npm install
   ```

3. **Configura tus credenciales:**
   Crea o edita el archivo `google-ads.yaml` con tus datos:
   ```yaml
   developer_token: TU_TOKEN
   client_id: TU_CLIENT_ID
   client_secret: TU_CLIENT_SECRET
   login_customer_id: TU_ID_MCC_O_CUENTA
   ```

4. **Obtén tu Refresh Token:**
   ```bash
   npm run auth
   ```

## 🔌 Conexión con Antigravity

Añade este bloque a tu `mcp_config.json`:

```json
"google-ads": {
  "command": "node",
  "args": ["RUTA_COMPLETA_A_TU_CARPETA/mcp-server.js"]
}
```

## 🛠️ Herramientas disponibles (Tools)
- `list_campaigns`: Lista todas las campañas.
- `get_campaign_metrics`: Obtiene clicks, impresiones, coste y CTR.
- `list_ad_groups`: Explora los grupos de anuncios de una campaña.
- `list_keywords`: Analiza el rendimiento de palabras clave.
- `get_account_summary`: Resumen ejecutivo de la cuenta.

## ⚖️ Licencia
MIT

---
*Desarrollado con 🦾 por Antigravity AI para Adspubli.*

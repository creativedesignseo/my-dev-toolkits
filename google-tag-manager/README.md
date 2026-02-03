# Google Tag Manager MCP Server

🤖 **Servidor MCP para Google Tag Manager** - Control estandarizado para tus contenedores de GTM.

## 🚀 Capacidades

- **Listar Cuentas y Contenedores**: Visualiza tu estructura de GTM.
- **Auditoría de Etiquetas**: Revisa qué tags están instalados.
- **Gestión de Versiones**: (Próximamente) Publica y versiona cambios.

## 🛠️ Instalación

1.  Clonar repositorio.
2.  `npm install`
3.  Configurar credenciales (ver `get-refresh-token.js`).
4.  Ejecutar servidor: `node mcp-server.js`

## 🔒 Seguridad

Este proyecto utiliza OAuth 2.0. **NUNCA** subas tus archivos de credenciales (`credentials.json`, `*.yaml`) al repositorio.

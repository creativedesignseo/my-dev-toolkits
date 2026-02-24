# Google Tag Manager MCP Server v2.0.0

Este servidor permite a un Agente de IA (como Antigravity) administrar completamente cuentas de Google Tag Manager mediante el protocolo MCP.

## Características
- **API Completa**: Soporte total para GTM API v2.
- **46 Herramientas**: Desde lectura básica hasta publicación de versiones y gestión de permisos.
- **Auto-vínculo de Workspace**: Las herramientas de Tags, Triggers y Variables detectan automáticamente el primer workspace activo si solo se provee el `containerPath`.

## Requisitos Previos
1. **Google Cloud Project**: Tener una App registrada con la API de Tag Manager habilitada.
2. **credentials.json**: Archivo en la raíz con `client_id` y `client_secret`.
3. **Refresh Token**: Ejecutar `npm run auth` para generar el token de acceso inicial.

## Listado de Herramientas (Groups)

### 📊 Cuentas y Contenedores
- `list_accounts`: Lista todas las cuentas accesibles.
- `get_account`: Detalles de una cuenta específica.
- `create_container`: Crea un contenedor (Web, iOS, Android, AMP, Server).
- `get_container_snippet`: Genera el código GTM-XXXXX para insertar en el HTML.

### 🛠️ Configuración (Workspaces)
- `list_workspaces`: Ver espacios de trabajo actuales.
- `create_workspace`: Crear un entorno de edición separado.
- `sync_workspace`: Traer cambios de la versión publicada al workspace.

### 🏷️ Etiquetas (Tags)
- `create_tag`: Crear etiquetas (GA4, HTML Personalizado, etc.).
- `update_tag`: Modificar parámetros de etiquetas existentes.
- `list_tags`: Ver etiquetas enriquecidas con sus disparadores (triggers).

### ⚡ Disparadores (Triggers)
- `create_trigger`: Definir cuando se activan las etiquetas (clics, vistas de página, eventos personalizados).
- `list_triggers`: Ver todos los activadores definidos.

### 📦 Versiones y Publicación
- `create_version`: Congelar los cambios actuales en una versión.
- `publish_version`: **Hacer públicos los cambios** en el sitio web.
- `set_latest_version`: Rollback o actualización de la versión activa.

### 👥 Administración
- `list_user_permissions`: Ver quién tiene acceso.
- `create_user_permission`: Invitar nuevos usuarios con roles específicos.

## Cómo probar la implementación
Para verificar que el servidor está funcionando correctamente, puedes pedirle a la IA:
1. *"Lista mis cuentas de GTM."*
2. *"Dime qué contenedores tengo en la cuenta [Path]."*
3. *"Crea un Tag de configuración de GA4 en el contenedor [Path]."*

---
**Desarrollado para:** Antigravity Toolkit Project.
**Versión de API:** GTM v2 REST.

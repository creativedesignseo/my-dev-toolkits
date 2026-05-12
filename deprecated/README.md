# ⚰️ deprecated/ — herramientas archivadas

> 🚫 **No usar nada de esta carpeta en proyectos nuevos.**

Aquí guardamos herramientas que **ya no se mantienen** pero conservamos como referencia histórica — por si alguna vez necesitamos recordar cómo estaba hecho algo, o por si hay que copiar una idea concreta.

---

## 📋 Inventario

### 🪦 google-gmail-manager/

**Archivado el**: 12 de mayo de 2026
**Lenguaje**: Node.js
**Tipo**: Servidor MCP (Model Context Protocol) para Gmail

**Qué era**: un servidor MCP en Node.js que exponía Gmail a clientes como Claude Code, Antigravity y Cursor.

**Por qué se deprecó**:
- Errores `403 Permission Denied` recurrentes que obligaban a reconectar el MCP cada 1-2 días.
- No soportaba envío de adjuntos (PDFs, imágenes).
- No soportaba alias "Send as" de Google Workspace.
- Solo permitía configurar **una sola cuenta Gmail** simultáneamente.
- Arquitectura MCP añadía una capa intermedia más que rompía la fiabilidad.

**Reemplazado por**: 👉 [`../google-apis/`](../google-apis/) (CLI `gmail` en Python)

---

### 🪦 gmail-mcp/

**Archivado el**: 12 de mayo de 2026
**Lenguaje**: Node.js
**Tipo**: Wrapper sobre paquete público `@shinzolabs/gmail-mcp`

**Qué era**: un intento de usar un servidor MCP de Gmail de terceros (paquete npm público).

**Por qué se deprecó**:
- Mismos problemas de fiabilidad que `google-gmail-manager/`.
- Sin control sobre las actualizaciones del paquete upstream.
- Sin posibilidad de añadir features personalizadas sin forkear.

**Reemplazado por**: 👉 [`../google-apis/`](../google-apis/) (CLI `gmail` en Python)

---

## 🔍 ¿Por qué los conservamos?

1. **Referencia histórica**: si alguien pregunta "por qué dejasteis los MCP", podemos enseñar el código.
2. **Material de aprendizaje**: las decisiones de diseño (acertadas o no) son útiles para entender el patrón MCP en Node.js.
3. **Recuperación**: si el reemplazo (`google-apis/`) tuviera algún problema crítico, tenemos un fallback.

---

## ⚠️ Reglas para esta carpeta

- ❌ **No instalar dependencias** (`npm install`) — están desactualizadas y pueden tener vulnerabilidades.
- ❌ **No conectar a clientes MCP** — los problemas que tenían siguen ahí.
- ❌ **No commitear credenciales** — aunque sean viejas, `.gitignore` las protege pero siempre verifica.
- ✅ **Sí se puede consultar el código** como referencia.
- ✅ **Sí se pueden copiar ideas concretas** al CLI activo si son útiles.

---

## 🗑️ ¿Cuándo borraremos esto definitivamente?

Cuando lleve **6 meses sin ninguna referencia** y el reemplazo (`google-apis/`) esté maduro y probado en producción con todos los flujos.

Aproximadamente: **noviembre de 2026**.

---

📁 Volver al [README principal](../README.md)

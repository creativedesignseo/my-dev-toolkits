# Shopify Admin MCP Server

Un servidor MCP (Model Context Protocol) para interactuar con la Shopify Admin GraphQL API. Permite a Agentes de IA gestionar productos, inventario y realizar operaciones masivas.

## 🚀 Instalación y Compilación

1. **Instalar dependencias**:
   ```bash
   cd toolkits/shopify-admin-mcp
   npm install
   ```

2. **Compilar el código TypeScript**:
   ```bash
   npm run build
   ```
   Esto generará los archivos JavaScript en la carpeta `build/`.

3. **Variables de Entorno**:
   El servidor requiere dos variables de entorno críticas. Puedes pasarlas directamente en la configuración del cliente MCP o crear un archivo `.env` (no recomendado para producción si se distribuye, pero útil localmente).

   - `SHOPIFY_ACCESS_TOKEN`: Token de acceso de la Admin API (comienza por `shpat_...` o similar).
   - `SHOP_DOMAIN`: Dominio de la tienda (ej. `mi-tienda.myshopify.com`).

## 🛠️ Herramientas Disponibles

### 1. `search_products`
Busca productos utilizando la sintaxis de búsqueda de Shopify.
- **Entrada**: 
  - `query`: String de búsqueda (ej. `title:Camiseta tag:verano`).
  - `first`: (Opcional) Número de resultados.

### 2. `create_product_with_variants`
Crea un nuevo producto con variantes opcionales.
- **Entrada**: `title`, `descriptionHtml`, `vendor`, `productType`, `variants` (array de objetos con precio/sku).

### 3. `update_inventory`
Ajusta el nivel de stock de una variante en una ubicación específica.
- **Entrada**: `inventoryItemId`, `locationId`, `availableDelta` (positivo para añadir, negativo para restar).

### 4. `run_bulk_operation`
Inicia una operación masiva de lectura (Bulk Operation).
- **Entrada**: `query` (El cuerpo de la query GraphQL para exportar).

## 🔌 Conexión con Antigravity / Clientes MCP

Para usar este servidor, configúralo en tu cliente MCP (ej. fichero de configuración de herramientas):

```json
{
  "mcpServers": {
    "shopify": {
      "command": "node",
      "args": ["path/to/toolkits/shopify-admin-mcp/build/index.js"],
      "env": {
        "SHOPIFY_ACCESS_TOKEN": "shpat_xxxxxxxxxxxxxxxx",
        "SHOP_DOMAIN": "tu-tienda.myshopify.com"
      }
    }
  }
}
```

## ⚠️ Manejo de Errores

El servidor maneja automáticamente:
- **Rate Limits (429)**: Devuelve un error descriptivo para que el Agente espere.
- **Errores GraphQL**: Parsea los errores devueltos por Shopify (ej. validación de campos) y los presenta claramente.

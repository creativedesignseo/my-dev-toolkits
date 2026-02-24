const { google } = require('googleapis');
const { OAuth2Client } = require('google-auth-library');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// ─── Configuración Inicial ──────────────────────────────────────
const credentialsPath = path.join(__dirname, 'credentials.json');

let credentials = {};
try {
    credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
} catch (e) {
    console.error("⚠️ No se encontraron credenciales. Ejecuta get-refresh-token.js primero.");
    process.exit(1);
}

const oauth2Client = new OAuth2Client(
    credentials.client_id,
    credentials.client_secret,
    'http://localhost:3001/oauth2callback'
);

if (credentials.refresh_token) {
    oauth2Client.setCredentials({ refresh_token: credentials.refresh_token });
}

// Inicializar la Content API for Shopping
const shopping = google.content({ version: 'v2.1', auth: oauth2Client });

// Validar que se provea Merchant ID
function requireMerchantId(args) {
    if (!args.merchantId) {
        throw new Error("El parámetro 'merchantId' es obligatorio para consultar la Merchant API.");
    }
    return args.merchantId;
}

// ─── Definición de Herramientas (Tools) ─────────────────────────
const TOOL_DEFINITIONS = [
    {
        name: 'list_products',
        description: 'Obtener la lista de productos del Merchant Center',
        inputSchema: {
            type: 'object',
            properties: {
                merchantId: { type: 'string', description: 'El ID numérico único de la cuenta de Merchant Center' },
                maxResults: { type: 'number', description: 'Número máximo de productos a retornar (por defecto 50)' }
            },
            required: ['merchantId']
        }
    },
    {
        name: 'get_product',
        description: 'Obtener los detalles de un producto específico',
        inputSchema: {
            type: 'object',
            properties: {
                merchantId: { type: 'string', description: 'El ID de la cuenta de Merchant Center' },
                productId: { type: 'string', description: 'El ID del producto (generalmente en formato online:es:ES:SKU)' }
            },
            required: ['merchantId', 'productId']
        }
    }
];

// ─── Controladores de las herramientas ──────────────────────────
const handlers = {
    async list_products(args) {
        const merchantId = requireMerchantId(args);
        const maxResults = args.maxResults || 50;
        
        const res = await shopping.products.list({
            merchantId: merchantId,
            maxResults: maxResults
        });
        
        return res.data;
    },
    
    async get_product(args) {
        const merchantId = requireMerchantId(args);
        if (!args.productId) throw new Error("El parametro 'productId' es obligatorio.");
        
        const res = await shopping.products.get({
            merchantId: merchantId,
            productId: args.productId
        });
        
        return res.data;
    }
};

// ─── Interfaz JSON-RPC (MCP) ────────────────────────────────────
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});

function sendResponse(id, result) {
    console.log(JSON.stringify({ jsonrpc: '2.0', id, result }));
}

function sendError(id, code, message) {
    console.log(JSON.stringify({ jsonrpc: '2.0', id, error: { code, message } }));
}

rl.on('line', async (line) => {
    try {
        const req = JSON.parse(line);
        if (!req.id && req.method) return; // ignore notifications

        let res;
        switch (req.method) {
            case 'initialize':
                res = {
                    protocolVersion: '2024-11-05',
                    capabilities: { tools: {} },
                    serverInfo: { name: 'google-merchant-mcp', version: '1.0.0' }
                };
                break;

            case 'notifications/initialized':
                return;

            case 'tools/list':
                res = { tools: TOOL_DEFINITIONS };
                break;

            case 'tools/call':
                const toolName = req.params?.name;
                const args = req.params?.arguments || {};
                try {
                    if (!handlers[toolName]) {
                        throw new Error(`Herramienta desconocida: ${toolName}`);
                    }
                    const result = await handlers[toolName](args);
                    // Standard MCP output is text content
                    res = {
                        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
                    };
                } catch (e) {
                    const errorMsg = e.response?.data?.error?.message || e.message;
                    res = {
                        content: [{ type: 'text', text: `Error: ${errorMsg}` }],
                        isError: true
                    };
                }
                break;

            default:
                sendError(req.id, -32601, `Method not found: ${req.method}`);
                return;
        }

        sendResponse(req.id, res);
    } catch (e) {
        // Ignorar JSON malformados en modo stdio
    }
});

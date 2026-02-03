const { google } = require('googleapis');
const { OAuth2Client } = require('google-auth-library');
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const readline = require('readline');

// Configuración de credenciales
const credentialsPath = path.join(__dirname, 'credentials.json');
process.env.GOOGLE_CLOUD_PROJECT = 'amsip-com-152005'; // Forzar proyecto correcto
let credentials = {};
try {
    credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
} catch (e) {
    console.error("⚠️ No se encontraron credenciales. Ejecuta basic-auth.js primero.");
}

const oauth2Client = new OAuth2Client(
    credentials.client_id,
    credentials.client_secret,
    'http://localhost:3001/oauth2callback'
);

if (credentials.refresh_token) {
    oauth2Client.setCredentials({ refresh_token: credentials.refresh_token });
}

const tagmanager = google.tagmanager({ version: 'v2', auth: oauth2Client });

const tools = {
    // Listar Cuentas de GTM
    async listAccounts() {
        try {
            const res = await tagmanager.accounts.list();
            return res.data.account || [];
        } catch (e) { return { error: e.message }; }
    },

    // Listar Contenedores de una Cuenta
    async listContainers(accountPath) {
        try {
            // accountPath debe ser 'accounts/123456'
            const res = await tagmanager.accounts.containers.list({ parent: accountPath });
            return res.data.container || [];
        } catch (e) { return { error: e.message }; }
    },

    // Listar Etiquetas (Tags) de un Contenedor
    async listTags(containerPath) {
        try {
            // 1. Obtener Workspaces
            const workspacesRes = await tagmanager.accounts.containers.workspaces.list({ parent: containerPath });
            const workspaces = workspacesRes.data.workspace;

            if (!workspaces || workspaces.length === 0) {
                return { error: "No se encontraron workspaces en este contenedor." };
            }

            // Usamos el primer workspace (normalmente 'Default Workspace' o el activo)
            const activeWorkspace = workspaces[0];
            
            // 2. Listar Tags de ese workspace
            const tagsRes = await tagmanager.accounts.containers.workspaces.tags.list({
                parent: activeWorkspace.path
            });
            
            const tags = tagsRes.data.tag || [];

            // 3. (Opcional) Listar Triggers para enriquecer la info
            const triggersRes = await tagmanager.accounts.containers.workspaces.triggers.list({
                parent: activeWorkspace.path
            });
            const triggers = triggersRes.data.trigger || [];

            // Mapear respuesta enriquecida
            return tags.map(t => {
                const triggerNames = t.firingTriggerId?.map(id => 
                    triggers.find(tr => tr.triggerId === id)?.name || id
                ) || [];

                return {
                    name: t.name,
                    type: t.type,
                    tagId: t.tagId,
                    triggers: triggerNames,
                    parameter: t.parameter // Para ver detalles como Measurement ID
                };
            });

        } catch (e) { return { error: e.message }; }
    },
    
    // Crear una Etiqueta Básica (Ejemplo GA4 Config)
    async createGA4ConfigTag(containerPath, measurementId) {
        try {
             const workspaces = await tagmanager.accounts.containers.workspaces.list({ parent: containerPath });
             const workspacePath = workspaces.data.workspace?.[0]?.path;
             
             if (!workspacePath) return { error: "No workspace found" };

             const res = await tagmanager.accounts.containers.workspaces.tags.create({
                 parent: workspacePath,
                 requestBody: {
                     name: `GA4 Configuration - ${measurementId}`,
                     type: 'gaawc', // Google Analytics 4 Configuration
                     parameter: [
                         { key: 'measurementId', type: 'template', value: measurementId }
                     ],
                     firingTriggerId: [] // Sin triggers por ahora, o buscar 'All Pages'
                 }
             });
             return res.data;
        } catch (e) { return { error: e.message }; }
    }
};

// Interface MCP
const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: false });

function sendResponse(id, result) {
    console.log(JSON.stringify({ jsonrpc: '2.0', id, result }));
}

function sendError(id, code, message) {
    console.log(JSON.stringify({ jsonrpc: '2.0', id, error: { code, message } }));
}

rl.on('line', async (line) => {
    try {
        const req = JSON.parse(line);
        if (!req.id && req.method) return;

        let res;
        switch (req.method) {
            case 'initialize':
                res = { 
                    protocolVersion: '2024-11-05', 
                    capabilities: { tools: {} }, 
                    serverInfo: { name: 'google-tag-manager-mcp', version: '1.0.0' } 
                };
                break;
            case 'tools/list':
                res = {
                    tools: [
                        { name: 'list_accounts', description: 'Listar cuentas de GTM', inputSchema: { type: 'object', properties: {} } },
                        { name: 'list_containers', description: 'Listar contenedores de una cuenta', inputSchema: { type: 'object', properties: { accountPath: { type: 'string', description: 'accounts/1234' } }, required: ['accountPath'] } },
                         { name: 'list_tags', description: 'Listar etiquetas de un contenedor', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'accounts/123/containers/456' } }, required: ['containerPath'] } }
                    ]
                };
                break;
            case 'tools/call':
                const args = req.params?.arguments || {};
                try {
                    let result;
                    switch (req.params?.name) {
                        case 'list_accounts': result = await tools.listAccounts(); break;
                        case 'list_containers': result = await tools.listContainers(args.accountPath); break;
                        case 'list_tags': result = await tools.listTags(args.containerPath); break;
                        default: throw new Error('Herramienta desconocida');
                    }
                    res = { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
                } catch (e) {
                    res = { content: [{ type: 'text', text: e.message }], isError: true };
                }
                break;
            default:
                sendError(req.id, -32601, 'Method not found');
                return;
        }
        sendResponse(req.id, res);
    } catch (e) {}
});

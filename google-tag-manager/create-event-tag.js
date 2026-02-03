const { google } = require('googleapis');
const { OAuth2Client } = require('google-auth-library');
const fs = require('fs');
const path = require('path');

const credentialsPath = path.join(__dirname, 'credentials.json');
let credentials = {};
try { credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8')); } 
catch (e) { process.exit(1); }

const oauth2Client = new OAuth2Client(
    credentials.client_id,
    credentials.client_secret,
    'http://localhost:3001/oauth2callback'
);
if (credentials.refresh_token) oauth2Client.setCredentials({ refresh_token: credentials.refresh_token });

const tagmanager = google.tagmanager({ version: 'v2', auth: oauth2Client });

const CONTAINER_ID = 'accounts/6203566842/containers/242527726';
const MEASUREMENT_ID = 'G-RLJD3KBT0J';

async function createEventTag() {
    try {
        console.log("🔍 Buscando Workspace...");
        const workspacesRes = await tagmanager.accounts.containers.workspaces.list({ parent: CONTAINER_ID });
        const wsPath = workspacesRes.data.workspace?.[0]?.path;
        console.log(`✅ Workspace: ${wsPath}`);

        // 1. Buscar Trigger WhatsApp para obtener su ID
        console.log("🔍 Buscando Trigger 'Click - WhatsApp Button'...");
        const triggersRes = await tagmanager.accounts.containers.workspaces.triggers.list({ parent: wsPath });
        const waTrigger = triggersRes.data.trigger?.find(t => t.name === 'Click - WhatsApp Button');
        
        if (!waTrigger) throw new Error("Trigger WhatsApp no encontrado. ¿Se borró?");
        console.log(`✅ Trigger ID: ${waTrigger.triggerId}`);

        // 2. Crear Tag Evento
        // Intentaremos pasar el measurementId. Si falla, es posible que requiera configuración via Google Tag.
        console.log("🛠️ Creando Tag de Evento...");
        const tagRes = await tagmanager.accounts.containers.workspaces.tags.create({
            parent: wsPath,
            requestBody: {
                name: 'GA4 Event - WhatsApp Click',
                type: 'gaawe', 
                parameter: [
                    { key: 'measurementIdOverride', type: 'template', value: MEASUREMENT_ID },
                    { key: 'eventName', type: 'template', value: 'whatsapp_click' }
                ],
                firingTriggerId: [waTrigger.triggerId]
            }
        });
        console.log(`✅ Event Tag Creado! ID: ${tagRes.data.tagId}`);

    } catch (e) {
        console.error("❌ Error:", e.message);
        if (e.errors) console.error(JSON.stringify(e.errors, null, 2));
    }
}

createEventTag();

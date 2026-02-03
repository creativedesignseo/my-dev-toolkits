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

async function updateTrigger() {
    try {
        console.log("🔍 Buscando Workspace...");
        const workspacesRes = await tagmanager.accounts.containers.workspaces.list({ parent: CONTAINER_ID });
        const wsPath = workspacesRes.data.workspace?.[0]?.path;
        
        console.log("🛠️ Actualizando Trigger 4 (Click - Conversion Buttons) con IDs estables...");
        
        // El trigger 4 ya existe (lo vimos en el log anterior).
        // Actualizamos su filtro para usar IDs, mucho más robusto que clases CSS.
        
        await tagmanager.accounts.containers.workspaces.triggers.update({
            path: `${wsPath}/triggers/4`, 
            requestBody: {
                name: 'Click - Conversion Buttons',
                type: 'click', 
                filter: [
                    {
                        type: 'cssSelector', 
                        parameter: [
                            { type: 'template', key: 'arg0', value: '{{Click Element}}' },
                            // Selector actualizado para coincidir con los nuevos IDs que acabamos de poner en el código
                            { type: 'template', key: 'arg1', value: '#btn-whatsapp-hero, #btn-whatsapp-cta' } 
                        ]
                    }
                ]
            }
        });
        console.log(`✅ Trigger 4 actualizado con selectores de ID.`);

        console.log("📦 Publicando cambios GTM...");
        const createVerRes = await tagmanager.accounts.containers.workspaces.create_version({
            path: wsPath,
            requestBody: { name: 'Update Trigger to use Robust IDs' }
        });
        
        const version = createVerRes.data.containerVersion;
        console.log("Details:", version);

        if (!version.path) {
            console.warn("⚠️ Path missing in response, constructing manually...");
            version.path = `accounts/6203566842/containers/242527726/versions/${version.containerVersionId}`;
        }
        console.log(`🚀 Intentando publicar path: ${version.path}`);

        await tagmanager.accounts.containers.versions.publish({
            path: version.path
        });
        
        console.log(`🌟 Nueva versión publicada: ${version.containerVersionId}`);

    } catch (e) {
        console.error("❌ Error:", e.message);
        if (e.errors) console.error(JSON.stringify(e.errors, null, 2));
    }
}

updateTrigger();

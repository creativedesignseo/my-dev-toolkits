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

async function publish() {
    try {
        const workspacesRes = await tagmanager.accounts.containers.workspaces.list({ parent: CONTAINER_ID });
        const wsPath = workspacesRes.data.workspace?.[0]?.path;
        console.log(`✅ Workspace: ${wsPath}`);

        console.log("📦 Creando Versión Final...");
        const createVerRes = await tagmanager.accounts.containers.workspaces.create_version({
            path: wsPath,
            requestBody: { name: 'Full Setup: GA4 + WhatsApp Event' }
        });
        
        const version = createVerRes.data.containerVersion;
        console.log(`✅ Versión Creada: ${version.containerVersionId}`);

        console.log("🚀 Publicando...");
        await tagmanager.accounts.containers.versions.publish({
            path: version.path
        });
        console.log(`🌟 PUBLICADO CON ÉXITO!`);

    } catch (e) {
        console.error("❌ Error:", e.message);
        if (e.errors) console.error(JSON.stringify(e.errors, null, 2));
    }
}

publish();

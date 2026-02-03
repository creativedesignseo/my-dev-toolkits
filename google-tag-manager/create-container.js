const { google } = require('googleapis');
const { OAuth2Client } = require('google-auth-library');
const fs = require('fs');
const path = require('path');

// Configuración de credenciales
const credentialsPath = path.join(__dirname, 'credentials.json');
let credentials = {};
try {
    credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
} catch (e) {
    console.error("⚠️ No se encontraron credenciales.");
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

const tagmanager = google.tagmanager({ version: 'v2', auth: oauth2Client });

async function createContainer() {
    const ACCOUNT_ID = 'accounts/6203566842'; // adspubli
    const CONTAINER_NAME = 'Taxi Lux Ride';
    
    console.log(`🚀 Creando contenedor '${CONTAINER_NAME}' en ${ACCOUNT_ID}...`);

    try {
        const res = await tagmanager.accounts.containers.create({
            parent: ACCOUNT_ID,
            requestBody: {
                name: CONTAINER_NAME,
                usageContext: ['web']
            }
        });

        console.log("✅ Contenedor Creado con Éxito!");
        console.log("Nombre:", res.data.name);
        console.log("Container ID (GTM-XXXX):", res.data.publicId);
        console.log("Internal ID:", res.data.containerId);
        console.log("URL:", res.data.tagManagerUrl);

    } catch (e) {
        console.error("❌ Error creando contenedor:", e.message);
        if (e.response) {
            console.error("Detalle:", JSON.stringify(e.response.data, null, 2));
        }
    }
}

createContainer();

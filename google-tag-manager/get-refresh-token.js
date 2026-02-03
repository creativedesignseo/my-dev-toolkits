const { OAuth2Client } = require('google-auth-library');
const http = require('http');
const url = require('url');
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const { exec } = require('child_process');

// Configuración base
const configPath = path.join(__dirname, 'google-tag-manager.yaml');

// Usamos los mismos credenciales que GA4/Ads por ahora (del proyecto amsip-com)
// Usamos los mismos credenciales que GA4/Ads por ahora (del proyecto amsip-com)
const CLIENT_ID = 'YOUR_CLIENT_ID';
const CLIENT_SECRET = 'YOUR_CLIENT_SECRET';
const REDIRECT_URI = 'http://localhost:3001/oauth2callback';

// Scopes para Tag Manager
const SCOPES = [
    'https://www.googleapis.com/auth/tagmanager.readonly',
    'https://www.googleapis.com/auth/tagmanager.edit.containers',
    'https://www.googleapis.com/auth/tagmanager.manage.accounts',
    'https://www.googleapis.com/auth/tagmanager.publish'
];

const oauth2Client = new OAuth2Client(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI);

function openBrowser(url) {
    exec(`start "" "${url}"`);
}

async function getRefreshToken() {
    return new Promise((resolve, reject) => {
        const server = http.createServer(async (req, res) => {
            if (req.url.startsWith('/oauth2callback')) {
                const q = url.parse(req.url, true).query;
                res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
                res.end('<h1>✅ Autenticación GTM Exitosa!</h1><p>Vuelve a la terminal.</p>');
                
                const { tokens } = await oauth2Client.getToken(q.code);
                server.close();
                resolve(tokens.refresh_token);
            }
        });

        server.listen(3001, () => {
            const authUrl = oauth2Client.generateAuthUrl({
                access_type: 'offline',
                scope: SCOPES,
                prompt: 'consent'
            });
            console.log('🚀 Abriendo navegador para Google Tag Manager...\n');
            openBrowser(authUrl);
        });
    });
}

(async () => {
    try {
        console.log("=".repeat(50));
        console.log("  GOOGLE TAG MANAGER - AUTH SETUP");
        console.log("=".repeat(50));
        
        const refreshToken = await getRefreshToken();
        
        const config = {
            client_id: CLIENT_ID,
            client_secret: CLIENT_SECRET,
            refresh_token: refreshToken
        };
        
        fs.writeFileSync(configPath, yaml.dump(config));
        
        // Crear copia para credentials.json (formato standard)
        const credentialsJson = {
            type: 'authorized_user',
            client_id: CLIENT_ID,
            client_secret: CLIENT_SECRET,
            refresh_token: refreshToken,
            quota_project_id: 'amsip-com-152005'
        };
        
        fs.writeFileSync(path.join(__dirname, 'credentials.json'), JSON.stringify(credentialsJson, null, 2));

        console.log("\n✅ Refresh Token guardado en google-tag-manager.yaml y credentials.json");
        process.exit(0);
    } catch (e) {
        console.error("❌ Error:", e.message);
        process.exit(1);
    }
})();

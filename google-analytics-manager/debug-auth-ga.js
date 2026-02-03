const { google } = require('googleapis');
const { OAuth2Client } = require('google-auth-library');
const fs = require('fs');
const path = require('path');

const credentialsPath = path.join(__dirname, 'credentials.json');
let credentials = {};
try { credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8')); } 
catch (e) { process.exit(1); }

// Try to find Client ID/Secret in file, or fallback to GTM ones (assuming user re-used them?)
// Wait, I should use the Values from get-refresh-token.js placeholders if I didn't update them?
// No, I need real values. I'll use the ones I know work (from GTM setup).
const CLIENT_ID = 'YOUR_CLIENT_ID';
const CLIENT_SECRET = 'YOUR_CLIENT_SECRET';

const oauth2Client = new OAuth2Client(CLIENT_ID, CLIENT_SECRET);
if (credentials.refresh_token) oauth2Client.setCredentials({ refresh_token: credentials.refresh_token });

async function checkScopes() {
    try {
        console.log("Obteniendo Access Token...");
        const tokenResponse = await oauth2Client.getAccessToken();
        const accessToken = tokenResponse.token;

        const tokenInfo = await oauth2Client.getTokenInfo(accessToken);
        console.log("\n--- TOKEN SCOPES ---");
        console.log(tokenInfo.scopes);
        
        if (tokenInfo.scopes.includes('https://www.googleapis.com/auth/analytics.edit')) {
            console.log("✅ TIENE PERMISO DE EDICIÓN (analytics.edit)");
        } else {
            console.log("❌ FALTA PERMISO DE EDICIÓN");
        }
    } catch (e) {
        console.error("Error:", e.message);
    }
}

checkScopes();

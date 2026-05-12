const { OAuth2Client } = require('google-auth-library');
const http = require('http');
const url = require('url');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

const credentialsPath = path.join(__dirname, 'credentials.json');
const tokenPath = path.join(__dirname, 'token.json');

if (!fs.existsSync(credentialsPath)) {
    console.error("❌ No se encontró credentials.json. Por favor agrégalo.");
    process.exit(1);
}

const credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));

const oauth2Client = new OAuth2Client(
    credentials.client_id,
    credentials.client_secret,
    'http://localhost:3001/oauth2callback'
);

const SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
];

function openBrowser(authUrl) {
    exec(`open "${authUrl}"`, (error) => {
        if (error) {
            console.log('⚠️ No se pudo abrir el navegador automáticamente.');
        }
    });
}

async function getRefreshToken() {
    return new Promise((resolve, reject) => {
        const server = http.createServer(async (req, res) => {
            try {
                if (req.url && req.url.startsWith('/oauth2callback')) {
                    const q = url.parse(req.url, true).query;

                    if (q.error) {
                        res.writeHead(400, { 'Content-Type': 'text/html; charset=utf-8' });
                        res.end('<h1>❌ Error de autenticación</h1><p>' + q.error + '</p>');
                        server.close();
                        reject(new Error(q.error));
                        return;
                    }

                    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
                    res.end('<h1>✅ Autorización exitosa!</h1><p>Ya puedes cerrar esta ventana y volver a la terminal.</p>');

                    console.log('✅ Código recibido. Intercambiando por tokens...');

                    try {
                        const { tokens } = await oauth2Client.getToken(q.code);
                        server.close();
                        resolve(tokens);
                    } catch (tokenError) {
                        server.close();
                        reject(tokenError);
                    }
                }
            } catch (e) {
                server.close();
                reject(e);
            }
        });

        server.listen(3001, () => {
            const authUrl = oauth2Client.generateAuthUrl({
                access_type: 'offline',
                scope: SCOPES,
                prompt: 'consent'
            });

            console.log('\n🚀 Abriendo navegador para autenticación...\n');
            console.log('👉 Si no se abre automáticamente, visita esta URL:\n');
            console.log(authUrl);
            console.log('\n⏳ Esperando autenticación con la cuenta info@one.adspubli.com...\n');

            openBrowser(authUrl);
        });

        server.on('error', (err) => {
            reject(err);
        });
    });
}

(async () => {
    try {
        console.log("=".repeat(50));
        console.log("  GMAIL MCP - OBTENER REFRESH TOKEN");
        console.log("=".repeat(50));
        console.log("\nIniciando proceso de autenticación...\n");

        const tokens = await getRefreshToken();

        fs.writeFileSync(tokenPath, JSON.stringify(tokens, null, 2));

        console.log("\n" + "=".repeat(50));
        console.log("🎉 ¡ÉXITO! Token guardado en token.json");
        console.log("=".repeat(50));
        console.log("\n📋 El MCP de Gmail está listo para usar con la cuenta autorizada.\n");

        process.exit(0);
    } catch (e) {
        console.error("\n❌ Error:", e.message);
        process.exit(1);
    }
})();

const { OAuth2Client } = require('google-auth-library');
const http = require('http');
const url = require('url');
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const { exec } = require('child_process');

// Leer configuración actual
const configPath = path.join(__dirname, 'google-ads.yaml');
let config = {};
try {
    const fileContents = fs.readFileSync(configPath, 'utf8');
    config = yaml.load(fileContents);
} catch (e) {
    console.error("Error leyendo google-ads.yaml:", e);
    process.exit(1);
}

const CLIENT_ID = config.client_id;
const CLIENT_SECRET = config.client_secret;
const REDIRECT_URI = 'http://localhost:3000/oauth2callback';

if (!CLIENT_ID || !CLIENT_SECRET || CLIENT_ID.includes('INSERT')) {
    console.error("❌ Faltan el Client ID o Secret en google-ads.yaml");
    process.exit(1);
}

const oauth2Client = new OAuth2Client(
    CLIENT_ID,
    CLIENT_SECRET,
    REDIRECT_URI
);

// Escopes necesarios para gestionar Google Ads
const SCOPES = ['https://www.googleapis.com/auth/adwords'];

// Función para abrir URL en Windows
function openBrowser(url) {
    exec(`start "" "${url}"`, (error) => {
        if (error) {
            console.log('⚠️ No se pudo abrir el navegador automáticamente.');
            console.log('👉 Copia y pega esta URL en tu navegador:\n');
            console.log(url);
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
                        res.end('Error de autenticación: ' + q.error);
                        server.close();
                        reject(new Error(q.error));
                        return;
                    }
                    
                    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
                    res.end('<h1>✅ Autenticación exitosa!</h1><p>Ya puedes cerrar esta ventana y volver a la terminal.</p>');
                    
                    console.log('✅ Código recibido. Intercambiando por tokens...');
                    
                    try {
                        const { tokens } = await oauth2Client.getToken(q.code);
                        server.close();
                        resolve(tokens.refresh_token);
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

        server.listen(3000, () => {
            const authUrl = oauth2Client.generateAuthUrl({
                access_type: 'offline',
                scope: SCOPES,
                prompt: 'consent'
            });
            
            console.log('🚀 Abriendo navegador para autenticación...\n');
            console.log('👉 Si no se abre automáticamente, visita esta URL:\n');
            console.log(authUrl);
            console.log('\n⏳ Esperando autenticación...\n');
            
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
        console.log("  GOOGLE ADS - OBTENER REFRESH TOKEN");
        console.log("=".repeat(50));
        console.log("\nIniciando proceso de autenticación...\n");
        
        const refreshToken = await getRefreshToken();
        
        console.log("\n" + "=".repeat(50));
        console.log("🎉 ¡ÉXITO! Refresh Token obtenido:");
        console.log("=".repeat(50));
        console.log("\n" + refreshToken + "\n");
        
        // Actualizar archivo YAML
        config.refresh_token = refreshToken;
        fs.writeFileSync(configPath, yaml.dump(config));
        
        console.log("✅ Archivo google-ads.yaml actualizado automáticamente.");
        console.log("\n📋 Próximo paso: Configura el login_customer_id en el archivo.");
        
        process.exit(0);
        
    } catch (e) {
        console.error("\n❌ Error:", e.message);
        process.exit(1);
    }
})();

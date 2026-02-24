const { OAuth2Client } = require('google-auth-library');
const http = require('http');
const url = require('url');
const open = require('open');
const fs = require('fs');
const path = require('path');

const credentialsPath = path.join(__dirname, 'credentials.json');

if (!fs.existsSync(credentialsPath)) {
    console.error("No se encontró credentials.json. Por favor agrégalo.");
    process.exit(1);
}

const credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));

const client = new OAuth2Client(
    credentials.client_id,
    credentials.client_secret,
    'http://localhost:3001/oauth2callback'
);

// We need the Content API for Shopping scope
const SCOPES = ['https://www.googleapis.com/auth/content'];

async function getRefreshToken() {
    return new Promise((resolve, reject) => {
        const authorizeUrl = client.generateAuthUrl({
            access_type: 'offline',
            scope: SCOPES,
            prompt: 'consent' // Forces consent screen to ensure to get refresh_token
        });

        console.log('Abriendo navegador para autorización...\nSi no se abre automáticamente, entra aquí:\n\n' + authorizeUrl + '\n');
        open(authorizeUrl);

        const server = http.createServer(async (req, res) => {
            try {
                if (req.url.indexOf('/oauth2callback') > -1) {
                    const qs = new url.URL(req.url, 'http://localhost:3001').searchParams;
                    const code = qs.get('code');
                    
                    res.writeHead(200, { 'Content-Type': 'text/html' });
                    res.end('<h1>Autorizacion exitosa!</h1><p>Puedes cerrar esta ventana y revisar tu terminal.</p>');
                    server.destroy();
                    
                    const { tokens } = await client.getToken(code);
                    
                    console.log("\n✅ ¡Autorización Exitosa!\n");
                    
                    if (tokens.refresh_token) {
                        credentials.refresh_token = tokens.refresh_token;
                        fs.writeFileSync(credentialsPath, JSON.stringify(credentials, null, 2));
                        console.log("-> refresh_token guardado en credentials.json 🎉");
                    } else {
                        console.log("⚠️ No se recibió refresh_token. (Asegúrate de que la APP tenga estado 'Testing' o de forzar prompt: 'consent')");
                    }
                    
                    resolve(tokens);
                }
            } catch (e) {
                reject(e);
            }
        });

        const destroyer = require('server-destroy');
        destroyer(server);
        server.listen(3001, () => {
            console.log('👉 Servidor local esperando el callback en http://localhost:3001...');
        });
    });
}

getRefreshToken().catch(console.error);

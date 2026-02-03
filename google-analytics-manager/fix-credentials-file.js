const fs = require('fs');
const path = require('path');

const credentialsPath = path.join(__dirname, 'credentials.json');
const CLIENT_ID = 'YOUR_CLIENT_ID';
const CLIENT_SECRET = 'YOUR_CLIENT_SECRET';

try {
    let credentials = {};
    if (fs.existsSync(credentialsPath)) {
        credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
    }

    // Ensure type is authorized_user
    credentials.type = 'authorized_user';
    credentials.client_id = CLIENT_ID;
    credentials.client_secret = CLIENT_SECRET;
    
    // Refresh token should already be there from get-refresh-token.js
    if (!credentials.refresh_token) {
        console.error("❌ No refresh token found in file! Run get-refresh-token.js first.");
        process.exit(1);
    }

    fs.writeFileSync(credentialsPath, JSON.stringify(credentials, null, 2));
    console.log("✅ credentials.json fixed with valid Client ID/Secret.");

} catch (e) {
    console.error("Error:", e.message);
}

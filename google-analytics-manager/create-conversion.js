const { google } = require('googleapis');
const { OAuth2Client } = require('google-auth-library');
const fs = require('fs');
const path = require('path');

const credentialsPath = path.join(__dirname, 'credentials.json');
let credentials = {};
try { credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8')); } 
catch (e) { process.exit(1); }

// CREDENCIALES REALES
// CREDENCIALES (Reemplazar con tus propios datos)
const CLIENT_ID = 'YOUR_CLIENT_ID';
const CLIENT_SECRET = 'YOUR_CLIENT_SECRET';

const oauth2Client = new OAuth2Client(CLIENT_ID, CLIENT_SECRET);
if (credentials.refresh_token) oauth2Client.setCredentials({ refresh_token: credentials.refresh_token });

const analyticsAdmin = google.analyticsadmin({ version: 'v1beta', auth: oauth2Client });
const PROPERTY_ID = '473797624';

async function createConversion() {
    try {
        console.log(`🔍 Configuring Key Event for Property ${PROPERTY_ID}...`);

        // Check if already exists?
        // Method: properties.conversionEvents.list
        // Resource name: properties/473797624/conversionEvents/whatsapp_click
        
        try {
            console.log("Checking if event exists...");
            const listRes = await analyticsAdmin.properties.conversionEvents.list({
                parent: `properties/${PROPERTY_ID}`
            });
            
            const existing = listRes.data.conversionEvents?.find(e => e.eventName === 'whatsapp_click');
            if (existing) {
                console.log(`✅ Event 'whatsapp_click' is ALREADY a Key Event (Conversion).`);
                console.log(`   Resource: ${existing.name}`);
                return;
            }
        } catch (listErr) {
            console.error("Warning: Could not list existing events.", listErr.message);
        }

        console.log("🆕 Creating Conversion Event...");
        const res = await analyticsAdmin.properties.conversionEvents.create({
            parent: `properties/${PROPERTY_ID}`,
            requestBody: {
                eventName: 'whatsapp_click'
            }
        });

        console.log("✅ SUCCESS! Event created.");
        console.log(`   Name: ${res.data.name}`);
        console.log(`   Event Name: ${res.data.eventName}`);

    } catch (e) {
        console.error("❌ Error:", e.message);
        if (e.response && e.response.data) {
             console.error("   Details:", JSON.stringify(e.response.data, null, 2));
        }
    }
}

createConversion();

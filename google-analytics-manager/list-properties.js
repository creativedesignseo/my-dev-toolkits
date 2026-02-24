const { AnalyticsAdminServiceClient } = require('@google-analytics/admin');
const path = require('path');

process.env.GOOGLE_APPLICATION_CREDENTIALS = path.join(__dirname, 'credentials.json');
process.env.GOOGLE_CLOUD_PROJECT = 'amsip-com-152005';

const adminClient = new AnalyticsAdminServiceClient();

async function listAllProperties() {
    try {
        console.log("Recuperando cuentas...");
        const [accounts] = await adminClient.listAccounts();
        
        for (const account of accounts) {
            console.log(`\n=== Cuenta: ${account.displayName} (${account.name}) ===`);
            try {
                const [properties] = await adminClient.listProperties({ filter: `parent:${account.name}` });
                if (properties.length === 0) {
                    console.log("  (Sin propiedades)");
                } else {
                    properties.forEach(p => {
                        console.log(`  - ${p.displayName} (ID: ${p.name.split('/')[1]})`);
                    });
                }
            } catch (err) {
                console.error(`  Error al obtener propiedades: ${err.message}`);
            }
        }
    } catch (e) {
        console.error("Error al obtener cuentas:", e.message);
    }
}

listAllProperties();

const { AnalyticsAdminServiceClient } = require('@google-analytics/admin');
const path = require('path');

process.env.GOOGLE_APPLICATION_CREDENTIALS = path.join(__dirname, 'credentials.json');
process.env.GOOGLE_CLOUD_PROJECT = 'amsip-com-152005';

const TARGET_PROPERTY_ID = '517085062';

async function findProperty() {
    console.log(`🔍 Buscando la propiedad ${TARGET_PROPERTY_ID} en todas las cuentas...`);
    const adminClient = new AnalyticsAdminServiceClient();

    try {
        const [accounts] = await adminClient.listAccounts();
        console.log(`ℹ️ Escaneando ${accounts.length} cuentas...`);

        for (const account of accounts) {
            try {
                const [properties] = await adminClient.listProperties({ filter: `parent:${account.name}` });
                const found = properties.find(p => p.name === `properties/${TARGET_PROPERTY_ID}`);
                
                if (found) {
                    console.log('\n✅ ¡ENCONTRADA!');
                    console.log(`📂 Cuenta: ${account.displayName}`);
                    console.log(`🆔 ID Cuenta: ${account.name}`);
                    console.log(`🏠 Propiedad: ${found.displayName}`);
                    console.log(`🔗 ID Propiedad: ${found.name}`);
                    return;
                }
            } catch (err) {
                // Ignore permission errors on specific accounts
            }
        }
        console.log('\n❌ Propiedad no encontrada en las cuentas accesibles.');
    } catch (e) {
        console.error('Error:', e.message);
    }
}

findProperty();

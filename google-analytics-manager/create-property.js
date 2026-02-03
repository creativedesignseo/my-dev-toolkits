const { AnalyticsAdminServiceClient } = require('@google-analytics/admin');
const path = require('path');

process.env.GOOGLE_APPLICATION_CREDENTIALS = path.join(__dirname, 'credentials.json');
process.env.GOOGLE_CLOUD_PROJECT = 'amsip-com-152005';

const ACCOUNT_ID = 'accounts/244866621';
const DOMAIN = 'taxiluxride.com';
const DISPLAY_NAME = 'Taxi Lux Ride';

async function createProperty() {
    const adminClient = new AnalyticsAdminServiceClient();

    console.log(`🚀 Creando propiedad para ${DOMAIN} en ${ACCOUNT_ID}...`);

    try {
        // 1. Crear la Propiedad
        const [property] = await adminClient.createProperty({
            property: {
                parent: ACCOUNT_ID,
                displayName: DISPLAY_NAME,
                industryCategory: 'TRAVEL',
                timeZone: 'Europe/Madrid',
                currencyCode: 'EUR'
            }
        });

        console.log(`✅ Propiedad creada: ${property.displayName} (${property.name})`);

        // 2. Crear el Data Stream (Flujo de datos web) para obtener el Measurement ID
        console.log('🌊 Creando flujo de datos web...');
        
        const [dataStream] = await adminClient.createDataStream({
            parent: property.name,
            dataStream: {
                type: 'WEB_DATA_STREAM',
                displayName: `Web - ${DOMAIN}`,
                webStreamData: {
                    defaultUri: `https://${DOMAIN}`
                }
            }
        });

        console.log(`\n🎉 ¡ LISTO !`);
        console.log(`🆔 Measurement ID: ${dataStream.webStreamData.measurementId}`);
        console.log(`🔗 Stream ID: ${dataStream.name}`);
        console.log(`🏠 Propiedad ID: ${property.name.split('/')[1]}`);

    } catch (e) {
        console.error('❌ Error creando propiedad:', e);
    }
}

createProperty();

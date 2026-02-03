const { GoogleAdsApi } = require('google-ads-api');
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

// Cargar configuración
const configPath = path.join(__dirname, 'google-ads.yaml');
let config;
try {
    config = yaml.load(fs.readFileSync(configPath, 'utf8'));
    console.log('✅ Configuración cargada correctamente\n');
} catch (e) {
    console.error('❌ Error loading config:', e.message);
    process.exit(1);
}

// Limpiar valores
const refreshToken = String(config.refresh_token).trim();
const customerId = String(config.login_customer_id).replace(/['-]/g, '');

console.log('📋 Datos:');
console.log(`   Developer Token: ${config.developer_token}`);
console.log(`   Customer ID: ${customerId}`);
console.log(`   Refresh Token: ${refreshToken.substring(0, 40)}...`);
console.log('');

async function test() {
    try {
        console.log('📊 Inicializando cliente...\n');
        
        const client = new GoogleAdsApi({
            client_id: config.client_id,
            client_secret: config.client_secret,
            developer_token: config.developer_token
        });

        console.log('✓ Cliente API creado');

        const customer = client.Customer({
            customer_id: customerId,
            refresh_token: refreshToken
        });

        console.log('✓ Customer configurado');
        console.log('\n🔍 Ejecutando query...\n');
        
        const results = await customer.query(`
            SELECT customer.id, customer.descriptive_name
            FROM customer
            LIMIT 1
        `);
        
        console.log('✅ ÉXITO! Resultado:', JSON.stringify(results, null, 2));

    } catch (error) {
        console.error('\n❌ ERROR COMPLETO:');
        console.error('   Mensaje:', error.message);
        console.error('   Nombre:', error.name);
        
        if (error.errors) {
            console.error('   Errores API:', JSON.stringify(error.errors, null, 2));
        }
        
        if (error.stack) {
            console.error('\n   Stack trace (primeras líneas):');
            console.error(error.stack.split('\n').slice(0, 5).join('\n'));
        }
    }
}

test();

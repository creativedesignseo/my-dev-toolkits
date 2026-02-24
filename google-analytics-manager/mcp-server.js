const { BetaAnalyticsDataClient } = require('@google-analytics/data');
const { AnalyticsAdminServiceClient } = require('@google-analytics/admin');
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const readline = require('readline');

// Configurar credenciales
process.env.GOOGLE_APPLICATION_CREDENTIALS = path.join(__dirname, 'credentials.json');
process.env.GOOGLE_CLOUD_PROJECT = 'amsip-com-152005';

// Cargar configuración adicional (property_id por defecto)
const configPath = path.join(__dirname, 'google-analytics.yaml');
let config = {};
try {
    config = yaml.load(fs.readFileSync(configPath, 'utf8'));
} catch (e) {}

const dataClient = new BetaAnalyticsDataClient();
const adminClient = new AnalyticsAdminServiceClient();

const tools = {
    // Listar Cuentas
    async listAccounts() {
        try {
            const [accounts] = await adminClient.listAccounts();
            return accounts.map(a => ({ name: a.name, displayName: a.displayName }));
        } catch (e) { return { error: e.message }; }
    },

    // Listar Propiedades de una cuenta
    async listProperties(accountName) {
        try {
            const [properties] = await adminClient.listProperties({ filter: `parent:${accountName}` });
            return properties.map(p => ({ name: p.name, displayName: p.displayName, propertyId: p.name.split('/')[1] }));
        } catch (e) { return { error: e.message }; }
    },

    // Reporte Core (histórico)
    async runReport(propertyId, startDate = '30daysAgo', endDate = 'today', metrics = ['activeUsers'], dimensions = ['country']) {
        try {
            const [response] = await dataClient.runReport({
                property: `properties/${propertyId}`,
                dateRanges: [{ startDate, endDate }],
                dimensions: dimensions.map(d => ({ name: d })),
                metrics: metrics.map(m => ({ name: m })),
            });
            
            // Formatear respuesta
            const headers = [...dimensions, ...metrics];
            const rows = response.rows?.map(row => {
                const obj = {};
                row.dimensionValues?.forEach((v, i) => obj[dimensions[i]] = v.value);
                row.metricValues?.forEach((v, i) => obj[metrics[i]] = v.value);
                return obj;
            }) || [];
            
            return { headers, rows, rowCount: response.rowCount };
        } catch (e) { return { error: e.message }; }
    },

    // Reporte en Tiempo Real
    async runRealtimeReport(propertyId, metrics = ['activeUsers'], dimensions = ['city']) {
        try {
            const [response] = await dataClient.runRealtimeReport({
                property: `properties/${propertyId}`,
                dimensions: dimensions.map(d => ({ name: d })),
                metrics: metrics.map(m => ({ name: m })),
            });
            
            const rows = response.rows?.map(row => {
                const obj = {};
                row.dimensionValues?.forEach((v, i) => obj[dimensions[i]] = v.value);
                row.metricValues?.forEach((v, i) => obj[metrics[i]] = v.value);
                return obj;
            }) || [];
            
            return { rows, totalUsers: rows.reduce((sum, r) => sum + parseInt(r.activeUsers || 0), 0) };
        } catch (e) { return { error: e.message }; }
    },

    // Crear Propiedad + Data Stream
    async createPropertySetup(accountId, domain, displayName, timezone = 'Europe/Madrid', currency = 'EUR') {
        try {
            // 1. Crear Propiedad
            const [property] = await adminClient.createProperty({
                property: {
                    parent: accountId,
                    displayName: displayName || domain,
                    industryCategory: 'TRAVEL',
                    timeZone: timezone,
                    currencyCode: currency
                }
            });

            // 2. Crear Data Stream
            const [dataStream] = await adminClient.createDataStream({
                parent: property.name,
                dataStream: {
                    type: 'WEB_DATA_STREAM',
                    displayName: `Web - ${domain}`,
                    webStreamData: { defaultUri: `https://${domain}` }
                }
            });

            return {
                success: true,
                propertyName: property.displayName,
                propertyId: property.name.split('/')[1],
                measurementId: dataStream.webStreamData.measurementId,
                streamId: dataStream.name,
                setupUrl: `https://analytics.google.com/analytics/web/#/p${property.name.split('/')[1]}/admin/streams/table`
            };
        } catch (e) {
            return { error: e.message };
        }
    },

    // Crear Evento de Conversión (Key Event)
    async createConversionEvent(propertyId, eventName) {
        try {
            // Check if exists first
            const [list] = await adminClient.listConversionEvents({ parent: `properties/${propertyId}` });
            const existing = list.find(e => e.eventName === eventName);
            if (existing) return { status: 'exists', name: existing.name };

            const [conversion] = await adminClient.createConversionEvent({
                parent: `properties/${propertyId}`,
                conversionEvent: { eventName }
            });
            return { status: 'created', name: conversion.name };
        } catch (e) { return { error: e.message }; }
    },

    // Listar Enlaces de Google Ads
    async listGoogleAdsLinks(propertyId) {
        try {
            const [links] = await adminClient.listGoogleAdsLinks({ parent: `properties/${propertyId}` });
            return links;
        } catch (e) { return { error: e.message }; }
    },

    // Crear Enlace de Google Ads
    async createGoogleAdsLink(propertyId, customerId) {
        try {
            const [link] = await adminClient.createGoogleAdsLink({
                parent: `properties/${propertyId}`,
                googleAdsLink: {
                    customerId: customerId.replace(/-/g, ''), // Eliminar guiones
                    adsPersonalizationEnabled: { value: true }
                }
            });
            return link;
        } catch (e) { return { error: e.message }; }
    }
};

// Interface STDIO for MCP
const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: false });

function sendResponse(id, result) {
    const response = { jsonrpc: '2.0', id, result };
    console.log(JSON.stringify(response));
}

function sendError(id, code, message) {
    const response = { jsonrpc: '2.0', id, error: { code, message } };
    console.log(JSON.stringify(response));
}

rl.on('line', async (line) => {
    try {
        const req = JSON.parse(line);
        if (!req.id && req.method) return;
        let res;

        switch (req.method) {
            case 'initialize':
                res = { 
                    protocolVersion: '2024-11-05', 
                    capabilities: { tools: {} }, 
                    serverInfo: { name: 'google-analytics-mcp', version: '1.1.0' } 
                };
                break;
                
            case 'tools/list':
                res = {
                    tools: [
                        { name: 'list_accounts', description: 'Lista todas las cuentas de Google Analytics disponibles', inputSchema: { type: 'object', properties: {} } },
                        { name: 'list_properties', description: 'Lista las propiedades de una cuenta específica', inputSchema: { type: 'object', properties: { account_name: { type: 'string', description: 'ID de la cuenta (ej: accounts/123456)' } }, required: ['account_name'] } },
                        { name: 'create_property_setup', description: 'Crea una nueva propiedad GA4 + Flujo de datos Web', inputSchema: { type: 'object', properties: { account_id: { type: 'string', description: 'ID de la cuenta padre (ej: accounts/123456)' }, domain: { type: 'string', description: 'Dominio del sitio web (ej: ejemplo.com)' }, display_name: { type: 'string', description: 'Nombre visible de la propiedad' } }, required: ['account_id', 'domain'] } },
                        { name: 'run_report', description: 'Ejecuta un reporte histórico personalizado', inputSchema: { type: 'object', properties: { property_id: { type: 'string' }, start_date: { type: 'string' }, end_date: { type: 'string' }, metrics: { type: 'array', items: { type: 'string' } }, dimensions: { type: 'array', items: { type: 'string' } } }, required: ['property_id'] } },
                        { name: 'run_realtime_report', description: 'Muestra usuarios en tiempo real', inputSchema: { type: 'object', properties: { property_id: { type: 'string' } }, required: ['property_id'] } },
                        { name: 'create_conversion_event', description: 'Marca un evento como Key Event (Conversión)', inputSchema: { type: 'object', properties: { property_id: { type: 'string' }, event_name: { type: 'string' } }, required: ['property_id', 'event_name'] } },
                        { name: 'list_google_ads_links', description: 'Lista las vinculaciones con Google Ads de una propiedad', inputSchema: { type: 'object', properties: { property_id: { type: 'string' } }, required: ['property_id'] } },
                        { name: 'create_google_ads_link', description: 'Vincula una cuenta de Google Ads con la propiedad de Analytics', inputSchema: { type: 'object', properties: { property_id: { type: 'string', description: 'ID de la propiedad de Analytics' }, customer_id: { type: 'string', description: 'ID de la cuenta de Google Ads (con o sin guiones)' } }, required: ['property_id', 'customer_id'] } }
                    ]
                };
                break;
                
            case 'tools/call':
                const args = req.params?.arguments || {};
                try {
                    let result;
                    switch (req.params?.name) {
                        case 'list_accounts': result = await tools.listAccounts(); break;
                        case 'list_properties': result = await tools.listProperties(args.account_name); break;
                        case 'create_property_setup': result = await tools.createPropertySetup(args.account_id, args.domain, args.display_name); break;
                        case 'run_report': result = await tools.runReport(args.property_id, args.start_date, args.end_date, args.metrics, args.dimensions); break;
                        case 'run_realtime_report': result = await tools.runRealtimeReport(args.property_id, args.metrics, args.dimensions); break;
                        case 'create_conversion_event': result = await tools.createConversionEvent(args.property_id, args.event_name); break;
                        case 'list_google_ads_links': result = await tools.listGoogleAdsLinks(args.property_id); break;
                        case 'create_google_ads_link': result = await tools.createGoogleAdsLink(args.property_id, args.customer_id); break;
                        default: throw new Error('Herramienta desconocida');
                    }
                    res = { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
                } catch (err) {
                    res = { content: [{ type: 'text', text: 'Error: ' + err.message }], isError: true };
                }
                break;
                
            default:
                sendError(req.id, -32601, 'Method not found');
                return;
        }
        
        sendResponse(req.id, res);
    } catch (e) {}
});

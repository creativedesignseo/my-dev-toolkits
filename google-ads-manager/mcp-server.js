const { GoogleAdsApi } = require('google-ads-api');
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const http = require('http');

// Cargar configuración
const configPath = path.join(__dirname, 'google-ads.yaml');
let config;
try {
    config = yaml.load(fs.readFileSync(configPath, 'utf8'));
} catch (e) {
    console.error('Error loading config:', e);
    process.exit(1);
}

// Inicializar cliente de Google Ads
const client = new GoogleAdsApi({
    client_id: config.client_id,
    client_secret: config.client_secret,
    developer_token: config.developer_token
});

const customer = client.Customer({
    customer_id: config.login_customer_id,
    refresh_token: config.refresh_token
});

// Herramientas disponibles
const tools = {
    // Listar campañas
    async listCampaigns() {
        try {
            const campaigns = await customer.query(`
                SELECT 
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign.advertising_channel_type,
                    campaign_budget.amount_micros
                FROM campaign
                ORDER BY campaign.name
            `);
            return campaigns;
        } catch (error) {
            return { error: error.message };
        }
    },

    // Obtener métricas de campaña
    async getCampaignMetrics(campaignId) {
        try {
            const metrics = await customer.query(`
                SELECT 
                    campaign.id,
                    campaign.name,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr,
                    metrics.average_cpc
                FROM campaign
                WHERE campaign.id = ${campaignId}
                AND segments.date DURING LAST_30_DAYS
            `);
            return metrics;
        } catch (error) {
            return { error: error.message };
        }
    },

    // Listar grupos de anuncios
    async listAdGroups(campaignId) {
        try {
            const adGroups = await customer.query(`
                SELECT 
                    ad_group.id,
                    ad_group.name,
                    ad_group.status,
                    ad_group.cpc_bid_micros
                FROM ad_group
                WHERE campaign.id = ${campaignId}
            `);
            return adGroups;
        } catch (error) {
            return { error: error.message };
        }
    },

    // Obtener keywords
    async listKeywords(adGroupId) {
        try {
            const keywords = await customer.query(`
                SELECT 
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    ad_group_criterion.status,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros
                FROM keyword_view
                WHERE ad_group.id = ${adGroupId}
                AND segments.date DURING LAST_30_DAYS
            `);
            return keywords;
        } catch (error) {
            return { error: error.message };
        }
    },

    // Resumen de cuenta
    async getAccountSummary() {
        try {
            const summary = await customer.query(`
                SELECT 
                    customer.descriptive_name,
                    customer.currency_code,
                    customer.time_zone,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions
                FROM customer
                WHERE segments.date DURING LAST_30_DAYS
            `);
            return summary;
        } catch (error) {
            return { error: error.message };
        }
    }
};

// Servidor MCP simplificado (stdio)
const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});

console.error('Google Ads MCP Server started');

rl.on('line', async (line) => {
    try {
        const request = JSON.parse(line);
        let result;

        switch (request.method) {
            case 'initialize':
                result = {
                    protocolVersion: '2024-11-05',
                    capabilities: { tools: {} },
                    serverInfo: { name: 'google-ads-mcp', version: '1.0.0' }
                };
                break;

            case 'tools/list':
                result = {
                    tools: [
                        { name: 'list_campaigns', description: 'Lista todas las campañas de Google Ads' },
                        { name: 'get_campaign_metrics', description: 'Obtiene métricas de una campaña específica', inputSchema: { type: 'object', properties: { campaign_id: { type: 'string' } }, required: ['campaign_id'] } },
                        { name: 'list_ad_groups', description: 'Lista grupos de anuncios de una campaña', inputSchema: { type: 'object', properties: { campaign_id: { type: 'string' } }, required: ['campaign_id'] } },
                        { name: 'list_keywords', description: 'Lista keywords de un grupo de anuncios', inputSchema: { type: 'object', properties: { ad_group_id: { type: 'string' } }, required: ['ad_group_id'] } },
                        { name: 'get_account_summary', description: 'Resumen general de la cuenta de Google Ads' }
                    ]
                };
                break;

            case 'tools/call':
                const toolName = request.params.name;
                const args = request.params.arguments || {};
                
                switch (toolName) {
                    case 'list_campaigns':
                        result = { content: [{ type: 'text', text: JSON.stringify(await tools.listCampaigns(), null, 2) }] };
                        break;
                    case 'get_campaign_metrics':
                        result = { content: [{ type: 'text', text: JSON.stringify(await tools.getCampaignMetrics(args.campaign_id), null, 2) }] };
                        break;
                    case 'list_ad_groups':
                        result = { content: [{ type: 'text', text: JSON.stringify(await tools.listAdGroups(args.campaign_id), null, 2) }] };
                        break;
                    case 'list_keywords':
                        result = { content: [{ type: 'text', text: JSON.stringify(await tools.listKeywords(args.ad_group_id), null, 2) }] };
                        break;
                    case 'get_account_summary':
                        result = { content: [{ type: 'text', text: JSON.stringify(await tools.getAccountSummary(), null, 2) }] };
                        break;
                    default:
                        result = { error: { code: -32601, message: `Unknown tool: ${toolName}` } };
                }
                break;

            default:
                result = { error: { code: -32601, message: `Unknown method: ${request.method}` } };
        }

        console.log(JSON.stringify({ jsonrpc: '2.0', id: request.id, result }));
    } catch (error) {
        console.error('Error processing request:', error);
    }
});

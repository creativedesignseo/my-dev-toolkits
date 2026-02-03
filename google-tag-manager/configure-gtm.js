const { google } = require('googleapis');
const { OAuth2Client } = require('google-auth-library');
const fs = require('fs');
const path = require('path');

const credentialsPath = path.join(__dirname, 'credentials.json');
let credentials = {};
try { credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8')); } 
catch (e) { process.exit(1); }

const oauth2Client = new OAuth2Client(
    credentials.client_id,
    credentials.client_secret,
    'http://localhost:3001/oauth2callback'
);
if (credentials.refresh_token) oauth2Client.setCredentials({ refresh_token: credentials.refresh_token });

const tagmanager = google.tagmanager({ version: 'v2', auth: oauth2Client });

const CONTAINER_ID = 'accounts/6203566842/containers/242527726';
const MEASUREMENT_ID = 'G-RLJD3KBT0J';

async function configureGTM() {
    try {
        console.log("🔍 Buscando Workspace...");
        const workspacesRes = await tagmanager.accounts.containers.workspaces.list({ parent: CONTAINER_ID });
        const workspace = workspacesRes.data.workspace?.[0];
        if (!workspace) throw new Error("No se encontró Workspace.");
        const wsPath = workspace.path;
        console.log(`✅ Workspace: ${wsPath}`);

        // 1. Habilitar Variables Built-In necesarias
        console.log("Variabilizando...");
        const builtInTypes = ['pageUrl', 'clickElement', 'clickClasses', 'clickUrl'];
        const enabledVars = [];
        
        // Listamos las que ya hay para no re-crear
        const existingVarsRes = await tagmanager.accounts.containers.workspaces.built_in_variables.list({ parent: wsPath });
        const existingTypes = existingVarsRes.data.builtInVariable?.map(v => v.type) || [];

        for (const type of builtInTypes) {
            if (!existingTypes.includes(type)) {
                console.log(`  + Habilitando variable: ${type}`);
                await tagmanager.accounts.containers.workspaces.built_in_variables.create({
                    parent: wsPath,
                    type: type
                });
            }
        }
        
        // Refrescamos lista para obtener IDs
        const finalVarsRes = await tagmanager.accounts.containers.workspaces.built_in_variables.list({ parent: wsPath });
        const mapVars = {}; // map type -> account...variableId
        finalVarsRes.data.builtInVariable.forEach(v => mapVars[v.type] = v.name); // v.name es el nombre variable (ej: "Page URL")? No, v.name returns "Click Element" usually.
        // Wait, filters need the VARIABLE ID properly formatted. 
        // Built-in variables in trigger filters refer to {{Page URL}} which usually implies specific structure.
        // Actually, trigger filters refer to parameter: [{type: 'template', key: 'arg0', value: '{{Click Element}}'}]
        
        // 2. Trigger "Page View - All"
        console.log("🔍 Buscando Trigger 'All Pages'...");
        const triggersRes = await tagmanager.accounts.containers.workspaces.triggers.list({ parent: wsPath });
        let allPagesTrigger = triggersRes.data.trigger?.find(t => t.name === 'All Pages' || t.name === 'Page View - All');

        if (!allPagesTrigger) {
            console.log("  + Creando Trigger 'Page View - All'...");
            const t = await tagmanager.accounts.containers.workspaces.triggers.create({
                parent: wsPath,
                requestBody: {
                    name: 'Page View - All',
                    type: 'pageview'
                }
            });
            allPagesTrigger = t.data;
        }

        // 3. Trigger WhatsApp (Click Element matches CSS)
        // Check if exists
        let waTrigger = triggersRes.data.trigger?.find(t => t.name === 'Click - WhatsApp Button');
        if (!waTrigger) {
            console.log("  + Creando Trigger 'Click - WhatsApp Button'...");
            const waRes = await tagmanager.accounts.containers.workspaces.triggers.create({
                parent: wsPath,
                requestBody: {
                    name: 'Click - WhatsApp Button',
                    type: 'click', 
                    filter: [
                        {
                            type: 'cssSelector', // El operador correcto para selector CSS es 'cssSelector'
                            parameter: [
                                { type: 'template', key: 'arg0', value: '{{Click Element}}' }, // La variable a chequear
                                { type: 'template', key: 'arg1', value: 'button.bg-\\[\\#FFDB3A\\]' } // El selector
                            ]
                        }
                    ]
                }
            });
            waTrigger = waRes.data;
        }
        console.log(`✅ Trigger WhatsApp ID: ${waTrigger.triggerId}`);

        // 4. Configurar Tag GA4 Config
        // Check if exists
        const tagsRes = await tagmanager.accounts.containers.workspaces.tags.list({ parent: wsPath });
        let gaConfigTag = tagsRes.data.tag?.find(t => t.name.includes('GA4 Configuration'));
        
        if (!gaConfigTag) {
            console.log("  + Creando Tag GA4 Config...");
            const gaRes = await tagmanager.accounts.containers.workspaces.tags.create({
                parent: wsPath,
                requestBody: {
                    name: `GA4 Configuration - ${MEASUREMENT_ID}`,
                    type: 'gaawc',
                    parameter: [
                        { key: 'measurementId', type: 'template', value: MEASUREMENT_ID }
                    ],
                    firingTriggerId: [allPagesTrigger.triggerId]
                }
            });
            gaConfigTag = gaRes.data;
        }

        // 5. Configurar Tag GA4 Event
        let gaEventTag = tagsRes.data.tag?.find(t => t.name === 'GA4 Event - WhatsApp Click');
        if (!gaEventTag) {
             console.log("  + Creando Tag GA4 Event - WhatsApp...");
             try {
                 await tagmanager.accounts.containers.workspaces.tags.create({
                    parent: wsPath,
                    requestBody: {
                        name: 'GA4 Event - WhatsApp Click',
                        type: 'gaawe',
                        parameter: [
                            { key: 'measurementId', type: 'template', value: MEASUREMENT_ID },
                            { key: 'eventName', type: 'template', value: 'whatsapp_click' }
                        ],
                        firingTriggerId: [waTrigger.triggerId] // Usar variable correcta
                    }
                });
                console.log("✅ Tag GA4 Event creado.");
             } catch (e) {
                 console.error("⚠️ Error creando Event Tag (continuando publicación):", e.message);
                 // Si falla, al menos tendremos Trigger y Config
             }
        }

        // 6. Publicar (Crear Versión -> Publicar)
        console.log("📦 Creando versión...");
        const createVerRes = await tagmanager.accounts.containers.workspaces.create_version({
            parent: wsPath,
            requestBody: { name: 'Initial Setup via MCP' }
        });
        
        const version = createVerRes.data.containerVersion;
        console.log(`✅ Versión creada: ${version.containerVersionId}`);

        console.log("🚀 Publicando...");
        await tagmanager.accounts.containers.versions.publish({
            path: version.path
        });
        console.log(`🌟 Contenedor publicado exitosamente!`);

    } catch (e) {
        console.error("❌ Error:", e.message);
        if (e.response) console.error(JSON.stringify(e.response.data, null, 2));
    }
}

configureGTM();

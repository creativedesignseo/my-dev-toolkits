const { google } = require('googleapis');
const { OAuth2Client } = require('google-auth-library');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// ─── Credentials ────────────────────────────────────────────────
const credentialsPath = path.join(__dirname, 'credentials.json');
process.env.GOOGLE_CLOUD_PROJECT = 'amsip-com-152005';
let credentials = {};
try {
    credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
} catch (e) {
    console.error("⚠️ No se encontraron credenciales. Ejecuta get-refresh-token.js primero.");
}

const oauth2Client = new OAuth2Client(
    credentials.client_id,
    credentials.client_secret,
    'http://localhost:3001/oauth2callback'
);

if (credentials.refresh_token) {
    oauth2Client.setCredentials({ refresh_token: credentials.refresh_token });
}

const tagmanager = google.tagmanager({ version: 'v2', auth: oauth2Client });

// ─── Helper: resolve workspace path from container path ─────────
async function resolveWorkspacePath(containerPath) {
    const res = await tagmanager.accounts.containers.workspaces.list({ parent: containerPath });
    const ws = res.data.workspace;
    if (!ws || ws.length === 0) throw new Error("No se encontraron workspaces en este contenedor.");
    return ws[0].path;
}

// ─── Tool Definitions (for tools/list) ──────────────────────────
const TOOL_DEFINITIONS = [
    // ── Accounts ──
    { name: 'list_accounts', description: 'Listar todas las cuentas de GTM', inputSchema: { type: 'object', properties: {} } },
    { name: 'get_account', description: 'Obtener detalles de una cuenta', inputSchema: { type: 'object', properties: { accountPath: { type: 'string', description: 'Ej: accounts/123456' } }, required: ['accountPath'] } },
    { name: 'update_account', description: 'Actualizar una cuenta de GTM', inputSchema: { type: 'object', properties: { accountPath: { type: 'string', description: 'Ej: accounts/123456' }, requestBody: { type: 'object', description: 'Campos a actualizar (name, shareData, etc.)' } }, required: ['accountPath', 'requestBody'] } },

    // ── Containers ──
    { name: 'list_containers', description: 'Listar contenedores de una cuenta', inputSchema: { type: 'object', properties: { accountPath: { type: 'string', description: 'Ej: accounts/123456' } }, required: ['accountPath'] } },
    { name: 'get_container', description: 'Obtener detalles de un contenedor', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' } }, required: ['containerPath'] } },
    { name: 'create_container', description: 'Crear un nuevo contenedor en una cuenta', inputSchema: { type: 'object', properties: { accountPath: { type: 'string', description: 'Ej: accounts/123456' }, name: { type: 'string', description: 'Nombre del contenedor' }, usageContext: { type: 'array', items: { type: 'string', enum: ['web', 'android', 'ios', 'amp', 'server'] }, description: 'Contextos de uso. Ej: ["web"]' } }, required: ['accountPath', 'name', 'usageContext'] } },
    { name: 'update_container', description: 'Actualizar un contenedor existente', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' }, requestBody: { type: 'object', description: 'Campos a actualizar (name, notes, usageContext, etc.)' } }, required: ['containerPath', 'requestBody'] } },
    { name: 'delete_container', description: 'Eliminar un contenedor', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' } }, required: ['containerPath'] } },
    { name: 'get_container_snippet', description: 'Obtener el snippet de instalación de un contenedor', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' } }, required: ['containerPath'] } },

    // ── Workspaces ──
    { name: 'list_workspaces', description: 'Listar workspaces de un contenedor', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' } }, required: ['containerPath'] } },
    { name: 'get_workspace', description: 'Obtener detalles de un workspace', inputSchema: { type: 'object', properties: { workspacePath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789' } }, required: ['workspacePath'] } },
    { name: 'create_workspace', description: 'Crear un nuevo workspace', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' }, name: { type: 'string', description: 'Nombre del workspace' }, description: { type: 'string', description: 'Descripción opcional' } }, required: ['containerPath', 'name'] } },
    { name: 'delete_workspace', description: 'Eliminar un workspace', inputSchema: { type: 'object', properties: { workspacePath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789' } }, required: ['workspacePath'] } },
    { name: 'sync_workspace', description: 'Sincronizar un workspace con la última versión del contenedor', inputSchema: { type: 'object', properties: { workspacePath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789' } }, required: ['workspacePath'] } },
    { name: 'create_version', description: 'Crear una nueva versión del contenedor desde un workspace', inputSchema: { type: 'object', properties: { workspacePath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789' }, name: { type: 'string', description: 'Nombre de la versión' }, notes: { type: 'string', description: 'Notas de la versión' } }, required: ['workspacePath', 'name'] } },
    { name: 'resolve_conflict', description: 'Resolver un conflicto de workspace (acepta la entidad del workspace sobre la versión base)', inputSchema: { type: 'object', properties: { workspacePath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789' }, requestBody: { type: 'object', description: 'Entidad con los cambios a resolver' } }, required: ['workspacePath'] } },

    // ── Tags ──
    { name: 'list_tags', description: 'Listar etiquetas de un contenedor (auto-resuelve workspace)', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' } }, required: ['containerPath'] } },
    { name: 'get_tag', description: 'Obtener detalles de una etiqueta', inputSchema: { type: 'object', properties: { tagPath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789/tags/111' } }, required: ['tagPath'] } },
    { name: 'create_tag', description: 'Crear una nueva etiqueta en un contenedor. Tipos comunes: gaawc (GA4 Config), gaawe (GA4 Event), html (Custom HTML), img (Custom Image)', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' }, requestBody: { type: 'object', description: 'Tag body: {name, type, parameter: [{key, type, value}], firingTriggerId: [...]}' } }, required: ['containerPath', 'requestBody'] } },
    { name: 'update_tag', description: 'Actualizar una etiqueta existente', inputSchema: { type: 'object', properties: { tagPath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789/tags/111' }, requestBody: { type: 'object', description: 'Campos actualizados del tag' } }, required: ['tagPath', 'requestBody'] } },
    { name: 'delete_tag', description: 'Eliminar una etiqueta', inputSchema: { type: 'object', properties: { tagPath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789/tags/111' } }, required: ['tagPath'] } },
    { name: 'revert_tag', description: 'Revertir cambios de una etiqueta en el workspace', inputSchema: { type: 'object', properties: { tagPath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789/tags/111' } }, required: ['tagPath'] } },

    // ── Triggers ──
    { name: 'list_triggers', description: 'Listar activadores de un contenedor (auto-resuelve workspace)', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' } }, required: ['containerPath'] } },
    { name: 'get_trigger', description: 'Obtener detalles de un activador', inputSchema: { type: 'object', properties: { triggerPath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789/triggers/111' } }, required: ['triggerPath'] } },
    { name: 'create_trigger', description: 'Crear un nuevo activador. Tipos: pageview, click, linkClick, formSubmission, jsError, timer, customEvent, triggerGroup, etc.', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' }, requestBody: { type: 'object', description: 'Trigger body: {name, type, filter: [{type, parameter: [...]}], customEventFilter: [...]}' } }, required: ['containerPath', 'requestBody'] } },
    { name: 'update_trigger', description: 'Actualizar un activador existente', inputSchema: { type: 'object', properties: { triggerPath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789/triggers/111' }, requestBody: { type: 'object', description: 'Campos actualizados del trigger' } }, required: ['triggerPath', 'requestBody'] } },
    { name: 'delete_trigger', description: 'Eliminar un activador', inputSchema: { type: 'object', properties: { triggerPath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789/triggers/111' } }, required: ['triggerPath'] } },
    { name: 'revert_trigger', description: 'Revertir cambios de un activador en el workspace', inputSchema: { type: 'object', properties: { triggerPath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789/triggers/111' } }, required: ['triggerPath'] } },

    // ── Variables ──
    { name: 'list_variables', description: 'Listar variables de un contenedor (auto-resuelve workspace)', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' } }, required: ['containerPath'] } },
    { name: 'get_variable', description: 'Obtener detalles de una variable', inputSchema: { type: 'object', properties: { variablePath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789/variables/111' } }, required: ['variablePath'] } },
    { name: 'create_variable', description: 'Crear una nueva variable. Tipos: v (Custom JS), jsm (Custom JS Variable), k (1st Party Cookie), u (URL), etc.', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' }, requestBody: { type: 'object', description: 'Variable body: {name, type, parameter: [{key, type, value}]}' } }, required: ['containerPath', 'requestBody'] } },
    { name: 'update_variable', description: 'Actualizar una variable existente', inputSchema: { type: 'object', properties: { variablePath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789/variables/111' }, requestBody: { type: 'object', description: 'Campos actualizados de la variable' } }, required: ['variablePath', 'requestBody'] } },
    { name: 'delete_variable', description: 'Eliminar una variable', inputSchema: { type: 'object', properties: { variablePath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789/variables/111' } }, required: ['variablePath'] } },
    { name: 'revert_variable', description: 'Revertir cambios de una variable en el workspace', inputSchema: { type: 'object', properties: { variablePath: { type: 'string', description: 'Ej: accounts/123/containers/456/workspaces/789/variables/111' } }, required: ['variablePath'] } },

    // ── Built-in Variables ──
    { name: 'list_built_in_variables', description: 'Listar variables integradas habilitadas en un contenedor', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' } }, required: ['containerPath'] } },
    { name: 'create_built_in_variable', description: 'Habilitar una variable integrada. Tipos: pageUrl, pageHostname, pagePath, referrer, event, clickElement, clickClasses, clickId, clickUrl, formElement, formClasses, formId, formUrl, etc.', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' }, type: { type: 'array', items: { type: 'string' }, description: 'Tipos de variables built-in a habilitar. Ej: ["pageUrl","clickElement"]' } }, required: ['containerPath', 'type'] } },
    { name: 'delete_built_in_variable', description: 'Deshabilitar una variable integrada', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' }, type: { type: 'array', items: { type: 'string' }, description: 'Tipos de variables built-in a deshabilitar' } }, required: ['containerPath', 'type'] } },

    // ── Versions ──
    { name: 'list_versions', description: 'Listar versiones de un contenedor (version headers)', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' } }, required: ['containerPath'] } },
    { name: 'get_version', description: 'Obtener detalles completos de una versión', inputSchema: { type: 'object', properties: { versionPath: { type: 'string', description: 'Ej: accounts/123/containers/456/versions/789' } }, required: ['versionPath'] } },
    { name: 'publish_version', description: 'Publicar una versión del contenedor', inputSchema: { type: 'object', properties: { versionPath: { type: 'string', description: 'Ej: accounts/123/containers/456/versions/789' } }, required: ['versionPath'] } },
    { name: 'set_latest_version', description: 'Establecer una versión como la más reciente', inputSchema: { type: 'object', properties: { versionPath: { type: 'string', description: 'Ej: accounts/123/containers/456/versions/789' } }, required: ['versionPath'] } },
    { name: 'update_version', description: 'Actualizar metadatos de una versión (nombre, notas)', inputSchema: { type: 'object', properties: { versionPath: { type: 'string', description: 'Ej: accounts/123/containers/456/versions/789' }, requestBody: { type: 'object', description: 'Campos a actualizar: {name, notes}' } }, required: ['versionPath', 'requestBody'] } },

    // ── Environments ──
    { name: 'list_environments', description: 'Listar entornos de un contenedor', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' } }, required: ['containerPath'] } },
    { name: 'get_environment', description: 'Obtener detalles de un entorno', inputSchema: { type: 'object', properties: { environmentPath: { type: 'string', description: 'Ej: accounts/123/containers/456/environments/1' } }, required: ['environmentPath'] } },
    { name: 'create_environment', description: 'Crear un nuevo entorno de prueba o staging', inputSchema: { type: 'object', properties: { containerPath: { type: 'string', description: 'Ej: accounts/123/containers/456' }, requestBody: { type: 'object', description: 'Environment body: {name, description, type, containerVersionId, enableBuiltInVariable, url}' } }, required: ['containerPath', 'requestBody'] } },
    { name: 'update_environment', description: 'Actualizar un entorno existente', inputSchema: { type: 'object', properties: { environmentPath: { type: 'string', description: 'Ej: accounts/123/containers/456/environments/1' }, requestBody: { type: 'object', description: 'Campos actualizados del entorno' } }, required: ['environmentPath', 'requestBody'] } },
    { name: 'delete_environment', description: 'Eliminar un entorno', inputSchema: { type: 'object', properties: { environmentPath: { type: 'string', description: 'Ej: accounts/123/containers/456/environments/1' } }, required: ['environmentPath'] } },

    // ── User Permissions ──
    { name: 'list_user_permissions', description: 'Listar permisos de usuarios de una cuenta', inputSchema: { type: 'object', properties: { accountPath: { type: 'string', description: 'Ej: accounts/123456' } }, required: ['accountPath'] } },
    { name: 'get_user_permission', description: 'Obtener permisos de un usuario específico', inputSchema: { type: 'object', properties: { permissionPath: { type: 'string', description: 'Ej: accounts/123456/user_permissions/789' } }, required: ['permissionPath'] } },
    { name: 'create_user_permission', description: 'Crear permisos para un nuevo usuario', inputSchema: { type: 'object', properties: { accountPath: { type: 'string', description: 'Ej: accounts/123456' }, requestBody: { type: 'object', description: 'Permission body: {emailAddress, accountAccess: {permission}, containerAccess: [{containerId, permission}]}' } }, required: ['accountPath', 'requestBody'] } },
    { name: 'update_user_permission', description: 'Actualizar permisos de un usuario existente', inputSchema: { type: 'object', properties: { permissionPath: { type: 'string', description: 'Ej: accounts/123456/user_permissions/789' }, requestBody: { type: 'object', description: 'Campos actualizados de permisos' } }, required: ['permissionPath', 'requestBody'] } },
    { name: 'delete_user_permission', description: 'Eliminar permisos de un usuario', inputSchema: { type: 'object', properties: { permissionPath: { type: 'string', description: 'Ej: accounts/123456/user_permissions/789' } }, required: ['permissionPath'] } },
];

// ─── Tool Handlers ──────────────────────────────────────────────
const handlers = {
    // ── Accounts ──
    async list_accounts() {
        const res = await tagmanager.accounts.list();
        return res.data.account || [];
    },
    async get_account({ accountPath }) {
        const res = await tagmanager.accounts.get({ path: accountPath });
        return res.data;
    },
    async update_account({ accountPath, requestBody }) {
        const res = await tagmanager.accounts.update({ path: accountPath, requestBody });
        return res.data;
    },

    // ── Containers ──
    async list_containers({ accountPath }) {
        const res = await tagmanager.accounts.containers.list({ parent: accountPath });
        return res.data.container || [];
    },
    async get_container({ containerPath }) {
        const res = await tagmanager.accounts.containers.get({ path: containerPath });
        return res.data;
    },
    async create_container({ accountPath, name, usageContext }) {
        const res = await tagmanager.accounts.containers.create({
            parent: accountPath,
            requestBody: { name, usageContext }
        });
        return res.data;
    },
    async update_container({ containerPath, requestBody }) {
        const res = await tagmanager.accounts.containers.update({ path: containerPath, requestBody });
        return res.data;
    },
    async delete_container({ containerPath }) {
        await tagmanager.accounts.containers.delete({ path: containerPath });
        return { success: true, message: `Contenedor ${containerPath} eliminado` };
    },
    async get_container_snippet({ containerPath }) {
        const res = await tagmanager.accounts.containers.snippet({ path: containerPath });
        return res.data;
    },

    // ── Workspaces ──
    async list_workspaces({ containerPath }) {
        const res = await tagmanager.accounts.containers.workspaces.list({ parent: containerPath });
        return res.data.workspace || [];
    },
    async get_workspace({ workspacePath }) {
        const res = await tagmanager.accounts.containers.workspaces.get({ path: workspacePath });
        return res.data;
    },
    async create_workspace({ containerPath, name, description }) {
        const body = { name };
        if (description) body.description = description;
        const res = await tagmanager.accounts.containers.workspaces.create({ parent: containerPath, requestBody: body });
        return res.data;
    },
    async delete_workspace({ workspacePath }) {
        await tagmanager.accounts.containers.workspaces.delete({ path: workspacePath });
        return { success: true, message: `Workspace ${workspacePath} eliminado` };
    },
    async sync_workspace({ workspacePath }) {
        const res = await tagmanager.accounts.containers.workspaces.sync({ path: workspacePath });
        return res.data;
    },
    async create_version({ workspacePath, name, notes }) {
        const body = { name };
        if (notes) body.notes = notes;
        const res = await tagmanager.accounts.containers.workspaces.create_version({ path: workspacePath, requestBody: body });
        return res.data;
    },
    async resolve_conflict({ workspacePath, requestBody }) {
        const res = await tagmanager.accounts.containers.workspaces.resolve_conflict({ path: workspacePath, requestBody: requestBody || {} });
        return res.data || { success: true };
    },

    // ── Tags ──
    async list_tags({ containerPath }) {
        const wsPath = await resolveWorkspacePath(containerPath);
        const tagsRes = await tagmanager.accounts.containers.workspaces.tags.list({ parent: wsPath });
        const tags = tagsRes.data.tag || [];
        // Enrich with trigger names
        const triggersRes = await tagmanager.accounts.containers.workspaces.triggers.list({ parent: wsPath });
        const triggers = triggersRes.data.trigger || [];
        return tags.map(t => {
            const triggerNames = t.firingTriggerId?.map(id =>
                triggers.find(tr => tr.triggerId === id)?.name || id
            ) || [];
            return { name: t.name, type: t.type, tagId: t.tagId, path: t.path, triggers: triggerNames, parameter: t.parameter };
        });
    },
    async get_tag({ tagPath }) {
        const res = await tagmanager.accounts.containers.workspaces.tags.get({ path: tagPath });
        return res.data;
    },
    async create_tag({ containerPath, requestBody }) {
        const wsPath = await resolveWorkspacePath(containerPath);
        const res = await tagmanager.accounts.containers.workspaces.tags.create({ parent: wsPath, requestBody });
        return res.data;
    },
    async update_tag({ tagPath, requestBody }) {
        const res = await tagmanager.accounts.containers.workspaces.tags.update({ path: tagPath, requestBody });
        return res.data;
    },
    async delete_tag({ tagPath }) {
        await tagmanager.accounts.containers.workspaces.tags.delete({ path: tagPath });
        return { success: true, message: `Tag ${tagPath} eliminado` };
    },
    async revert_tag({ tagPath }) {
        const res = await tagmanager.accounts.containers.workspaces.tags.revert({ path: tagPath });
        return res.data;
    },

    // ── Triggers ──
    async list_triggers({ containerPath }) {
        const wsPath = await resolveWorkspacePath(containerPath);
        const res = await tagmanager.accounts.containers.workspaces.triggers.list({ parent: wsPath });
        return res.data.trigger || [];
    },
    async get_trigger({ triggerPath }) {
        const res = await tagmanager.accounts.containers.workspaces.triggers.get({ path: triggerPath });
        return res.data;
    },
    async create_trigger({ containerPath, requestBody }) {
        const wsPath = await resolveWorkspacePath(containerPath);
        const res = await tagmanager.accounts.containers.workspaces.triggers.create({ parent: wsPath, requestBody });
        return res.data;
    },
    async update_trigger({ triggerPath, requestBody }) {
        const res = await tagmanager.accounts.containers.workspaces.triggers.update({ path: triggerPath, requestBody });
        return res.data;
    },
    async delete_trigger({ triggerPath }) {
        await tagmanager.accounts.containers.workspaces.triggers.delete({ path: triggerPath });
        return { success: true, message: `Trigger ${triggerPath} eliminado` };
    },
    async revert_trigger({ triggerPath }) {
        const res = await tagmanager.accounts.containers.workspaces.triggers.revert({ path: triggerPath });
        return res.data;
    },

    // ── Variables ──
    async list_variables({ containerPath }) {
        const wsPath = await resolveWorkspacePath(containerPath);
        const res = await tagmanager.accounts.containers.workspaces.variables.list({ parent: wsPath });
        return res.data.variable || [];
    },
    async get_variable({ variablePath }) {
        const res = await tagmanager.accounts.containers.workspaces.variables.get({ path: variablePath });
        return res.data;
    },
    async create_variable({ containerPath, requestBody }) {
        const wsPath = await resolveWorkspacePath(containerPath);
        const res = await tagmanager.accounts.containers.workspaces.variables.create({ parent: wsPath, requestBody });
        return res.data;
    },
    async update_variable({ variablePath, requestBody }) {
        const res = await tagmanager.accounts.containers.workspaces.variables.update({ path: variablePath, requestBody });
        return res.data;
    },
    async delete_variable({ variablePath }) {
        await tagmanager.accounts.containers.workspaces.variables.delete({ path: variablePath });
        return { success: true, message: `Variable ${variablePath} eliminada` };
    },
    async revert_variable({ variablePath }) {
        const res = await tagmanager.accounts.containers.workspaces.variables.revert({ path: variablePath });
        return res.data;
    },

    // ── Built-in Variables ──
    async list_built_in_variables({ containerPath }) {
        const wsPath = await resolveWorkspacePath(containerPath);
        const res = await tagmanager.accounts.containers.workspaces.built_in_variables.list({ parent: wsPath });
        return res.data.builtInVariable || [];
    },
    async create_built_in_variable({ containerPath, type }) {
        const wsPath = await resolveWorkspacePath(containerPath);
        const res = await tagmanager.accounts.containers.workspaces.built_in_variables.create({ parent: wsPath, type });
        return res.data;
    },
    async delete_built_in_variable({ containerPath, type }) {
        const wsPath = await resolveWorkspacePath(containerPath);
        const res = await tagmanager.accounts.containers.workspaces.built_in_variables.delete({ path: wsPath, type });
        return res.data || { success: true };
    },

    // ── Versions ──
    async list_versions({ containerPath }) {
        const res = await tagmanager.accounts.containers.version_headers.list({ parent: containerPath });
        return res.data.containerVersionHeader || [];
    },
    async get_version({ versionPath }) {
        const res = await tagmanager.accounts.containers.versions.get({ path: versionPath });
        return res.data;
    },
    async publish_version({ versionPath }) {
        const res = await tagmanager.accounts.containers.versions.publish({ path: versionPath });
        return res.data;
    },
    async set_latest_version({ versionPath }) {
        const res = await tagmanager.accounts.containers.versions.set_latest({ path: versionPath });
        return res.data;
    },
    async update_version({ versionPath, requestBody }) {
        const res = await tagmanager.accounts.containers.versions.update({ path: versionPath, requestBody });
        return res.data;
    },

    // ── Environments ──
    async list_environments({ containerPath }) {
        const res = await tagmanager.accounts.containers.environments.list({ parent: containerPath });
        return res.data.environment || [];
    },
    async get_environment({ environmentPath }) {
        const res = await tagmanager.accounts.containers.environments.get({ path: environmentPath });
        return res.data;
    },
    async create_environment({ containerPath, requestBody }) {
        const res = await tagmanager.accounts.containers.environments.create({ parent: containerPath, requestBody });
        return res.data;
    },
    async update_environment({ environmentPath, requestBody }) {
        const res = await tagmanager.accounts.containers.environments.update({ path: environmentPath, requestBody });
        return res.data;
    },
    async delete_environment({ environmentPath }) {
        await tagmanager.accounts.containers.environments.delete({ path: environmentPath });
        return { success: true, message: `Entorno ${environmentPath} eliminado` };
    },

    // ── User Permissions ──
    async list_user_permissions({ accountPath }) {
        const res = await tagmanager.accounts.user_permissions.list({ parent: accountPath });
        return res.data.userPermission || [];
    },
    async get_user_permission({ permissionPath }) {
        const res = await tagmanager.accounts.user_permissions.get({ path: permissionPath });
        return res.data;
    },
    async create_user_permission({ accountPath, requestBody }) {
        const res = await tagmanager.accounts.user_permissions.create({ parent: accountPath, requestBody });
        return res.data;
    },
    async update_user_permission({ permissionPath, requestBody }) {
        const res = await tagmanager.accounts.user_permissions.update({ path: permissionPath, requestBody });
        return res.data;
    },
    async delete_user_permission({ permissionPath }) {
        await tagmanager.accounts.user_permissions.delete({ path: permissionPath });
        return { success: true, message: `Permiso ${permissionPath} eliminado` };
    },
};

// ─── MCP JSON-RPC Interface ─────────────────────────────────────
const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: false });

function sendResponse(id, result) {
    console.log(JSON.stringify({ jsonrpc: '2.0', id, result }));
}

function sendError(id, code, message) {
    console.log(JSON.stringify({ jsonrpc: '2.0', id, error: { code, message } }));
}

rl.on('line', async (line) => {
    try {
        const req = JSON.parse(line);
        if (!req.id && req.method) return; // notification, ignore

        let res;
        switch (req.method) {
            case 'initialize':
                res = {
                    protocolVersion: '2024-11-05',
                    capabilities: { tools: {} },
                    serverInfo: { name: 'google-tag-manager-mcp', version: '2.0.0' }
                };
                break;

            case 'notifications/initialized':
                return; // no response needed

            case 'tools/list':
                res = { tools: TOOL_DEFINITIONS };
                break;

            case 'tools/call':
                const toolName = req.params?.name;
                const args = req.params?.arguments || {};
                try {
                    if (!handlers[toolName]) {
                        throw new Error(`Herramienta desconocida: ${toolName}`);
                    }
                    const result = await handlers[toolName](args);
                    res = { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
                } catch (e) {
                    const errorMsg = e.response?.data?.error?.message || e.message;
                    res = { content: [{ type: 'text', text: `Error: ${errorMsg}` }], isError: true };
                }
                break;

            default:
                sendError(req.id, -32601, `Method not found: ${req.method}`);
                return;
        }
        sendResponse(req.id, res);
    } catch (e) {
        // Malformed JSON or unexpected error — silently ignore
    }
});

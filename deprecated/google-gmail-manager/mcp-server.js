const readline = require('readline');

const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: false });

function send(id, result) {
  console.log(JSON.stringify({ jsonrpc: '2.0', id, result }));
}

rl.on('line', (line) => {
  try {
    const req = JSON.parse(line);
    if (!req.id && req.method) return;
    if (req.method === 'initialize') {
      send(req.id, {
        protocolVersion: '2024-11-05',
        capabilities: { tools: {} },
        serverInfo: { name: 'google-gmail-manager', version: '1.0.0' }
      });
    } else if (req.method === 'notifications/initialized') {
      return;
    } else if (req.method === 'tools/list') {
      send(req.id, {
        tools: [
          {
            name: 'search_emails',
            description: 'Busca correos en Gmail',
            inputSchema: { type: 'object', properties: { query: { type: 'string' }, maxResults: { type: 'number' } }, required: ['query'] }
          },
          {
            name: 'get_email_details',
            description: 'Obtiene detalles de un correo',
            inputSchema: { type: 'object', properties: { messageId: { type: 'string' } }, required: ['messageId'] }
          },
          {
            name: 'send_email',
            description: 'Envía un correo HTML o texto plano',
            inputSchema: { type: 'object', properties: { to: { type: 'string' }, subject: { type: 'string' }, body: { type: 'string' }, isHtml: { type: 'boolean' } }, required: ['to', 'body'] }
          }
        ]
      });
    } else if (req.method === 'tools/call') {
      const { google } = require('googleapis');
      const fs = require('fs');
      const path = require('path');
      const credentialsPath = path.join(__dirname, 'credentials.json');
      const tokenPath = path.join(__dirname, 'token.json');
      const credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
      const token = JSON.parse(fs.readFileSync(tokenPath, 'utf8'));
      const oauth2Client = new google.auth.OAuth2(credentials.client_id, credentials.client_secret);
      oauth2Client.setCredentials(token);
      const gmail = google.gmail({ version: 'v1', auth: oauth2Client });
      
      const args = req.params?.arguments || {};
      
      (async () => {
        try {
          let result;
          if (req.params?.name === 'search_emails') {
            const searchRes = await gmail.users.messages.list({ userId: 'me', q: args.query, maxResults: args.maxResults || 10 });
            const messages = searchRes.data.messages || [];
            const summary = [];
            for (const msg of messages) {
              const detail = await gmail.users.messages.get({ userId: 'me', id: msg.id });
              const headers = detail.data.payload.headers;
              summary.push({ id: msg.id, from: headers.find(h => h.name === 'From')?.value, to: headers.find(h => h.name === 'To')?.value, subject: headers.find(h => h.name === 'Subject')?.value, date: headers.find(h => h.name === 'Date')?.value, snippet: detail.data.snippet });
            }
            result = summary;
          } else if (req.params?.name === 'get_email_details') {
            const detail = await gmail.users.messages.get({ userId: 'me', id: args.messageId });
            result = { id: detail.data.id, snippet: detail.data.snippet, headers: detail.data.payload.headers };
          } else if (req.params?.name === 'send_email') {
            let mime = `To: ${args.to}\nSubject: ${args.subject || ''}\n`;
            if (args.isHtml) mime += `Content-Type: text/html; charset=utf-8\n`;
            mime += `\n${args.body}`;
            const raw = Buffer.from(mime).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
            const sendRes = await gmail.users.messages.send({ userId: 'me', requestBody: { raw } });
            result = { id: sendRes.data.id, status: 'sent' };
          } else {
            throw new Error('Herramienta desconocida');
          }
          console.log(JSON.stringify({ jsonrpc: '2.0', id: req.id, result: { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] } }));
        } catch (e) {
          console.log(JSON.stringify({ jsonrpc: '2.0', id: req.id, result: { content: [{ type: 'text', text: 'Error: ' + e.message }], isError: true } }));
        }
      })();
    } else {
      console.log(JSON.stringify({ jsonrpc: '2.0', id: req.id, error: { code: -32601, message: 'Method not found' } }));
    }
  } catch (e) {
    // ignore
  }
});

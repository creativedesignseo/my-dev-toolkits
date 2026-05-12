# 📨 google-apis — CLI directo a las APIs de Google

> **Tu navaja suiza para automatizar Google sin morir en el intento.**
> Conexión directa por OAuth 2.0, sin servidores MCP intermediarios, sin caídas aleatorias.

**Versión**: 1.0.0 · **Lenguaje**: Python 3.11 · **Estado**: 🟢 En producción
**Pertenece a**: [my-dev-toolkits](../README.md) — toolkits internos de Adspubli

---

## 🎯 ¿Qué resuelve esto?

Durante meses dependíamos de un **MCP de Gmail** (un conector externo) que se caía cada dos por tres con errores `403`. Cada vez que necesitábamos mandar un correo automatizado había que entrar, reconectar el MCP, y rezar. Perdíamos minutos —y a veces horas— por culpa de ese intermediario.

La solución **`google-apis/`** es montar la conexión **directamente** contra la API oficial de Google con autenticación OAuth 2.0 (Desktop Flow). El token se guarda en disco, se renueva automáticamente, y **nunca más vemos un 403**.

### Lo que ganamos vs el MCP antiguo

| Aspecto | MCP antiguo (Node.js) | Este CLI (Python) |
|---------|-----------------------|-------------------|
| Estabilidad | 🔴 Caídas cada 1-2 días | 🟢 Token auto-refresh, cero caídas |
| Adjuntos (PDFs, imágenes) | ❌ No soportaba | ✅ Sí, hasta 25 MB |
| Multi-cuenta | ❌ Una sola | ✅ N cuentas, vía `accounts.json` |
| Alias "Send as" | ❌ | ✅ `--from info@adspubli.com` |
| Búsquedas avanzadas Gmail | 🟡 Limitadas | 🟢 Sintaxis Gmail completa (`from:X has:attachment newer_than:7d`) |
| Desde cron / scripts | ❌ Solo desde clientes MCP | ✅ Cualquier shell |
| Capas que pueden fallar | 3 (Cliente → MCP server → Google) | 1 (Cliente → Google) |

---

## 🚀 Instalación

### 1. Preparar el entorno Python

```bash
cd google-apis
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

> ⚠️ Recomendamos Python **3.11** específicamente. Las versiones 3.12 y 3.14 de Homebrew (en macOS) tienen problemas con dependencias del sistema (`pyexpat`, `pip ensurepip`).

### 2. Symlink global (para llamar `gmail` desde cualquier sitio)

```bash
ln -sf "$(pwd)/bin/gmail" ~/.local/bin/gmail
# Comprueba que ~/.local/bin está en tu PATH
echo $PATH | tr ':' '\n' | grep -F "$HOME/.local/bin"
```

Después de esto, `gmail --help` debería funcionar desde cualquier carpeta.

### 3. Configurar credenciales OAuth

Necesitas un **client_secret JSON** descargado de Google Cloud Console:

1. Ve a https://console.cloud.google.com/apis/credentials
2. Selecciona (o crea) un proyecto
3. **APIs habilitadas** → habilita la **Gmail API**
4. **Credenciales** → "Crear credenciales" → "ID de cliente OAuth" → **Aplicación de escritorio**
5. Descarga el JSON
6. Guárdalo en `credentials/client_secret_<NOMBRE_PROYECTO>.json` (no se commitea, `.gitignore` lo protege)

> ⚠️ **Pantalla de consentimiento OAuth**: si el proyecto está en modo "Testing", añade tu email como **Test User** antes del primer login. Si está en "Production", no hace falta.

### 4. Mapear tu cuenta → client_secret

Edita `accounts.json` para indicar qué client_secret usar para cada email:

```json
{
  "info@one.adspubli.com":       "client_secret_adspubli.json",
  "creativedesignseo@gmail.com": "client_secret_amsip.json",

  "_default": "client_secret_adspubli.json"
}
```

### 5. Primer login (abre navegador, solo 1 vez por cuenta)

```bash
gmail login --account info@one.adspubli.com
```

Se abrirá el navegador, eliges la cuenta, autorizas los permisos, y se cierra la pestaña.
A partir de aquí, el token se guarda en `credentials/tokens/` y se refresca automáticamente.

---

## 📚 Uso

### Verificar a quién estás conectado

```bash
gmail whoami --account info@one.adspubli.com
```

### Crear un borrador (no envía, solo lo deja en Borradores)

```bash
gmail draft \
  --account info@one.adspubli.com \
  --from    info@adspubli.com \
  --to      cliente@ejemplo.com \
  --cc      jefe@ejemplo.com \
  --subject "Tu propuesta comercial" \
  --body    "Hola, te paso la propuesta adjunta."
```

### Enviar un correo directamente

```bash
gmail send \
  --account info@one.adspubli.com \
  --from    info@adspubli.com \
  --to      cliente@ejemplo.com \
  --subject "Propuesta comercial" \
  --body-file  /ruta/a/mensaje.txt \
  --html-body-file /ruta/a/mensaje.html \
  --attach  /ruta/a/propuesta.pdf
```

### Buscar correos

```bash
# Últimos 10 correos de Octavio con adjunto
gmail list \
  --account info@one.adspubli.com \
  --query   "from:octavio has:attachment" \
  --max     10
```

La sintaxis de `--query` es la misma que usas en el buscador de Gmail:
`from:X`, `to:Y`, `subject:Z`, `has:attachment`, `newer_than:7d`, `is:unread`, etc.

### Leer un hilo concreto

```bash
gmail read --account info@one.adspubli.com --thread-id 19e1c7fb510066bf
```

---

## 🏗️ Estructura interna

```
google-apis/
├── README.md             ← Este archivo
├── gmail_cli.py          ← Programa principal (~290 líneas Python)
├── accounts.json         ← Mapa cuenta → client_secret
├── requirements.txt      ← Dependencias Python
├── bin/
│   └── gmail             ← Wrapper bash (resuelve symlinks correctamente)
├── credentials/          ← (GITIGNORED — secretos aquí)
│   ├── .gitignore        ← Protege todo el contenido
│   ├── client_secret_adspubli.json   ← OAuth client del proyecto "adspubli"
│   ├── client_secret_amsip.json      ← OAuth client del proyecto "amsip-com-152005"
│   └── tokens/
│       └── info_at_one_adspubli_com.json   ← Token por cuenta
└── .venv/                ← (GITIGNORED) entorno virtual Python
```

---

## 🌍 Multi-proyecto Google Cloud

El sistema permite tener **varios proyectos Google Cloud** y elegir cuál usar para cada cuenta. Esto es útil porque:

- Cada agencia / cliente puede tener su propio proyecto GCP
- Los límites de cuota API son por proyecto
- La separación es más limpia y auditable

**Ejemplo de configuración real**:

| Cuenta | Proyecto GCP | client_secret |
|--------|--------------|---------------|
| `info@one.adspubli.com` | `adspubli` | `client_secret_adspubli.json` |
| `creativedesignseo@gmail.com` | `amsip-com-152005` | `client_secret_amsip.json` |

Añade un nuevo cliente OAuth descargando el JSON desde su proyecto GCP y registrándolo en `accounts.json`.

---

## 🔐 Seguridad

Todos los archivos sensibles están **doblemente protegidos**:

1. **`.gitignore` interno** en `credentials/`: ignora absolutamente todo excepto el propio `.gitignore`.
2. **`.gitignore` global** en la raíz del repo: patrones `**/client_secret*.json`, `**/credentials/tokens/`, `**/token*.json`, `**/.venv/`.

Para verificar que un archivo está protegido:

```bash
git check-ignore credentials/client_secret_adspubli.json
# (no imprime nada significa: SÍ está ignorado por una regla)
git check-ignore -v credentials/client_secret_adspubli.json
# Muestra qué regla lo está ignorando
```

Si por error commiteas un secreto:
1. **Revoca inmediatamente** el credencial en Google Cloud Console
2. Borra el archivo del repo y commitea
3. Para limpiarlo del histórico: `git filter-repo` (ojo, reescribe historia)

---

## 🛠️ Troubleshooting

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `gmail: command not found` | Symlink no creado o `~/.local/bin` fuera del PATH | Recrea symlink, verifica PATH |
| `Error: Symbol not found: _XML_SetAlloc...` al crear venv | Python 3.12 de Homebrew tiene `pyexpat` roto en macOS | Usa Python **3.11** |
| `❌ No client_secret mapped for X` | El email no está en `accounts.json` | Edita `accounts.json` y mapea ese email |
| `❌ Missing /credentials/client_secret_*.json` | Falta descargar el JSON de OAuth desde GCP | Descárgalo y guárdalo con el nombre que diga `accounts.json` |
| Navegador dice "Error 403: access_denied" en primer login | La cuenta no es Test User del proyecto GCP (modo "Testing") | Añádela como Test User en consent screen, o pasa el proyecto a "Production" |
| `Refresh failed` después de tiempo | Token revocado manualmente o expirado | Vuelve a hacer `gmail login --account X` |

---

---

## 📊 CLI `ga4` — Google Analytics 4

Mismo patrón que `gmail`. Funciona contra dos APIs:

- **Admin API** (`analyticsadmin v1beta`) — listar cuentas y propiedades
- **Data API** (`analyticsdata v1beta`) — reportes históricos y realtime

```bash
# Listar todas las cuentas GA accesibles
ga4 list-accounts --account creativedesignseo@gmail.com

# Listar propiedades GA4 (todas o filtrando por account-id)
ga4 list-properties --account creativedesignseo@gmail.com
ga4 list-properties --account creativedesignseo@gmail.com --account-id 244866621

# Reporte histórico (cualquier métrica + dimensión válida de GA4)
ga4 report \
  --account creativedesignseo@gmail.com \
  --property 534094689 \
  --metrics sessions,activeUsers,conversions \
  --dimensions sessionDefaultChannelGroup \
  --since 7daysAgo --until today

# Realtime (usuarios activos AHORA, últimos ~30 min)
ga4 realtime \
  --account creativedesignseo@gmail.com \
  --property 534094689 \
  --metrics activeUsers \
  --dimensions country
```

**Métricas más usadas**: `sessions`, `activeUsers`, `newUsers`, `conversions`, `engagementRate`, `screenPageViews`, `eventCount`, `averageSessionDuration`.

**Dimensiones más usadas**: `sessionDefaultChannelGroup`, `country`, `city`, `deviceCategory`, `pagePath`, `eventName`, `date`.

Referencia: [GA4 Data API metrics & dimensions](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema)

---

## 🔍 CLI `gsc` — Search Console

```bash
# Listar todos los sitios verificados desde tu cuenta
gsc list-sites --account creativedesignseo@gmail.com

# Top queries (keywords) del último mes
gsc queries \
  --account creativedesignseo@gmail.com \
  --site sc-domain:elrecolector.es \
  --since 30daysAgo --limit 25

# Top páginas
gsc pages --account creativedesignseo@gmail.com --site sc-domain:elrecolector.es --limit 10

# Posición media para palabras clave específicas
gsc positions \
  --account creativedesignseo@gmail.com \
  --site sc-domain:elrecolector.es \
  --keywords "vaciado pisos","recogida muebles barcelona"
```

**Formato del `--site`**:
- Domain property: `sc-domain:example.com` (sin protocolo)
- URL prefix: `https://www.example.com/` (con barra final)

Tienes que poner el sitio **exactamente como está registrado** en Search Console.

---

## 🗺️ Roadmap

Próximos CLIs siguiendo este mismo patrón:

- [ ] **`ads`** — Google Ads (campañas, RSAs, negativas — sustituye Playwright)
- [ ] **`drive`** — Google Drive (subir/bajar archivos)
- [ ] **`calendar`** — Google Calendar (agendar reuniones)

---

## 📖 Referencias

- [Google Identity — Installed Apps OAuth Flow](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Gmail API — Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)
- [Sintaxis de búsqueda en Gmail](https://support.google.com/mail/answer/7190)

---

📁 Volver al [README principal](../README.md)

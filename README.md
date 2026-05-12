# 🧰 My Dev Toolkits

> **Colección personal de herramientas internas de [Adspubli](https://adspubli.com)** — utilidades reutilizables para marketing digital, comercio electrónico, optimización web e inteligencia artificial.
>
> Mantenido por **Jonatan** · Última actualización: **12 de mayo de 2026**

---

## 📖 ¿Qué es este repositorio?

Es **una caja de herramientas** que vamos construyendo y reutilizando entre proyectos de Adspubli. En lugar de reinventar lo mismo en cada cliente, lo metemos aquí, lo dejamos bien documentado, y lo enchufamos donde haga falta.

Cada carpeta es **una herramienta independiente** que puede usarse por separado. Algunas son **CLIs** (programas que se ejecutan desde la terminal), otras son **servidores MCP** (los que conectan con asistentes IA como Claude o Cursor) y otras son **scripts** sueltos.

**No necesitas ser programador para entender este README** — la idea es que cualquier persona del equipo sepa qué hay disponible y para qué sirve.

---

## 🗂️ Vista rápida — qué encontrarás aquí

| 📦 Herramienta | 🎯 Para qué sirve | 🔧 Tipo | ✅ Estado |
|----------------|-------------------|---------|-----------|
| [**google-apis**](#-google-apis--cli-directo-a-las-apis-de-google) | CLI directos a Gmail, Google Analytics 4 y Search Console (sin MCPs frágiles) | CLI Python | 🟢 En producción |
| [**google-ads-manager**](#-google-ads-manager) | Servidor MCP para que la IA gestione campañas de Google Ads | MCP Node.js | 🟡 En migración |
| [**google-analytics-manager**](#-google-analytics-manager) | Servidor MCP para consultar datos de Google Analytics 4 | MCP Node.js | 🟡 En migración |
| [**google-tag-manager**](#-google-tag-manager) | Servidor MCP para configurar Google Tag Manager | MCP Node.js | 🟢 En producción |
| [**google-merchant-manager**](#-google-merchant-manager) | Servidor MCP para Google Merchant Center (catálogo de productos en Shopping) | MCP Node.js | 🟢 En producción |
| [**shopify-admin-mcp**](#-shopify-admin-mcp) | Servidor MCP para gestionar tiendas Shopify (productos, stock, etc.) | MCP Node.js | 🟢 En producción |
| [**image-optimizer**](#-image-optimizer) | Convierte imágenes pesadas (PNG/JPG) a WebP — reducción del 90-95% | Scripts Node.js | 🟢 En producción |
| [**gemini-cli-tools**](#-gemini-cli-tools) | Configuraciones y prompts para el CLI de Gemini (Google IA) | Configs | 🟡 Borrador |
| [**deprecated/**](#%EF%B8%8F-deprecated--archivado-no-usar) | Herramientas antiguas que ya no se usan, conservadas como referencia | Archivo | ⚫ No usar |

---

## 📨 Comunicación

### ⭐ google-apis — CLI directo a las APIs de Google

📁 [`google-apis/`](google-apis/) · **Versión 1.1.0** · ✅ En producción

**Qué hace en una frase**: te permite usar Gmail, **Google Analytics 4** y **Search Console** desde la terminal o desde scripts, sin pasar por los conectores MCP que se caían cada par de días.

**CLIs disponibles ahora mismo**: `gmail`, `ga4`, `gsc`.

**Por qué existe**: durante meses dependíamos de un MCP externo de Gmail que daba errores `403` constantemente — perdíamos horas reconectándolo. Aquí montamos una conexión **directa** a la API oficial de Google con OAuth 2.0, los tokens se refrescan solos y soporta cosas que el MCP no podía (adjuntos de PDFs, alias "Send as", multi-cuenta).

**Qué puedes hacer con él**:

- ✉️ Crear borradores de correo (`gmail draft ...`)
- 🚀 Enviar correos directamente, incluso con PDFs adjuntos (`gmail send ...`)
- 🔍 Buscar y leer correos (`gmail list`, `gmail read`)
- 👥 Gestionar **varias cuentas Gmail a la vez** (Adspubli, personal, clientes)
- 🏷️ Usar alias "Send as" — autenticas con `info@one.adspubli.com` pero el correo aparece como `info@adspubli.com`

**Cómo se usa** (ejemplo real):

```bash
# Enviar correo a un cliente con PDF adjunto
gmail send \
  --account info@one.adspubli.com \
  --from    info@adspubli.com \
  --to      cliente@ejemplo.com \
  --subject "Tu propuesta comercial" \
  --body-file mensaje.txt \
  --attach  propuesta.pdf
```

**Lenguaje**: Python 3.11 · **Dependencias**: `google-auth`, `googleapiclient`

📖 [Documentación completa](google-apis/README.md)

---

## 📊 Marketing y Analítica (Google)

> ⚠️ Las cuatro herramientas siguientes son **servidores MCP en Node.js** que se construyeron antes de descubrir el problema de los MCPs (caídas frecuentes). Funcionan, pero a futuro las vamos a migrar todas al modelo de `google-apis/` (Python, llamada directa). Mientras tanto, **se siguen usando**.

### 🎯 google-ads-manager

📁 [`google-ads-manager/`](google-ads-manager/) · MCP Server Node.js · 🟡 En migración

**Qué hace**: deja que una IA como Claude o Cursor lea y modifique tus campañas de Google Ads (listar campañas, ver métricas, explorar grupos de anuncios y palabras clave).

**Para qué lo usamos en Adspubli**: leer resúmenes de cuentas, métricas (clics, impresiones, coste, CTR) y rendimiento de palabras clave.

**Estado real**: funciona, pero la creación/edición de anuncios se hace con Playwright porque el MCP no llega a todo. Se sustituirá por `ads` CLI dentro de `google-apis/`.

📖 [Documentación interna](google-ads-manager/README.md)

---

### 📈 google-analytics-manager

📁 [`google-analytics-manager/`](google-analytics-manager/) · MCP Server Node.js · 🟡 En migración

**Qué hace**: conecta con Google Analytics 4 para pedir reportes (sesiones, conversiones, usuarios activos en tiempo real).

**Para qué lo usamos en Adspubli**: reportes semanales automáticos para clientes, debugging de eventos de conversión, lectura de propiedades GA4.

📖 [Documentación interna](google-analytics-manager/README.md)

---

### 🏷️ google-tag-manager

📁 [`google-tag-manager/`](google-tag-manager/) · MCP Server Node.js v2.0.0 · 🟢 En producción

**Qué hace**: gestiona **Google Tag Manager** desde la IA — 46 herramientas que cubren cuentas, contenedores, workspaces, etiquetas (tags), disparadores (triggers), variables, versiones y publicación.

**Para qué lo usamos en Adspubli**: instalación rápida de GA4, configuración de eventos, publicación de cambios sin entrar al panel.

📖 [Documentación interna](google-tag-manager/README.md)

---

### 🛍️ google-merchant-manager

📁 [`google-merchant-manager/`](google-merchant-manager/) · MCP Server Node.js · 🟢 En producción

**Qué hace**: conecta con **Google Merchant Center** (el catálogo de productos que aparece en Google Shopping). Permite listar el inventario activo y consultar productos individuales.

**Para qué lo usamos en Adspubli**: auditar feeds de productos de clientes e-commerce, detectar errores rápidos.

📖 Documentación: pendiente (TODO)

---

## 🛒 E-commerce

### 🛒 shopify-admin-mcp

📁 [`shopify-admin-mcp/`](shopify-admin-mcp/) · MCP Server TypeScript · 🟢 En producción

**Qué hace**: deja que una IA gestione tiendas Shopify a través de su Admin GraphQL API — buscar productos, crearlos con variantes, actualizar stock, operaciones masivas.

**Para qué lo usamos en Adspubli**: migración de productos entre tiendas, ajustes masivos de inventario, automatización de tareas repetitivas para clientes e-commerce.

**Lenguaje**: TypeScript (compila a JavaScript)

📖 [Documentación interna](shopify-admin-mcp/README.md)

---

## 🖼️ Multimedia

### 🖼️ image-optimizer

📁 [`image-optimizer/`](image-optimizer/) · **Versión 1.0.0** · 🟢 En producción

**Qué hace en una frase**: convierte tus imágenes pesadas (PNG, JPG) al formato moderno **WebP**, haciéndolas hasta **96% más ligeras sin pérdida visible de calidad**.

**Por qué importa**: una web rápida posiciona mejor en Google y convierte más visitantes en clientes. Imágenes grandes son la causa #1 de webs lentas.

**Resultados reales** (en el proyecto BaLo Restaurant):

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| Tamaño total | 37 MB | 1.5 MB | **96 %** ⚡ |
| Carga (4G) | 30 s | 1.2 s | **96 %** ⚡ |
| Calidad | 100 % | 99.9 % | Imperceptible |

**Funciones**:
- 🔄 Conversión automática PNG/JPG → WebP
- 🧹 Limpieza de duplicados
- ⚡ 100 % local (no sube nada a la nube — privacidad total)
- 🆓 Gratis y reutilizable en cualquier proyecto

📖 [Documentación interna](image-optimizer/README.md)

---

## 🤖 Inteligencia Artificial

### 🤖 gemini-cli-tools

📁 [`gemini-cli-tools/`](gemini-cli-tools/) · 🟡 Borrador

**Qué hace**: directorio con configuraciones, prompts y extensiones para el **Gemini CLI** de Google (el "Claude Code" de Google).

**Estado**: muy preliminar — solo la estructura, sin contenido. Se irá rellenando.

📖 [Documentación interna](gemini-cli-tools/README.md)

---

## ⚰️ deprecated/ — archivado, NO usar

📁 [`deprecated/`](deprecated/)

Aquí guardamos las herramientas **antiguas que ya no se usan** pero conservamos como referencia histórica (por si alguna vez necesitamos consultar cómo estaba hecho algo).

**Contenido actual**:

| Carpeta | Por qué se deprecó | Sustituida por |
|---------|--------------------|-----------------|
| `google-gmail-manager/` | Servidor MCP Gmail en Node.js que daba errores 403 constantes | `google-apis/` (CLI `gmail`) |
| `gmail-mcp/` | Wrapper sobre `@shinzolabs/gmail-mcp` — mismos problemas | `google-apis/` (CLI `gmail`) |

❗ **No instalar ni usar nada de aquí.** Si necesitas funcionalidad Gmail, usa el CLI `gmail` del paquete `google-apis/`.

---

## 🚀 Cómo empezar

### Si solo quieres echar un vistazo

```bash
git clone https://github.com/creativedesignseo/my-dev-toolkits.git
cd my-dev-toolkits
```

Cada carpeta tiene su propio `README.md` con instrucciones específicas.

### Si quieres usar el CLI `gmail` (recomendado para enviar correos)

```bash
cd google-apis
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Symlink global
ln -sf "$(pwd)/bin/gmail" ~/.local/bin/gmail

# Primer login (abre navegador)
gmail login --account tu-cuenta@gmail.com
```

A partir de ahí, ya puedes mandar correos desde cualquier sitio:

```bash
gmail send --account tu-cuenta@gmail.com \
  --to alguien@ejemplo.com \
  --subject "Hola" \
  --body "Mi primer correo desde el CLI"
```

📖 Detalle completo en [`google-apis/README.md`](google-apis/README.md).

### Si quieres conectar un MCP a Claude / Cursor / Antigravity

Cada carpeta `*-manager` o `*-mcp` tiene su propio README con la configuración del bloque `mcp_config.json` que necesitas pegar en tu cliente MCP. Consulta el README específico.

---

## 🔐 Seguridad — credenciales

> ⚠️ **Lectura obligatoria si vas a tocar cualquier herramienta que use Google APIs.**

- **Nunca** subas archivos `client_secret_*.json`, `credentials.json`, `token.json`, `*.yaml` con secretos, ni `.env`. El `.gitignore` ya los protege, pero siempre verifica con `git status` antes de commitear.
- Los tokens y client secrets viven en carpetas locales que el `.gitignore` excluye:
  - `google-apis/credentials/` (gitignored entero)
  - `*/credentials.json` (cubierto por el patrón)
  - `*/token.json`, `workspace_token.json`, `refresh_token.json` (cubiertos)
  - `*.yaml` (cubierto)
- Si por error commiteas un secreto: **revoca ese credencial inmediatamente** desde la consola de Google Cloud, no basta con borrarlo del repo (el histórico de git lo conserva).
- Para verificar antes de hacer push: `git check-ignore <archivo>` te dice si está protegido.

---

## 📂 Estructura del repo

```
my-dev-toolkits/
├── README.md                    ← Este archivo (overview general)
├── CHANGELOG.md                 ← Historial de versiones
├── .gitignore                   ← Reglas de qué NO subir
│
├── google-apis/                 ⭐ CLI Python — Gmail (y futuras Google APIs)
│   ├── gmail_cli.py
│   ├── accounts.json            ← Mapa cuenta → proyecto GCP
│   ├── bin/gmail                ← Wrapper bash (symlink-able)
│   ├── credentials/             ← (gitignored — secrets aquí)
│   └── requirements.txt
│
├── google-ads-manager/          ← MCP Node.js para Google Ads
├── google-analytics-manager/    ← MCP Node.js para Analytics 4
├── google-tag-manager/          ← MCP Node.js para Tag Manager
├── google-merchant-manager/     ← MCP Node.js para Merchant Center
│
├── shopify-admin-mcp/           ← MCP TypeScript para Shopify
│
├── image-optimizer/             ← Scripts de optimización de imágenes
│
├── gemini-cli-tools/            ← Configs para Gemini CLI
│
└── deprecated/                  ⚰️ Herramientas archivadas (no usar)
    ├── google-gmail-manager/
    └── gmail-mcp/
```

---

## 📚 Glosario rápido (para los no-técnicos)

| Término | Qué es en lenguaje normal |
|---------|---------------------------|
| **CLI** | "Command Line Interface". Un programa que ejecutas desde la terminal escribiendo comandos. |
| **MCP** | "Model Context Protocol". Un estándar que deja a las IAs (Claude, Cursor, etc.) usar herramientas externas. Un "servidor MCP" es un programa que expone funciones para que la IA las llame. |
| **API** | "Application Programming Interface". Es como un "menú" oficial que los servicios (Google, Shopify, etc.) ofrecen para que otros programas se conecten a ellos. |
| **OAuth 2.0** | El método estándar para "logear" un programa en tu cuenta Google/Shopify sin compartir tu contraseña. |
| **Token / Refresh Token** | Una "llave" que tu programa guarda después de loguearse, para no tener que pedirte la contraseña cada vez. El "refresh token" se usa para renovar la llave cuando caduca. |
| **Repositorio (repo)** | Una carpeta de proyecto controlada por Git — un sistema que guarda todos los cambios históricos. |
| **Commit** | Guardar un cambio en el historial del repo (como un punto de control). |
| **Push** | Subir tus cambios al servidor remoto (GitHub). |
| **gitignore** | Lista de archivos que el repo deliberadamente NO sube (típicamente: secretos, contraseñas, builds temporales). |

---

## 🗺️ Roadmap (qué viene)

- [ ] **`ga4`** — extender `google-apis/` con CLI para Google Analytics 4
- [ ] **`gsc`** — extender `google-apis/` con CLI para Search Console
- [ ] **`ads`** — extender `google-apis/` con CLI para Google Ads (sustituye Playwright)
- [ ] **`drive`** — extender `google-apis/` con CLI para Google Drive
- [ ] **`calendar`** — extender `google-apis/` con CLI para Calendar
- [ ] Migrar los MCP de Ads/GA/Merchant/GTM a CLIs Python tipo `google-apis/`
- [ ] **SEO Toolkit** (auditorías técnicas, lighthouse batch, etc.)
- [ ] **Deployment Scripts** (deploys automáticos a Netlify, Vercel, etc.)
- [ ] **Librería de componentes UI** (cards reutilizables para landings)

---

## 🤝 Convenciones

- **Idioma**: documentación en castellano, código y nombres de variables en inglés.
- **Versionado**: [Semantic Versioning](https://semver.org/lang/es/) — `MAYOR.MENOR.PARCHE`.
- **Cambios**: cada cambio relevante se anota en [CHANGELOG.md](CHANGELOG.md).
- **Commits**: en inglés, formato [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/) (ej: `feat: ...`, `fix: ...`, `docs: ...`).
- **Branches**: trabajamos directamente sobre `main`. Para experimentos grandes, crear branch aparte.

---

## 📄 Licencia

**MIT** — uso libre en proyectos personales y comerciales.

```
Copyright (c) 2025–2026 Jonatan / Adspubli

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, subject to the standard MIT terms.
```

---

## 👤 Mantenedor

**Jonatan** · [Adspubli](https://adspubli.com)
📧 `info@adspubli.com`
🐙 [github.com/creativedesignseo](https://github.com/creativedesignseo)

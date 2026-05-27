# 🤖 Skills — Claude Code skills puras

> Esta carpeta aloja **skills puras de Claude Code** (orquestación de agentes, prompts especializados, plantillas de razonamiento). A diferencia del resto del repo (CLIs Python, MCP servers Node.js, scripts), aquí **no hay código ejecutable** — son instrucciones que Claude Code interpreta.

---

## 📖 ¿Qué es una "skill" de Claude Code?

Una skill es un paquete de instrucciones que extiende lo que Claude puede hacer de forma especializada. Vive en `~/.claude/skills/<nombre>/` (global) o en `<proyecto>/.claude/skills/<nombre>/` (proyecto). Cada skill tiene un `SKILL.md` con frontmatter YAML que define cuándo activarse.

Cuando un usuario escribe algo que coincide con la `description` de la skill, Claude la activa automáticamente. También se pueden invocar explícitamente con `/<nombre-skill>`.

---

## 🗂️ Skills disponibles en este repo

| Skill | Para qué sirve | Estado | Comando |
|---|---|---|---|
| [**saas-audit**](./saas-audit/) | Auditoría production-readiness de SaaS con 13 agentes en paralelo. Score 0-100, hallazgos P0-P3, roadmap por fases. | 🟢 v0.1.0 | `/saas-audit` |

> **Nota**: las skills `shopify-admin` y `google-apis` (que también tienen `SKILL.md`) viven junto a su CLI correspondiente (`shopify-admin-cli/SKILL.md` y `google-apis/`) porque son consustanciales a la herramienta CLI. Aquí en `skills/` viven solo skills que **no acompañan a un CLI** — son skills "puras" de orquestación o auditoría.

---

## 📦 Instalación

### Una skill específica

```bash
npx skills add creativedesignseo/my-dev-toolkits --skill saas-audit -g
```

### Todas las skills del repo

```bash
npx skills add creativedesignseo/my-dev-toolkits --all -g
```

El flag `-g` instala globalmente (`~/.claude/skills/`). Quita el `-g` para instalar solo en el proyecto actual.

---

## 🛠️ Estructura de cada skill

```
skills/<nombre>/
├── SKILL.md           # Frontmatter + instrucciones principales (obligatorio)
├── README.md          # Documentación pública (para GitHub/skills.sh)
├── prompts/           # Prompts de sub-agentes (si la skill orquesta agentes)
├── helpers/           # Algoritmos, plantillas, heurísticas
└── examples/          # Ejemplos de uso (anonimizados si aplica)
```

---

## 🚀 Añadir una nueva skill

1. Crear `skills/<nombre>/` con su `SKILL.md` y frontmatter válido (`name`, `description`).
2. Añadir entrada a la tabla "Skills disponibles" arriba.
3. Actualizar la sección "🤖 Skills" del README maestro del repo.
4. Actualizar `CHANGELOG.md` con el versionado.

Para skills muy complejas (10+ archivos), consulta como referencia [`saas-audit/`](./saas-audit/).

---

## 🔗 Referencias útiles

- [Skills.sh](https://skills.sh/) — Directorio público de skills
- [Vercel-labs/skills CLI](https://github.com/vercel-labs/skills) — CLI oficial
- [Anthropics/skills](https://github.com/anthropics/skills) — Skills oficiales de Anthropic
- [Obra/superpowers](https://github.com/obra/superpowers) — Framework de skills agentic más popular (~200K stars)

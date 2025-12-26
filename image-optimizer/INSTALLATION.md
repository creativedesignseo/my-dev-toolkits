# 📦 Guía de Instalación - Image Optimizer Toolkit

## 🎯 Instalación Rápida (5 minutos)

### Paso 1: Copiar el toolkit

```bash
# Opción A: Copiar carpeta completa
cp -r image-optimizer-toolkit/ tu-proyecto/toolkit/

# Opción B: Copiar solo scripts
cp -r image-optimizer-toolkit/scripts/ tu-proyecto/scripts/
```

### Paso 2: Instalar dependencias

```bash
cd tu-proyecto
npm install --save-dev sharp vite-plugin-image-optimizer vite-imagetools
```

### Paso 3: Configurar package.json

Agrega estos scripts a tu `package.json`:

```json
{
  "scripts": {
    "convert-to-webp": "node scripts/convert-to-webp.js",
    "optimize-images": "node scripts/optimize-images.js"
  }
}
```

### Paso 4: Configurar Vite

Actualiza tu `vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { ViteImageOptimizer } from 'vite-plugin-image-optimizer'
import { imagetools } from 'vite-imagetools'

export default defineConfig({
  plugins: [
    react(),
    
    imagetools({
      defaultDirectives: (url) => {
        return new URLSearchParams({
          format: 'webp',
          quality: '85',
          w: '1920',
        })
      },
    }),
    
    ViteImageOptimizer({
      png: { quality: 80 },
      jpeg: { quality: 85 },
      webp: { quality: 85, lossless: false },
      cache: true,
    }),
  ],
})
```

### Paso 5: Probar

```bash
# Agregar imagen de prueba
cp test-image.png src/assets/

# Convertir
npm run convert-to-webp

# ¡Listo! ✅
```

---

## 🔧 Instalación Detallada

### Para proyectos React + Vite

```bash
# 1. Verificar que tienes Vite
npm list vite

# 2. Copiar scripts
mkdir -p scripts
cp image-optimizer-toolkit/scripts/* scripts/

# 3. Instalar dependencias
npm install --save-dev \
  sharp@^0.33.0 \
  vite-plugin-image-optimizer@^1.1.8 \
  vite-imagetools@^7.0.4

# 4. Configurar (ver Paso 4 arriba)

# 5. Verificar instalación
npm run convert-to-webp -- --help
```

### Para proyectos Next.js

```bash
# 1. Copiar scripts
cp -r image-optimizer-toolkit/scripts/ .

# 2. Instalar sharp
npm install --save-dev sharp

# 3. Agregar scripts a package.json
{
  "scripts": {
    "convert-to-webp": "node scripts/convert-to-webp.js"
  }
}

# 4. Usar manualmente (Next.js ya optimiza imágenes)
npm run convert-to-webp
```

### Para proyectos Vue + Vite

```bash
# Igual que React + Vite
# Solo cambia el plugin principal:

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { imageOptimizationPlugins } from './toolkit/vite.config.template'

export default defineConfig({
  plugins: [
    vue(),
    ...imageOptimizationPlugins,
  ],
})
```

---

## 📋 Checklist de Instalación

- [ ] Toolkit copiado a tu proyecto
- [ ] Dependencias instaladas (`sharp`, `vite-plugin-image-optimizer`, `vite-imagetools`)
- [ ] Scripts agregados a `package.json`
- [ ] `vite.config.ts` configurado
- [ ] Probado con imagen de prueba
- [ ] Build de producción exitoso

---

## 🐛 Troubleshooting

### Error: "Cannot find module 'sharp'"

```bash
# Solución:
npm install sharp --save-dev

# Si persiste:
npm rebuild sharp
```

### Error: "vite-plugin-image-optimizer not found"

```bash
# Solución:
npm install vite-plugin-image-optimizer vite-imagetools --save-dev
```

### Error: "Permission denied"

```bash
# En Windows (PowerShell como Admin):
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# En Mac/Linux:
chmod +x scripts/convert-to-webp.js
```

### Build muy lento

```bash
# La primera vez es normal (optimiza todas las imágenes)
# Las siguientes veces usa caché y es rápido

# Para limpiar caché:
rm -rf node_modules/.cache/vite-plugin-image-optimizer
```

---

## 🎓 Proyectos de Ejemplo

### Proyecto nuevo desde cero

```bash
# 1. Crear proyecto Vite
npm create vite@latest mi-proyecto -- --template react-ts

# 2. Entrar al proyecto
cd mi-proyecto

# 3. Copiar toolkit
cp -r ../image-optimizer-toolkit/scripts/ scripts/

# 4. Instalar dependencias
npm install
npm install --save-dev sharp vite-plugin-image-optimizer vite-imagetools

# 5. Configurar (ver pasos arriba)

# 6. ¡Listo!
```

### Proyecto existente

```bash
# 1. Ir a tu proyecto
cd mi-proyecto-existente

# 2. Copiar scripts
cp -r ../image-optimizer-toolkit/scripts/ scripts/

# 3. Instalar dependencias
npm install --save-dev sharp vite-plugin-image-optimizer vite-imagetools

# 4. Configurar vite.config.ts

# 5. Convertir imágenes existentes
npm run convert-to-webp

# 6. Verificar build
npm run build
```

---

## 📊 Verificación de Instalación

### Test básico

```bash
# 1. Crear imagen de prueba
echo "test" > src/assets/test.png

# 2. Ejecutar conversión
npm run convert-to-webp

# 3. Verificar resultado
ls -lh src/assets/test.webp

# 4. Limpiar
rm src/assets/test.png src/assets/test.webp
```

### Test completo

```bash
# 1. Agregar imagen real (5-10 MB)
cp ~/Downloads/foto.png src/assets/

# 2. Convertir
npm run convert-to-webp

# 3. Verificar ahorro
# Debería mostrar ~90-95% de reducción

# 4. Build de producción
npm run build

# 5. Verificar dist/assets/
ls -lh dist/assets/*.webp
```

---

## 🎉 ¡Instalación Completada!

Si llegaste aquí, tu toolkit está listo para usar.

### Próximos pasos:

1. ✅ Agregar imágenes a `src/assets/`
2. ✅ Ejecutar `npm run convert-to-webp`
3. ✅ Importar WebP en tu código
4. ✅ Build y deploy

### Recursos:

- [README.md](./README.md) - Documentación principal
- [USAGE.md](./USAGE.md) - Guía de uso
- [FAQ.md](./FAQ.md) - Preguntas frecuentes

---

**¿Problemas?** Revisa la sección de Troubleshooting o crea un issue.

**¿Funciona?** ¡Genial! Ahora optimiza todas tus imágenes 🚀

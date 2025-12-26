# 🚀 Guía de Uso - Image Optimizer Toolkit

## 📸 Uso Básico

### Convertir imágenes nuevas

```bash
npm run convert-to-webp
```

**Resultado:**
```
🎨 WebP Conversion Script
================================

Found 3 PNG/JPG images

📸 Converting: hero-image.png
   Original size: 10 MB
   ✅ WebP created: 800 KB
   💰 Saved: 9.2 MB (92%)

⏭️  Skipping: logo.png
   WebP version already exists

⏭️  Skipping: background.png
   WebP version already exists

================================
📊 CONVERSION SUMMARY
================================
✅ Converted: 1 image
⏭️  Skipped: 2 images (already have WebP)
```

---

## 🎯 Comandos Disponibles

### Modo normal (solo nuevas)
```bash
npm run convert-to-webp
```
- Detecta automáticamente imágenes sin WebP
- Solo procesa las nuevas
- Rápido y eficiente

### Modo forzado (reconvertir todas)
```bash
npm run convert-to-webp -- --force
```
- Reconvierte TODAS las imágenes
- Útil si cambias configuración de calidad
- Más lento

### Eliminar originales
```bash
npm run convert-to-webp -- --delete-originals
```
- Convierte a WebP
- Elimina PNG/JPG originales
- ⚠️ Usa con precaución

### Combinar opciones
```bash
npm run convert-to-webp -- --force --delete-originals
```

---

## 📋 Flujo de Trabajo Completo

### 1. Recibir imagen del diseñador

```bash
# Diseñador te envía: producto-hero.png (15 MB)
```

### 2. Guardar en assets

```bash
cp ~/Downloads/producto-hero.png src/assets/
```

### 3. Convertir a WebP

```bash
npm run convert-to-webp
```

**Salida:**
```
📸 Converting: producto-hero.png
   Original size: 15 MB
   ✅ WebP created: 1.2 MB
   💰 Saved: 13.8 MB (92%)
```

### 4. Importar en código

```tsx
// src/components/Hero.tsx
import productoHero from '../assets/producto-hero.webp';

export function Hero() {
  return (
    <div className="hero">
      <img 
        src={productoHero} 
        alt="Producto Hero"
        loading="lazy"
      />
    </div>
  );
}
```

### 5. Build y deploy

```bash
npm run build
# Deploy automático a Netlify/Vercel
```

---

## 🎨 Casos de Uso

### Caso 1: Sitio de restaurante

```bash
# Imágenes: platos, ambiente, chef
src/assets/
├── plato-1.png (8 MB) → plato-1.webp (650 KB)
├── plato-2.png (7 MB) → plato-2.webp (580 KB)
├── ambiente.png (12 MB) → ambiente.webp (950 KB)
└── chef.png (5 MB) → chef.webp (400 KB)

# Total: 32 MB → 2.58 MB (92% ahorro)
```

### Caso 2: E-commerce

```bash
# Imágenes: productos
src/assets/products/
├── producto-1.jpg (3 MB) → producto-1.webp (240 KB)
├── producto-2.jpg (3.5 MB) → producto-2.webp (280 KB)
├── producto-3.jpg (4 MB) → producto-3.webp (320 KB)
└── ... (50 productos)

# Total: 175 MB → 14 MB (92% ahorro)
```

### Caso 3: Portfolio de fotografía

```bash
# Imágenes: fotos de alta calidad
# Ajustar calidad a 90% para mejor resultado

# scripts/convert-to-webp.js
const WEBP_CONFIG = {
  quality: 90,  // Mayor calidad
  effort: 6,
};

# Resultado: 100 MB → 12 MB (88% ahorro)
# Calidad visual: Prácticamente idéntica
```

---

## 🔧 Personalización

### Cambiar calidad de conversión

Edita `scripts/convert-to-webp.js`:

```javascript
// Línea 27-31
const WEBP_CONFIG = {
  quality: 85,  // Cambiar este valor (0-100)
  effort: 6,    // Esfuerzo de compresión (0-6)
  lossless: false,
};
```

**Recomendaciones:**
- **75-80**: Máxima compresión (iconos, gráficos)
- **85**: Balance óptimo (recomendado)
- **90-95**: Alta calidad (fotografía profesional)

### Cambiar tamaño máximo

Edita `vite.config.ts`:

```typescript
imagetools({
  defaultDirectives: (url) => {
    return new URLSearchParams({
      format: 'webp',
      quality: '85',
      w: '2560',  // Cambiar ancho máximo
    })
  },
}),
```

---

## 📊 Monitoreo de Resultados

### Ver estadísticas de conversión

```bash
npm run convert-to-webp
```

**Salida detallada:**
```
================================
📊 CONVERSION SUMMARY
================================
✅ Converted: 5 images
Total original size: 45 MB
Total WebP size: 3.6 MB
Total saved: 41.4 MB (92%)

⏭️  Skipped: 3 images (already have WebP)
```

### Verificar tamaños

```bash
# Ver todas las imágenes WebP
ls -lh src/assets/*.webp

# Comparar con originales
ls -lh src/assets/*.png
```

### Verificar en build

```bash
npm run build

# Ver imágenes optimizadas en dist
ls -lh dist/assets/*.webp
```

---

## 💡 Tips y Mejores Prácticas

### 1. Mantener PNG originales (recomendado)

```bash
# NO uses --delete-originals durante desarrollo
npm run convert-to-webp

# Mantén PNG como backup
# Solo elimina en producción final si es necesario
```

### 2. Usar lazy loading

```tsx
<img 
  src={imagen} 
  alt="..." 
  loading="lazy"  // ← Carga solo cuando sea visible
/>
```

### 3. Responsive images (opcional)

```tsx
<picture>
  <source 
    srcSet={imagenMobile} 
    media="(max-width: 768px)" 
  />
  <source 
    srcSet={imagenDesktop} 
    media="(min-width: 769px)" 
  />
  <img src={imagenDesktop} alt="..." />
</picture>
```

### 4. Nombres descriptivos

```bash
# ❌ Mal
imagen1.png
foto.png
img.png

# ✅ Bien
hero-restaurant.png
plato-principal-salmon.png
chef-portrait.png
```

### 5. Organizar por carpetas

```bash
src/assets/
├── hero/
│   ├── hero-desktop.webp
│   └── hero-mobile.webp
├── products/
│   ├── product-1.webp
│   └── product-2.webp
└── team/
    ├── chef-1.webp
    └── chef-2.webp
```

---

## 🐛 Solución de Problemas

### Imagen no se convierte

```bash
# Verificar que es PNG o JPG
file src/assets/imagen.png

# Verificar permisos
ls -l src/assets/imagen.png

# Intentar forzar
npm run convert-to-webp -- --force
```

### Calidad muy baja

```javascript
// Aumentar calidad en scripts/convert-to-webp.js
const WEBP_CONFIG = {
  quality: 90,  // Aumentar de 85 a 90
  effort: 6,
};
```

### Build muy lento

```bash
# Limpiar caché
rm -rf node_modules/.cache/vite-plugin-image-optimizer

# Rebuild
npm run build
```

---

## 📚 Recursos Adicionales

- [README.md](./README.md) - Documentación principal
- [INSTALLATION.md](./INSTALLATION.md) - Guía de instalación
- [FAQ.md](./FAQ.md) - Preguntas frecuentes

---

**¿Dudas?** Revisa el FAQ o experimenta con diferentes configuraciones.

**¿Funciona bien?** ¡Genial! Ahora optimiza todas tus imágenes 🚀

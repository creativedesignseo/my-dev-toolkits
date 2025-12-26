import { defineConfig } from 'vite'
import { ViteImageOptimizer } from 'vite-plugin-image-optimizer'
import { imagetools } from 'vite-imagetools'

/**
 * Configuración de optimización de imágenes para Vite
 * 
 * Copia esta configuración a tu vite.config.ts y ajusta según necesites.
 * 
 * Uso:
 * 1. Importa estos plugins en tu vite.config.ts
 * 2. Agrega los plugins al array de plugins
 * 3. Ajusta la calidad si es necesario (80-90 recomendado)
 */

export const imageOptimizationPlugins = [
  // Conversión automática a WebP
  imagetools({
    defaultDirectives: (url) => {
      return new URLSearchParams({
        format: 'webp',
        quality: '85',
        w: '1920', // Max width for desktop
      })
    },
  }),
  
  // Optimización adicional durante el build
  ViteImageOptimizer({
    // PNG optimization (fallback for browsers that don't support WebP)
    png: {
      quality: 80,
    },
    // JPEG optimization
    jpeg: {
      quality: 85,
    },
    jpg: {
      quality: 85,
    },
    // WebP optimization
    webp: {
      quality: 85,
      lossless: false,
    },
    // Cache optimized images
    cache: true,
    cacheLocation: './node_modules/.cache/vite-plugin-image-optimizer',
  }),
];

// Ejemplo de uso en tu vite.config.ts:
/*
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { imageOptimizationPlugins } from './image-optimizer-toolkit/vite.config.template'

export default defineConfig({
  plugins: [
    react(),
    ...imageOptimizationPlugins,
  ],
})
*/

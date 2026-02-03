
import sharp from 'sharp';
import { promises as fs } from 'fs';
import { watch } from 'fs';
import { join, parse, dirname } from 'path';
import { fileURLToPath } from 'url';

// ==========================================
// 🏭 FÁBRICA DE ASSETS DE IMAGEN (GENERATOR)
// ==========================================
// Este script toma imágenes originales ("raw") y genera 
// automáticamente variantes optimizadas (WebP) y redimensionadas 
// según los perfiles definidos abajo.

// --- CONFIGURACIÓN DE RUTAS ---
// Ajusta estas rutas según la estructura de tu proyecto si es necesario.
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Por defecto asume que se ejecuta desde la raíz del proyecto o toolkit
// RAW: Donde pones las fotos originales (jpg, png, avif)
// OPTIMIZED: Donde el script guardará las versiones webp generadas
const RAW_DIR = join(__dirname, '../src/assets/raw'); 
const OUTPUT_DIR = join(__dirname, '../public/img/optimized');

// --- ⚙️ PERFILES DE GENERACIÓN ---
// Define aquí tus moldes. El script generará una imagen por cada perfil.
const PERFILES = {
  // Ej: Para tarjetas en la Home (334x250, fill crop)
  'card': { 
    width: 334, 
    height: 250, 
    fit: 'cover', 
    position: 'attention', // 'attention' busca el foco interesante, 'center' es default
    quality: 85 
  },

  // Ej: Para cabeceras grandes (Hero sections)
  'hero': { 
    width: 1920, 
    height: 800, 
    fit: 'cover', 
    position: 'center', 
    quality: 80 
  },

  // Ej: Miniaturas cuadradas
  'thumb': { 
    width: 150, 
    height: 150, 
    fit: 'cover', 
    position: 'center', 
    quality: 80 
  },
  
  // Ej: Versión vertical para móviles
  'mobile': { 
    width: 600, 
    height: 800, 
    fit: 'cover', 
    position: 'attention', 
    quality: 80 
  }
};

// --- SOPORTE DE ARCHIVOS ---
const SUPPORTED_EXT = /\.(jpg|jpeg|png|webp|avif)$/i;

// --- UTILS ---
async function ensureDir(dir) {
  try {
    await fs.access(dir);
  } catch {
    console.log(`📁 Creando directorio: ${dir}`);
    await fs.mkdir(dir, { recursive: true });
  }
}

async function processSingleFile(filename) {
  if (!SUPPORTED_EXT.test(filename)) return;

  const { name } = parse(filename);
  const inputPath = join(RAW_DIR, filename);

  try {
    // Verificar si el archivo original aún existe (puede haber sido borrado)
    let inputStats;
    try {
      inputStats = await fs.stat(inputPath);
    } catch (err) {
      if (err.code === 'ENOENT') {
        console.log(`🗑️  Original borrado: ${filename} -> Limpiando versiones optimizadas...`);
        // Borrar versiones generadas
        for (const profileName of Object.keys(PERFILES)) {
           const outputPath = join(OUTPUT_DIR, `${name}-${profileName}.webp`);
           try {
             await fs.unlink(outputPath);
             console.log(`   ❌ Borrado: ${name}-${profileName}.webp`);
           } catch (e) { /* ignore */ }
        }
        return;
      }
      throw err;
    }

    // Lógica de Caché Inteligente
    let needsProcessing = false;
    for (const profileName of Object.keys(PERFILES)) {
        const outputFilename = `${name}-${profileName}.webp`;
        const outputPath = join(OUTPUT_DIR, outputFilename);
        try {
            const outputStats = await fs.stat(outputPath);
            // Si el original es más nuevo que el generado, hay que actualizar
            if (inputStats.mtimeMs > outputStats.mtimeMs) {
                needsProcessing = true;
                break;
            }
        } catch (e) {
            // El archivo generado no existe
            needsProcessing = true;
            break;
        }
    }

    if (!needsProcessing) {
       // Opcional: Descomentar para ver logs de "saltado"
       // console.log(`⏭️  Salto: ${filename} (ya está actualizado)`);
       return;
    }

    console.log(`⚡ Procesando: ${filename} ...`);

    // Procesar para cada perfil
    for (const [profileName, config] of Object.entries(PERFILES)) {
      const outputFilename = `${name}-${profileName}.webp`;
      const outputPath = join(OUTPUT_DIR, outputFilename);

      await sharp(inputPath)
        .resize({
            width: config.width,
            height: config.height,
            fit: config.fit,
            position: config.position === 'attention' ? sharp.strategy.attention : config.position
        })
        .webp({ quality: config.quality })
        .toFile(outputPath);
    }
    console.log(`   ✅ Generadas ${Object.keys(PERFILES).length} variantes.`);

  } catch (error) {
    console.error(`❌ Error procesando ${filename}:`, error.message);
  }
}

async function processAll() {
  console.log('🏭 Escaneando imágenes en raw/ ...');
  try {
    const files = await fs.readdir(RAW_DIR);
    if (files.length === 0) {
      console.log('⚠️  Carpeta vacía. Añade imágenes .jpg, .png o .avif aquí.');
    }
    for (const file of files) {
      await processSingleFile(file);
    }
    console.log('✨ Ciclo de escaneo completado.\n');
  } catch (err) {
    if (err.code === 'ENOENT') {
        console.error(`❌ Error: No existe el directorio de origen: ${RAW_DIR}`);
        console.error('   Créalo y pon tus imágenes ahí.');
    } else {
        console.error(err);
    }
  }
}

async function main() {
  await ensureDir(RAW_DIR);
  await ensureDir(OUTPUT_DIR);

  const isWatchMode = process.argv.includes('--watch');

  if (isWatchMode) {
    console.log('👀 MODO ESCUCHA ACTIVADO (Watch Mode)');
    console.log(`   📂 Origen: ${RAW_DIR}`);
    console.log(`   📂 Destino: ${OUTPUT_DIR}`);
    console.log('   -> Arrastra imágenes para procesar. Borra para limpiar.');
    console.log('   -> Presiona CTRL+C para salir.\n');

    await processAll(); // Procesar lo existente primero

    // Debounce simple para evitar múltiples eventos por un solo archivo
    let debounceTimer = null;
    watch(RAW_DIR, (eventType, filename) => {
      if (!filename) return;
      if (debounceTimer) clearTimeout(debounceTimer);
      
      debounceTimer = setTimeout(() => {
        processSingleFile(filename);
      }, 300); 
    });

  } else {
    // Modo ejecución única
    await processAll();
    console.log('💡 Tip: Usa "npm run generate-assets -- --watch" para modo automático.');
  }
}

main();

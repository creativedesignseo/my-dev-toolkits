#!/usr/bin/env node

/**
 * Manual Image Optimization Script
 * 
 * This script optimizes all images in src/assets using Sharp.
 * It creates WebP versions and compresses PNG files.
 * 
 * Usage: npm run optimize-images
 */

import sharp from 'sharp';
import { readdir, stat, mkdir } from 'fs/promises';
import { join, extname, basename } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const ASSETS_DIR = join(__dirname, '../src/assets');
const OUTPUT_DIR = join(__dirname, '../src/assets/optimized');

// Supported image formats
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg'];

// Optimization settings
const OPTIMIZATION_CONFIG = {
  png: {
    quality: 80,
    compressionLevel: 9,
  },
  jpeg: {
    quality: 85,
    progressive: true,
  },
  webp: {
    quality: 85,
    effort: 6,
  },
};

/**
 * Format bytes to human-readable size
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Get all image files in a directory
 */
async function getImageFiles(dir) {
  const files = await readdir(dir);
  const imageFiles = [];

  for (const file of files) {
    const filePath = join(dir, file);
    const stats = await stat(filePath);

    if (stats.isFile() && IMAGE_EXTENSIONS.includes(extname(file).toLowerCase())) {
      imageFiles.push(filePath);
    }
  }

  return imageFiles;
}

/**
 * Optimize a single image
 */
async function optimizeImage(inputPath) {
  const ext = extname(inputPath).toLowerCase();
  const name = basename(inputPath, ext);
  
  // Get original file size
  const originalStats = await stat(inputPath);
  const originalSize = originalStats.size;

  console.log(`\n📸 Processing: ${basename(inputPath)}`);
  console.log(`   Original size: ${formatBytes(originalSize)}`);

  let totalSaved = 0;

  try {
    // Create optimized directory if it doesn't exist
    await mkdir(OUTPUT_DIR, { recursive: true });

    // 1. Create optimized PNG/JPEG
    const optimizedPath = join(OUTPUT_DIR, `${name}${ext}`);
    
    if (ext === '.png') {
      await sharp(inputPath)
        .png(OPTIMIZATION_CONFIG.png)
        .toFile(optimizedPath);
    } else {
      await sharp(inputPath)
        .jpeg(OPTIMIZATION_CONFIG.jpeg)
        .toFile(optimizedPath);
    }

    const optimizedStats = await stat(optimizedPath);
    const optimizedSize = optimizedStats.size;
    const savedPng = originalSize - optimizedSize;
    
    console.log(`   ✅ Optimized ${ext.toUpperCase()}: ${formatBytes(optimizedSize)} (saved ${formatBytes(savedPng)})`);
    totalSaved += savedPng;

    // 2. Create WebP version
    const webpPath = join(OUTPUT_DIR, `${name}.webp`);
    await sharp(inputPath)
      .webp(OPTIMIZATION_CONFIG.webp)
      .toFile(webpPath);

    const webpStats = await stat(webpPath);
    const webpSize = webpStats.size;
    const savedWebp = originalSize - webpSize;

    console.log(`   ✅ WebP version: ${formatBytes(webpSize)} (saved ${formatBytes(savedWebp)})`);
    
    // Show best option
    const bestFormat = webpSize < optimizedSize ? 'WebP' : ext.toUpperCase();
    const bestSize = Math.min(webpSize, optimizedSize);
    const bestSavings = originalSize - bestSize;
    const savingsPercent = Math.round((bestSavings / originalSize) * 100);

    console.log(`   🎯 Best format: ${bestFormat} - ${savingsPercent}% smaller`);

    return {
      original: originalSize,
      optimized: bestSize,
      saved: bestSavings,
    };

  } catch (error) {
    console.error(`   ❌ Error optimizing ${basename(inputPath)}:`, error.message);
    return {
      original: originalSize,
      optimized: originalSize,
      saved: 0,
    };
  }
}

/**
 * Main function
 */
async function main() {
  console.log('🎨 Image Optimization Script');
  console.log('================================\n');

  try {
    const imageFiles = await getImageFiles(ASSETS_DIR);

    if (imageFiles.length === 0) {
      console.log('No images found in src/assets');
      return;
    }

    console.log(`Found ${imageFiles.length} images to optimize\n`);

    let totalOriginal = 0;
    let totalOptimized = 0;

    for (const imagePath of imageFiles) {
      const result = await optimizeImage(imagePath);
      totalOriginal += result.original;
      totalOptimized += result.optimized;
    }

    const totalSaved = totalOriginal - totalOptimized;
    const savingsPercent = Math.round((totalSaved / totalOriginal) * 100);

    console.log('\n================================');
    console.log('📊 OPTIMIZATION SUMMARY');
    console.log('================================');
    console.log(`Total original size: ${formatBytes(totalOriginal)}`);
    console.log(`Total optimized size: ${formatBytes(totalOptimized)}`);
    console.log(`Total saved: ${formatBytes(totalSaved)} (${savingsPercent}%)`);
    console.log('\n✅ Optimized images saved to: src/assets/optimized/');
    console.log('\n💡 Next steps:');
    console.log('   1. Review optimized images for quality');
    console.log('   2. Replace original images if satisfied');
    console.log('   3. Update imports to use .webp files for best performance');

  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

main();

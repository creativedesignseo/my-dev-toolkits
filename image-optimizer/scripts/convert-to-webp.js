#!/usr/bin/env node

/**
 * WebP Conversion Script
 * 
 * This script converts all PNG/JPG images in src/assets to WebP format
 * using Sharp with high quality settings.
 * 
 * Usage: npm run convert-to-webp
 */

import sharp from 'sharp';
import { readdir, stat, unlink } from 'fs/promises';
import { join, extname, basename } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const ASSETS_DIR = join(__dirname, '../src/assets');

// Supported image formats to convert
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg'];

// WebP conversion settings
const WEBP_CONFIG = {
  quality: 85,
  effort: 6, // Max compression effort (0-6)
  lossless: false,
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
 * Check if WebP version already exists
 */
async function webpExists(imagePath) {
  const ext = extname(imagePath).toLowerCase();
  const name = basename(imagePath, ext);
  const webpPath = join(ASSETS_DIR, `${name}.webp`);
  
  try {
    await stat(webpPath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Convert a single image to WebP
 */
async function convertToWebP(inputPath, deleteOriginal = false, force = false) {
  const ext = extname(inputPath).toLowerCase();
  const name = basename(inputPath, ext);
  
  // Check if WebP already exists (unless force is true)
  if (!force && await webpExists(inputPath)) {
    console.log(`\n⏭️  Skipping: ${basename(inputPath)}`);
    console.log(`   WebP version already exists`);
    return {
      original: 0,
      webp: 0,
      saved: 0,
      path: null,
      skipped: true,
    };
  }
  
  // Get original file size
  const originalStats = await stat(inputPath);
  const originalSize = originalStats.size;

  console.log(`\n📸 Converting: ${basename(inputPath)}`);
  console.log(`   Original size: ${formatBytes(originalSize)}`);

  try {
    // Create WebP version
    const webpPath = join(ASSETS_DIR, `${name}.webp`);
    
    await sharp(inputPath)
      .webp(WEBP_CONFIG)
      .toFile(webpPath);

    const webpStats = await stat(webpPath);
    const webpSize = webpStats.size;
    const saved = originalSize - webpSize;
    const savingsPercent = Math.round((saved / originalSize) * 100);

    console.log(`   ✅ WebP created: ${formatBytes(webpSize)}`);
    console.log(`   💰 Saved: ${formatBytes(saved)} (${savingsPercent}%)`);

    // Delete original if requested
    if (deleteOriginal) {
      await unlink(inputPath);
      console.log(`   🗑️  Deleted original ${ext.toUpperCase()}`);
    }

    return {
      original: originalSize,
      webp: webpSize,
      saved: saved,
      path: webpPath,
      skipped: false,
    };

  } catch (error) {
    console.error(`   ❌ Error converting ${basename(inputPath)}:`, error.message);
    return {
      original: originalSize,
      webp: originalSize,
      saved: 0,
      path: null,
      skipped: false,
    };
  }
}

/**
 * Main function
 */
async function main() {
  console.log('🎨 WebP Conversion Script');
  console.log('================================\n');

  // Check if we should delete originals or force reconversion
  const deleteOriginals = process.argv.includes('--delete-originals');
  const forceReconvert = process.argv.includes('--force');
  
  if (deleteOriginals) {
    console.log('⚠️  WARNING: Original files will be DELETED after conversion');
    console.log('   Press Ctrl+C within 3 seconds to cancel...\n');
    await new Promise(resolve => setTimeout(resolve, 3000));
  }

  if (forceReconvert) {
    console.log('🔄 Force mode: Reconverting ALL images\n');
  }

  try {
    const imageFiles = await getImageFiles(ASSETS_DIR);

    if (imageFiles.length === 0) {
      console.log('No PNG/JPG images found in src/assets');
      return;
    }

    console.log(`Found ${imageFiles.length} PNG/JPG images\n`);

    let totalOriginal = 0;
    let totalWebP = 0;
    const convertedFiles = [];
    let skippedCount = 0;

    for (const imagePath of imageFiles) {
      const result = await convertToWebP(imagePath, deleteOriginals, forceReconvert);
      
      if (result.skipped) {
        skippedCount++;
      } else {
        totalOriginal += result.original;
        totalWebP += result.webp;
        if (result.path) {
          convertedFiles.push(result.path);
        }
      }
    }

    const totalSaved = totalOriginal - totalWebP;
    const savingsPercent = totalOriginal > 0 ? Math.round((totalSaved / totalOriginal) * 100) : 0;

    console.log('\n================================');
    console.log('📊 CONVERSION SUMMARY');
    console.log('================================');
    
    if (convertedFiles.length > 0) {
      console.log(`✅ Converted: ${convertedFiles.length} images`);
      console.log(`Total original size: ${formatBytes(totalOriginal)}`);
      console.log(`Total WebP size: ${formatBytes(totalWebP)}`);
      console.log(`Total saved: ${formatBytes(totalSaved)} (${savingsPercent}%)`);
    } else {
      console.log(`✅ No new images to convert`);
    }
    
    if (skippedCount > 0) {
      console.log(`⏭️  Skipped: ${skippedCount} images (already have WebP)`);
    }
    
    if (deleteOriginals && convertedFiles.length > 0) {
      console.log('\n✅ Original PNG/JPG files have been deleted');
    } else if (convertedFiles.length > 0) {
      console.log('\n💡 Original PNG/JPG files kept as backup');
      console.log('   Run with --delete-originals flag to remove them');
    }

    if (convertedFiles.length > 0) {
      console.log('\n🔧 Next steps:');
      console.log('   1. Update image imports in your code to use .webp files');
      console.log('   2. Test the website to ensure images load correctly');
      console.log('   3. Run "npm run build" to verify production build');
    } else {
      console.log('\n💡 Tip: Add new PNG/JPG images to src/assets/ and run again');
      console.log('   Or use --force flag to reconvert all images');
    }

  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

main();

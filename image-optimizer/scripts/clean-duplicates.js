#!/usr/bin/env node

/**
 * Clean PNG/JPG Duplicates Script
 * 
 * This script removes PNG/JPG files that already have WebP versions
 * to save disk space.
 * 
 * Usage: npm run clean-duplicates
 */

import { readdir, stat, unlink } from 'fs/promises';
import { join, extname, basename } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const ASSETS_DIR = join(__dirname, '../src/assets');

// Supported image formats to check
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg'];

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
 * Check if WebP version exists
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
 * Main function
 */
async function main() {
  console.log('🧹 Clean Duplicate Images Script');
  console.log('================================\n');

  console.log('⚠️  WARNING: This will DELETE PNG/JPG files that have WebP versions');
  console.log('   Press Ctrl+C within 3 seconds to cancel...\n');
  await new Promise(resolve => setTimeout(resolve, 3000));

  try {
    const imageFiles = await getImageFiles(ASSETS_DIR);

    if (imageFiles.length === 0) {
      console.log('No PNG/JPG images found in src/assets');
      return;
    }

    console.log(`Found ${imageFiles.length} PNG/JPG images\n`);

    let totalDeleted = 0;
    let totalSpaceSaved = 0;
    const deletedFiles = [];

    for (const imagePath of imageFiles) {
      const hasWebP = await webpExists(imagePath);
      
      if (hasWebP) {
        const stats = await stat(imagePath);
        const fileSize = stats.size;
        
        console.log(`🗑️  Deleting: ${basename(imagePath)} (${formatBytes(fileSize)})`);
        
        await unlink(imagePath);
        
        totalDeleted++;
        totalSpaceSaved += fileSize;
        deletedFiles.push(basename(imagePath));
      } else {
        console.log(`⏭️  Keeping: ${basename(imagePath)} (no WebP version)`);
      }
    }

    console.log('\n================================');
    console.log('📊 CLEANUP SUMMARY');
    console.log('================================');
    
    if (totalDeleted > 0) {
      console.log(`✅ Deleted: ${totalDeleted} files`);
      console.log(`💾 Space saved: ${formatBytes(totalSpaceSaved)}`);
      console.log('\n🗑️  Deleted files:');
      deletedFiles.forEach(file => console.log(`   - ${file}`));
    } else {
      console.log(`✅ No duplicate files to delete`);
      console.log(`   All PNG/JPG files are needed (no WebP versions exist)`);
    }

    console.log('\n✨ Cleanup complete!');

  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

main();

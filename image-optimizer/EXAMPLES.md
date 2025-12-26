# 📚 Image Optimizer Toolkit - Examples

This directory contains real-world examples of how to use the Image Optimizer Toolkit in different scenarios.

## Example 1: Restaurant Website (BaLo)

**Project Type:** Restaurant website with high-quality food photography

**Results:**
- Original size: 37.04 MB (PNG)
- Optimized size: 1.48 MB (WebP)
- Reduction: **96%**
- Load time: 96% faster

**Configuration used:**
```javascript
// vite.config.ts
imagetools({
  defaultDirectives: (url) => {
    return new URLSearchParams({
      format: 'webp',
      quality: '85',
      w: '1920',
    })
  },
})
```

**Commands used:**
```bash
npm run convert-to-webp
npm run clean-duplicates
npm run build
```

---

## Example 2: E-commerce Product Catalog

**Project Type:** Online store with 100+ product images

**Estimated Results:**
- Original size: ~100 MB (PNG/JPG)
- Optimized size: ~6 MB (WebP)
- Reduction: **94%**

**Configuration:**
```javascript
// For product images, use higher quality
imagetools({
  defaultDirectives: (url) => {
    return new URLSearchParams({
      format: 'webp',
      quality: '90', // Higher quality for products
      w: '1200',
    })
  },
})
```

---

## Example 3: Portfolio/Gallery Website

**Project Type:** Photography portfolio

**Configuration:**
```javascript
// For artistic photos, use maximum quality
imagetools({
  defaultDirectives: (url) => {
    return new URLSearchParams({
      format: 'webp',
      quality: '95', // Maximum quality
      w: '2560', // 4K support
    })
  },
})
```

**Estimated Results:**
- Original size: ~200 MB
- Optimized size: ~15 MB
- Reduction: **92%**

---

## Example 4: Blog with Many Images

**Project Type:** Blog with articles containing multiple images

**Configuration:**
```javascript
// For blog images, balance quality and size
imagetools({
  defaultDirectives: (url) => {
    return new URLSearchParams({
      format: 'webp',
      quality: '80',
      w: '1200',
    })
  },
})
```

**Estimated Results:**
- Original size: ~50 MB
- Optimized size: ~3 MB
- Reduction: **94%**

---

## Example 5: Mobile-First Application

**Project Type:** Mobile app with responsive images

**Configuration:**
```javascript
// Generate multiple sizes for different devices
imagetools({
  defaultDirectives: (url) => {
    const params = new URLSearchParams({
      format: 'webp',
      quality: '85',
    });
    
    // Detect device size and adjust
    if (url.includes('mobile')) {
      params.set('w', '400');
    } else if (url.includes('tablet')) {
      params.set('w', '800');
    } else {
      params.set('w', '1920');
    }
    
    return params;
  },
})
```

---

## Quick Start for Your Project

1. **Copy the toolkit to your project:**
   ```bash
   cp -r image-optimizer-toolkit/ your-project/
   ```

2. **Install dependencies:**
   ```bash
   npm install sharp vite-plugin-image-optimizer vite-imagetools --save-dev
   ```

3. **Choose the configuration** that matches your project type from the examples above

4. **Run the conversion:**
   ```bash
   npm run convert-to-webp
   ```

5. **Clean up duplicates:**
   ```bash
   npm run clean-duplicates
   ```

6. **Build and deploy:**
   ```bash
   npm run build
   ```

---

## Tips for Different Project Types

### High-Quality Photography:
- Quality: 90-95
- Width: 2560px (4K)
- Expected reduction: 85-90%

### E-commerce Products:
- Quality: 85-90
- Width: 1200-1920px
- Expected reduction: 90-94%

### Blog/Articles:
- Quality: 75-85
- Width: 800-1200px
- Expected reduction: 92-95%

### Icons/UI Elements:
- Quality: 80-85
- Width: 400-800px
- Expected reduction: 90-93%

---

**Last Updated:** December 26, 2025

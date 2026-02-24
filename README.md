# 🛠️ My Development Toolkits

Personal collection of reusable development tools and utilities.

## 📦 Available Toolkits

### 1. **Image Optimizer** (`image-optimizer/`)
**Version:** 1.0.0  
**Description:** Professional image optimization with WebP conversion  
**Reduction:** 90-95% file size  
**Status:** ✅ Production Ready  

**Features:**
- PNG/JPG → WebP conversion
- Automatic optimization
- Duplicate cleanup
- 100% local processing

[📖 Documentation](image-optimizer/README.md)

---

### 2. **Shopify Admin MCP** (`shopify-admin-mcp/`)
**Version:** 1.0.0
**Description:** MCP Server for Shopify Admin GraphQL API
**Status:** ✅ Production Ready

**Features:**
- Search products
- Create products with variants
- Update inventory
- Bulk operations

[📖 Documentation](shopify-admin-mcp/README.md)

---

### 3. **Google Merchant Center MCP** (`google-merchant-manager/`)
**Version:** 1.0.0
**Description:** MCP Server for Google Content API for Shopping
**Status:** ✅ Production Ready

**Features:**
- `list_products`: Get active inventory from a specific Merchant ID
- `get_product`: Get specific product details by ID

---

### 4. **Google Tag Manager MCP** (`google-tag-manager/`)
**Version:** 1.0.0
**Description:** MCP Server for interacting with GTM accounts, containers, workspaces and tags
**Status:** ✅ Production Ready

**Features:**
- List Accounts, Containers, Workspaces, Tags, Versions
- Read and Update Tags dynamically via API

---

### 5. **Google Analytics MCP** (`google-analytics-manager/`)
**Version:** 1.0.0
**Description:** MCP Server for Google Analytics 4 Management API
**Status:** ✅ Production Ready

**Features:**
- `list_accounts` & `list_properties`
- `create_conversion_event` to programmatically set Key Events
- Standard Reports generation

---

### 6. **Google Ads MCP** (`google-ads-manager/`)
**Version:** 1.0.0
**Description:** MCP Server for Google Ads API
**Status:** 🚧 In Development

**Features:**
- Querying Google Ads accounts and structure

---

## 🚀 Quick Start

### Clone this repository:
```bash
git clone https://github.com/creativedesignseo/my-dev-toolkits.git
```

### Use in your project:
```bash
# Copy toolkit to your project
cp -r my-dev-toolkits/image-optimizer/ your-project/

# Install dependencies
cd your-project
npm install sharp vite-plugin-image-optimizer vite-imagetools --save-dev

# Use it
npm run convert-to-webp
npm run clean-duplicates
```

---

## 📊 Toolkit Stats

| Toolkit | Version | Status | Downloads |
|---------|---------|--------|-----------|
| Image Optimizer | 1.0.0 | ✅ Ready | - |

---

## 🔄 Version History

### Image Optimizer
- **v1.0.0** (2025-12-26) - Initial release
  - WebP conversion
  - Clean duplicates
  - Comprehensive documentation

---

## 🎯 Future Toolkits

- [ ] SEO Toolkit
- [ ] Deployment Scripts
- [ ] UI Component Library
- [ ] API Templates

---

## 📝 License

MIT - Use freely in personal and commercial projects

---

**Maintained by:** Jonathan  
**Last Updated:** December 26, 2025

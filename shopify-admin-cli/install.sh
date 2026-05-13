#!/usr/bin/env bash
# install.sh — Instala shopify-admin en ~/.local/bin/
# Uso: bash install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
WRAPPER="$BIN_DIR/shopify-admin"

mkdir -p "$BIN_DIR"

cat > "$WRAPPER" << WRAPPER_EOF
#!/usr/bin/env bash
# shopify-admin wrapper — generado por install.sh
exec python3 "$SCRIPT_DIR/shopify_admin.py" "\$@"
WRAPPER_EOF

chmod +x "$WRAPPER"
chmod +x "$SCRIPT_DIR/shopify_admin.py"

echo ""
echo "✓ shopify-admin instalado en $WRAPPER"
echo ""
echo "  Primer paso:"
echo "  shopify-admin config add --store piro \\"
echo "    --domain piroaccessories.myshopify.com \\"
echo "    --token shpat_TU_TOKEN_AQUI"
echo ""
echo "  Luego verificar conexión:"
echo "  shopify-admin shop"
echo ""

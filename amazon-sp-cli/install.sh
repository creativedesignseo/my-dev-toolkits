#!/usr/bin/env bash
# install.sh — Instala amazon-sp en ~/.local/bin/
# Uso: bash install.sh
#
# Crea un venv aislado en ./.venv/ con python-amazon-sp-api, y un wrapper
# en ~/.local/bin/amazon-sp que ejecuta el script con ese venv.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
BIN_DIR="$HOME/.local/bin"
WRAPPER="$BIN_DIR/amazon-sp"

mkdir -p "$BIN_DIR"

# 1. Encontrar un Python que funcione.
#    En Homebrew, Python 3.12 y 3.14 vienen con pyexpat roto (libexpat mismatch).
#    Permitimos override con PYTHON=... y si no, buscamos uno que cargue xml.parsers.expat.
find_python() {
  if [ -n "$PYTHON" ] && command -v "$PYTHON" >/dev/null 2>&1; then
    "$PYTHON" -c "import xml.parsers.expat" 2>/dev/null && echo "$PYTHON" && return 0
  fi
  for py in python3.13 python3.11 python3.10 python3.14 python3.12 python3; do
    if command -v "$py" >/dev/null 2>&1 && \
       "$py" -c "import xml.parsers.expat" 2>/dev/null; then
      echo "$py"
      return 0
    fi
  done
  return 1
}

PY="$(find_python)" || {
  echo "Error: no encontre un Python con xml.parsers.expat funcional."
  echo "  Los Python de Homebrew 3.12 y 3.14 tienen pyexpat roto en este sistema."
  echo "  Instala otra version: brew install python@3.13   (o  python@3.11)"
  echo "  O exporta PYTHON apuntando a un binario que funcione."
  exit 1
}
echo "→ Usando $PY ($("$PY" --version))"

# 2. Crear venv si no existe.
#    En Homebrew Python 3.14 el ensurepip dentro de venv falla — fallback con get-pip.py.
if [ ! -x "$VENV_DIR/bin/python3" ]; then
  echo "→ Creando venv en $VENV_DIR"
  if ! "$PY" -m venv "$VENV_DIR" 2>/dev/null; then
    echo "  (ensurepip fallo, usando bootstrap via get-pip.py)"
    rm -rf "$VENV_DIR"
    "$PY" -m venv --without-pip "$VENV_DIR"
    curl -fsSL https://bootstrap.pypa.io/get-pip.py | "$VENV_DIR/bin/python3" - --quiet
  fi
fi

# 3. Instalar dependencias dentro del venv
echo "→ Instalando python-amazon-sp-api en el venv"
"$VENV_DIR/bin/python3" -m pip install --quiet --upgrade pip
"$VENV_DIR/bin/python3" -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"

# 3. Escribir wrapper
cat > "$WRAPPER" << WRAPPER_EOF
#!/usr/bin/env bash
# amazon-sp wrapper — generado por install.sh
exec "$VENV_DIR/bin/python3" "$SCRIPT_DIR/amazon_sp.py" "\$@"
WRAPPER_EOF

chmod +x "$WRAPPER"
chmod +x "$SCRIPT_DIR/amazon_sp.py"

echo ""
echo "✓ amazon-sp instalado en $WRAPPER"
echo ""
echo "  Primer paso — crea ~/.env.amazon (o en pirojewelry.com/.env.amazon)"
echo "  con tus credenciales LWA:"
echo ""
echo "    AMAZON_LWA_CLIENT_ID=amzn1.application-oa2-client.xxxxx"
echo "    AMAZON_LWA_CLIENT_SECRET=xxxxxxxxxxxx"
echo "    AMAZON_REFRESH_TOKEN=Atzr|IwEBIxxxxxxxx"
echo "    AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER"
echo ""
echo "  Luego verificar conexion:"
echo "  amazon-sp shop"
echo ""

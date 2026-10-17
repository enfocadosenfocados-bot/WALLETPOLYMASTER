#!/usr/bin/env bash
# ============================================================================
# Script de Instalación Automática para VPS en Londres (Ubuntu 22.04 / 24.04)
# Deja el entorno .venv, el archivo .env y el servicio systemd 100% listos.
# ============================================================================
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER="$(whoami)"

echo "[1/6] Actualizando paquetes del sistema en Ubuntu..."
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv git curl jq htop chrony

echo "[2/6] Sincronizando reloj NTP de precisión sub-milisegundo (Chrony) para firmas CLOB..."
sudo systemctl enable chrony
sudo systemctl restart chrony

echo "[3/6] Optimizando stack TCP de Linux (TCP BBR + FastOpen) para baja latencia (<2ms a Cloudflare Londres)..."
sudo sysctl -w net.ipv4.tcp_fastopen=3
sudo sysctl -w net.ipv4.tcp_tw_reuse=1
sudo sysctl -w net.core.rmem_max=16777216
sudo sysctl -w net.core.wmem_max=16777216
sudo sysctl -w net.core.default_qdisc=fq || true
sudo sysctl -w net.ipv4.tcp_congestion_control=bbr || true

echo "[4/6] Creando entorno virtual de Python (.venv) e instalando dependencias..."
cd "$REPO_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f "$REPO_DIR/.env" ]; then
    cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
    chmod 600 "$REPO_DIR/.env"
    echo "  -> Archivo .env creado a partir de .env.example (permisos 600)."
fi

echo "[5/6] Creando servicio systemd 'polymarket-bot.service' para ejecución 24/7 con auto-reinicio..."
sudo tee /etc/systemd/system/polymarket-bot.service > /dev/null <<EOF
[Unit]
Description=Polymarket 10-Strategy Autonomous Engine (WALLETPOLYMASTER)
After=network-online.target chrony.service
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$REPO_DIR
EnvironmentFile=$REPO_DIR/.env
ExecStart=$REPO_DIR/.venv/bin/python $REPO_DIR/bot.py
Restart=always
RestartSec=5
LimitNOFILE=65535
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

echo "[6/6] Verificando latencia y estado de Geoblock hacia Polymarket CLOB..."
curl -s -w "\nLatencia Total HTTP: %{time_total}s\n" https://clob.polymarket.com/time

echo "============================================================================"
echo " ✅ INSTALACIÓN DE VPS COMPLETADA CON ÉXITO"
echo "----------------------------------------------------------------------------"
echo " Próximos pasos:"
echo " 1. Edita tu archivo .env:         nano $REPO_DIR/.env"
echo " 2. Inicializa credenciales L2:    source $REPO_DIR/.venv/bin/activate && python $REPO_DIR/setup_credentials.py"
echo " 3. Prueba en Paper Trading (60s): python $REPO_DIR/bot.py --test-seconds 60"
echo " 4. Activa el servicio 24/7:       sudo systemctl enable --now polymarket-bot"
echo " 5. Ver logs en tiempo real:       sudo journalctl -u polymarket-bot -f"
echo "============================================================================"


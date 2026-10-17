#!/usr/bin/env bash
# ============================================================================
# Script de Instalación Automática para VPS en Londres (Ubuntu 22.04 / 24.04)
# ============================================================================
set -e

echo "[1/5] Actualizando paquetes del sistema en Ubuntu..."
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv git curl jq htop chrony

echo "[2/5] Sincronizando reloj NTP de precisión (Chrony) para firmas CLOB..."
sudo systemctl enable chrony
sudo systemctl restart chrony

echo "[3/5] Optimizando stack TCP de Linux para baja latencia (<2ms a Cloudflare Londres)..."
sudo sysctl -w net.ipv4.tcp_fastopen=3
sudo sysctl -w net.ipv4.tcp_tw_reuse=1
sudo sysctl -w net.core.rmem_max=16777216
sudo sysctl -w net.core.wmem_max=16777216

echo "[4/5] Creando entorno virtual de Python e instalando dependencias..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[5/5] Verificando latencia y estado de Geoblock hacia Polymarket CLOB..."
curl -s -w "\nLatencia Total HTTP: %{time_total}s\n" https://clob.polymarket.com/time

echo "============================================================================"
echo "Instalación completada. Copia .env.example a .env, configura tu PRIVATE_KEY"
echo "y ejecuta: source venv/bin/activate && python bot.py"
echo "============================================================================"

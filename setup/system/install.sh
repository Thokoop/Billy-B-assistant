#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DEST_DIR="/etc/systemd/system"

echo "🔧 Copying systemd service files..."
for service_file in "$SCRIPT_DIR"/*.service; do
    service_name=$(basename "$service_file")
    echo "  ↪ Installing $service_name..."
    sudo cp "$service_file" "$SYSTEMD_DEST_DIR/$service_name"
    sudo chmod 644 "$SYSTEMD_DEST_DIR/$service_name"
    sudo systemctl enable "$service_name"
    sudo systemctl restart "$service_name"
done

echo "📡 Setting up hostapd..."
sudo apt-get update
sudo apt-get install -y hostapd dnsmasq network-manager iw

echo "📝 Writing hostapd.conf..."
sudo tee /etc/hostapd/hostapd.conf >/dev/null <<EOF
interface=wlan0
driver=nl80211
ssid=Billy_Bassistant
hw_mode=g
channel=7
wmm_enabled=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=billybilly
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' | sudo tee /etc/default/hostapd

echo "⏳ Reloading and restarting services..."
sudo systemctl daemon-reexec
sudo systemctl daemon-reload

echo "✅ Wi-Fi setup installed and ready."
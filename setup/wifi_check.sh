#!/bin/bash

[ "$EUID" -ne 0 ] && exec sudo "$0" "$@"

LOG_TAG="BillyWiFiCheck"

echo "[$LOG_TAG] Checking internet connectivity..."

# Try to ping Google DNS
if ping -c 1 -W 3 8.8.8.8 &> /dev/null; then
    echo "[$LOG_TAG] Internet is available."
    sudo systemctl stop billy-wifi-setup.service
else
    echo "[$LOG_TAG] No internet connection. Starting onboarding flow..."
    # Stop conflicting services
    sudo systemctl stop NetworkManager

    # Bring wlan0 down and back up with static IP
    ip link set wlan0 down
    ip addr flush dev wlan0
    ip link set wlan0 up
    sleep 1
    ip addr add 192.168.4.1/24 dev wlan0

    echo "[$LOG_TAG] IP on wlan0:"
    ip a show wlan0

    # Restart services
    sudo systemctl restart dnsmasq
    sudo systemctl restart hostapd

    # Start the Flask onboarding app (in service)
    sudo systemctl restart billy-wifi-setup.service
    echo "[$LOG_TAG] Onboarding Flask app launched."
fi

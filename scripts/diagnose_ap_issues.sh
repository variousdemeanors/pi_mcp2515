#!/bin/bash

echo "=================================================="
echo "🔍 Pi WiFi AP Diagnostic Tool"
echo "=================================================="
echo "Date: $(date)"
echo ""

echo "🌐 Network Interface Status:"
echo "----------------------------"
ip addr show | grep -E "(wlan|inet)"
echo ""

echo "🔧 NetworkManager Status:"
echo "-------------------------"
sudo systemctl status NetworkManager --no-pager -l
echo ""

echo "📡 Active Connections:"
echo "----------------------"
sudo nmcli connection show --active
echo ""

echo "📋 All Connections:"
echo "-------------------"
sudo nmcli connection show
echo ""

echo "🔍 Device Status:"
echo "-----------------"
sudo nmcli device status
echo ""

echo "⚙️  NetworkManager Configuration:"
echo "---------------------------------"
if [ -f /etc/NetworkManager/NetworkManager.conf ]; then
    echo "NetworkManager.conf exists:"
    cat /etc/NetworkManager/NetworkManager.conf
else
    echo "❌ NetworkManager.conf not found"
fi
echo ""

echo "🏠 Hostapd Status:"
echo "------------------"
sudo systemctl status hostapd --no-pager -l || echo "hostapd not running"
echo ""

echo "📡 Dnsmasq Status:"
echo "------------------"
sudo systemctl status dnsmasq --no-pager -l || echo "dnsmasq not running"
echo ""

echo "🔧 dhcpcd Status:"
echo "-----------------"
sudo systemctl status dhcpcd --no-pager -l || echo "dhcpcd not running"
echo ""

echo "📊 Process List (network related):"
echo "-----------------------------------"
ps aux | grep -E "(hostapd|dnsmasq|dhcp|wpa|network)" | grep -v grep
echo ""

echo "🔍 WiFi Interface Details:"
echo "--------------------------"
sudo iw dev
echo ""

echo "📡 WiFi Interface Configuration:"
echo "--------------------------------"
sudo iwconfig
echo ""

echo "🔧 Conflicting Services Check:"
echo "------------------------------"
echo "Checking for conflicting DHCP services..."
sudo netstat -tulpn | grep :67 || echo "No DHCP server found on port 67"
echo ""
echo "Checking for conflicting DNS services..."
sudo netstat -tulpn | grep :53 || echo "No DNS server found on port 53"
echo ""

echo "📋 Routing Table:"
echo "-----------------"
ip route show
echo ""

echo "🔍 AP Mode Capability Check:"
echo "----------------------------"
sudo iw list | grep -A 10 "Supported interface modes" || echo "Could not check interface modes"
echo ""

echo "⚠️  Log Errors (last 50 lines):"
echo "-------------------------------"
sudo journalctl -u NetworkManager -n 50 --no-pager
echo ""

echo "🔧 Recommendations:"
echo "-------------------"
echo "1. Check if multiple DHCP services are running"
echo "2. Verify NetworkManager isn't conflicting with hostapd"
echo "3. Check if wpa_supplicant is interfering"
echo "4. Ensure correct WiFi interface assignments"
echo ""

echo "=================================================="
echo "✅ Diagnostic complete!"
echo "=================================================="
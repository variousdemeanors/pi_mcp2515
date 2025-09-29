#!/bin/bash

echo "=================================================="
echo "🔍 ESP32 Connection Test"
echo "=================================================="
echo "Testing ESP32 connection to WMIPressure AP"
echo ""

echo "🌐 Checking AP Status:"
echo "----------------------"
# Check hostapd status instead of NetworkManager
sudo systemctl status hostapd --no-pager -l | head -10
echo ""
echo "🔧 Checking hostapd configuration:"
sudo cat /etc/hostapd/hostapd.conf | grep -E "(ssid|channel|interface)"
echo ""
echo "🔧 Checking dnsmasq DHCP range:"
sudo cat /etc/dnsmasq.conf | grep -E "(dhcp-range|interface)" || echo "No DHCP range configured"
echo ""

echo "📡 Checking AP Gateway:"
echo "-----------------------"
ping -c 3 192.168.4.1
echo ""

echo "🔍 Scanning for ESP32 on AP network:"
echo "------------------------------------"
echo "Checking static IP (192.168.4.150)..."
if curl -s --connect-timeout 3 http://192.168.4.150:5000/status > /dev/null 2>&1; then
    echo "✅ ESP32 found at static IP 192.168.4.150"
    curl -s http://192.168.4.150:5000/status | head -5
else
    echo "❌ ESP32 not responding at static IP"
fi

echo ""
echo "Scanning DHCP range (192.168.4.101-110)..."
for i in {101..110}; do
    IP="192.168.4.$i"
    if curl -s --connect-timeout 1 http://$IP:5000/status > /dev/null 2>&1; then
        echo "✅ ESP32 found at DHCP IP $IP"
        curl -s http://$IP:5000/status | head -3
        break
    fi
done

echo ""
echo "🔍 Checking WiFi interface status:"
echo "---------------------------------"
sudo iwconfig wlan0
echo ""
echo "🔍 Checking if AP is broadcasting:"
echo "---------------------------------"
sudo iwlist wlan0 scan | grep -A 5 -B 5 "WMIPressure" || echo "⚠️  WMIPressure not found in scan (may be normal for own AP)"

echo ""
echo "🔍 Checking DHCP leases:"
echo "------------------------"
sudo journalctl -u dnsmasq | grep -i dhcp | tail -5

echo ""
echo "📊 Current network clients:"
echo "---------------------------"
# Check ARP table for active devices on AP network
arp -a | grep "192.168.4"

echo ""
echo "=================================================="
echo "✅ ESP32 connection test complete"
echo "=================================================="
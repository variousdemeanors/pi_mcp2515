#!/bin/bash

echo "=================================================="
echo "🔧 Pi WiFi AP Issue Fixer"
echo "=================================================="
echo "This script will fix common AP configuration issues"
echo ""

# Function to ask for confirmation
confirm() {
    read -p "$1 (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

echo "🛑 Step 1: Stop conflicting services"
echo "------------------------------------"
if confirm "Stop hostapd and dnsmasq services?"; then
    sudo systemctl stop hostapd || echo "hostapd already stopped"
    sudo systemctl stop dnsmasq || echo "dnsmasq already stopped"
    sudo systemctl disable hostapd || echo "hostapd not enabled"
    sudo systemctl disable dnsmasq || echo "dnsmasq not enabled"
    echo "✅ Legacy AP services stopped"
fi

echo ""
echo "🔧 Step 2: Clean up dhcpcd conflicts"
echo "------------------------------------"
if confirm "Disable dhcpcd on wlan0 (AP interface)?"; then
    # Add denyinterfaces wlan0 to dhcpcd.conf if not present
    if ! grep -q "denyinterfaces wlan0" /etc/dhcpcd.conf 2>/dev/null; then
        echo "denyinterfaces wlan0" | sudo tee -a /etc/dhcpcd.conf
        echo "✅ Added denyinterfaces wlan0 to dhcpcd.conf"
    else
        echo "✅ dhcpcd already configured to ignore wlan0"
    fi
    sudo systemctl restart dhcpcd
fi

echo ""
echo "🔧 Step 3: Configure NetworkManager for dual WiFi"
echo "---------------------------------------------------"
if confirm "Configure NetworkManager for dual WiFi (AP + Client)?"; then
    # Ensure NetworkManager.conf exists and is configured correctly
    sudo mkdir -p /etc/NetworkManager
    sudo cat > /etc/NetworkManager/NetworkManager.conf << 'EOF'
[main]
plugins=ifupdown,keyfile

[ifupdown]
managed=false

[device]
wifi.scan-rand-mac-address=no

[connection]
wifi.cloned-mac-address=stable
EOF
    
    echo "✅ NetworkManager.conf configured"
fi

echo ""
echo "🔧 Step 4: Remove existing WMIPressure connection"
echo "-------------------------------------------------"
if confirm "Remove and recreate WMIPressure AP connection?"; then
    # Remove existing connection if it exists
    sudo nmcli connection delete "WMIPressure" 2>/dev/null || echo "No existing WMIPressure connection"
    echo "✅ Removed existing WMIPressure connection"
fi

echo ""
echo "🔧 Step 5: Create new AP connection"
echo "-----------------------------------"
if confirm "Create new WMIPressure AP on wlan0?"; then
    # Create new AP connection
    sudo nmcli connection add type wifi ifname wlan0 mode ap con-name "WMIPressure" ssid "WMIPressure"
    sudo nmcli connection modify "WMIPressure" 802-11-wireless.band bg
    sudo nmcli connection modify "WMIPressure" 802-11-wireless.channel 7
    sudo nmcli connection modify "WMIPressure" 802-11-wireless-security.key-mgmt wpa-psk
    sudo nmcli connection modify "WMIPressure" 802-11-wireless-security.psk "pressure22"
    sudo nmcli connection modify "WMIPressure" ipv4.method shared
    sudo nmcli connection modify "WMIPressure" ipv4.addresses 192.168.4.1/24
    sudo nmcli connection modify "WMIPressure" connection.autoconnect yes
    
    echo "✅ WMIPressure AP connection created"
fi

echo ""
echo "🔧 Step 6: Restart NetworkManager"
echo "---------------------------------"
if confirm "Restart NetworkManager to apply changes?"; then
    sudo systemctl restart NetworkManager
    sleep 5
    echo "✅ NetworkManager restarted"
fi

echo ""
echo "🔧 Step 7: Bring up AP connection"
echo "---------------------------------"
if confirm "Activate WMIPressure AP?"; then
    sudo nmcli connection up "WMIPressure"
    sleep 3
    echo "✅ WMIPressure AP activated"
fi

echo ""
echo "🔍 Step 8: Verify configuration"
echo "-------------------------------"
echo "Network interfaces:"
ip addr show | grep -E "(wlan|inet)"
echo ""
echo "Active connections:"
sudo nmcli connection show --active
echo ""
echo "Device status:"
sudo nmcli device status
echo ""

echo "🔧 Step 9: Test AP broadcast"
echo "----------------------------"
echo "Checking if WMIPressure is broadcasting..."
sudo iwlist wlan0 scan | grep -i "wmipressure" || echo "⚠️  WMIPressure not found in scan"

echo ""
echo "=================================================="
echo "✅ AP configuration complete!"
echo "=================================================="
echo ""
echo "🎯 Next steps:"
echo "1. Check if WMIPressure network is visible from other devices"
echo "2. Test ESP32 connection to the AP"
echo "3. Verify Pi gateway is reachable at 192.168.4.1"
echo ""
echo "🔍 If issues persist, run: ./diagnose_ap_issues.sh"
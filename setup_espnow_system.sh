#!/bin/bash

# ESP-NOW OBD Datalogger Setup Script
# This script automates the setup of the Raspberry Pi for ESP-NOW based OBD datalogging

set -e

echo "🚀 Starting ESP-NOW OBD Datalogger Setup..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
echo "📦 Installing required packages..."
sudo apt install -y python3 python3-pip python3-venv git i2c-tools python3-smbus

# Enable serial interface
echo "🔧 Enabling serial interface..."
sudo raspi-config nonint do_serial 0
sudo systemctl disable hciuart
sudo systemctl stop hciuart

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install pyserial for serial communication
pip install pyserial

# Set up CAN interface (if needed for testing)
echo "🔧 Setting up CAN interface..."
sudo modprobe can
sudo modprobe can_raw
sudo modprobe mcp2515

# Create udev rule for MCP2515 (optional)
echo "🔧 Creating udev rule for MCP2515..."
sudo tee /etc/udev/rules.d/99-mcp2515.rules > /dev/null <<EOF
SUBSYSTEM=="spi", KERNEL=="spi0.0", ACTION=="add", RUN+="/sbin/modprobe mcp2515"
EOF
sudo udevadm control --reload-rules

# Set up logging directory
echo "📁 Setting up logging directory..."
mkdir -p logs

# Configure Pi for low latency (optional)
echo "⚡ Configuring for low latency..."
sudo tee -a /etc/sysctl.conf > /dev/null <<EOF
# Low latency settings for real-time datalogging
kernel.sched_rt_runtime_us = -1
vm.swappiness = 1
EOF

# Enable realtime scheduling for user
echo "👤 Enabling realtime scheduling..."
sudo tee /etc/security/limits.d/99-realtime.conf > /dev/null <<EOF
* - rtprio 99
* - memlock unlimited
EOF

echo "✅ Hardware setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Wire the ESP32s according to the instructions"
echo "2. Flash esp32_can_obd.ino to the CAN ESP32 (update coordinator MAC address)"
echo "3. Flash esp32_coordinator.ino to the coordinator ESP32"
echo "4. Power on the system and run: python main.py"
echo ""
echo "🔍 To test the setup:"
echo "python -c \"from core.wireless_obd_adapter import create_wireless_obd_connection; import json; conn = create_wireless_obd_connection(json.load(open('config.json'))); print('Connection created' if conn else 'Config error')\""
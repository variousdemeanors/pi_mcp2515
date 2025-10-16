#!/bin/bash

# Deploy ESP32 firmware to Raspberry Pi and flash
# Usage: ./deploy_to_pi.sh [pi_hostname_or_ip] [port]
# Example: ./deploy_to_pi.sh raspberrypi.local /dev/ttyUSB0

set -e  # Exit on error

# Configuration
PI_HOST="${1:-raspberrypi.local}"
ESP_PORT="${2:-/dev/ttyUSB0}"
PI_USER="pi"
REMOTE_DIR="/tmp/esp32_flash"
PROJECT_NAME="3.2inch_ESP32_LVGL"

echo "========================================="
echo "ESP32 Deploy & Flash Script"
echo "========================================="
echo "Target Pi: ${PI_USER}@${PI_HOST}"
echo "ESP32 Port: ${ESP_PORT}"
echo ""

# Step 1: Build the firmware
echo "📦 Building firmware in codespace..."
idf.py build

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Build successful!"
echo ""

# Step 2: Create temporary directory on Pi
echo "📁 Creating remote directory on Pi..."
ssh ${PI_USER}@${PI_HOST} "mkdir -p ${REMOTE_DIR}"

# Step 3: Copy binaries to Pi
echo "📤 Copying firmware files to Pi..."
scp build/bootloader/bootloader.bin \
    build/partition_table/partition-table.bin \
    build/${PROJECT_NAME}.bin \
    ${PI_USER}@${PI_HOST}:${REMOTE_DIR}/

if [ $? -ne 0 ]; then
    echo "❌ Failed to copy files to Pi!"
    exit 1
fi

echo "✅ Files copied successfully!"
echo ""

# Step 4: Flash on Pi
echo "⚡ Flashing ESP32 on Pi..."
ssh ${PI_USER}@${PI_HOST} << EOF
    set -e
    cd ${REMOTE_DIR}
    
    # Check if esptool is installed
    if ! command -v esptool.py &> /dev/null; then
        echo "Installing esptool..."
        pip3 install esptool
    fi
    
    echo "Flashing to ${ESP_PORT}..."
    esptool.py --chip esp32 -p ${ESP_PORT} -b 460800 \
        --before default_reset --after hard_reset write_flash \
        --flash_mode dio --flash_size 2MB --flash_freq 40m \
        0x1000 bootloader.bin \
        0x8000 partition-table.bin \
        0x10000 ${PROJECT_NAME}.bin
    
    echo ""
    echo "✅ Flash complete!"
    echo ""
    echo "To monitor serial output, run:"
    echo "  ssh ${PI_USER}@${PI_HOST}"
    echo "  screen ${ESP_PORT} 115200"
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "✅ Deployment successful!"
    echo "========================================="
    echo ""
    echo "Next steps:"
    echo "  1. SSH to Pi: ssh ${PI_USER}@${PI_HOST}"
    echo "  2. Monitor: screen ${ESP_PORT} 115200"
    echo "     (Exit screen: Ctrl+A, then K, then Y)"
else
    echo ""
    echo "❌ Flash failed! Check Pi connection and port."
    exit 1
fi

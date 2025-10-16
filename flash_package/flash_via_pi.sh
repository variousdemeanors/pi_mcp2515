#!/bin/bash
# Flash ESP32 via Raspberry Pi
# Usage: ./flash_via_pi.sh [PI_HOST] [ESP_PORT]
# Example: ./flash_via_pi.sh pi@raspberrypi.local /dev/ttyUSB0

PI_HOST="${1:-pi@raspberrypi.local}"
ESP_PORT="${2:-/dev/ttyUSB0}"

echo "Uploading binaries to Raspberry Pi..."
scp bootloader.bin partition-table.bin 3.2inch_ESP32_LVGL.bin "$PI_HOST:/tmp/"

if [ $? -ne 0 ]; then
    echo "❌ Failed to copy files to Raspberry Pi"
    exit 1
fi

echo "Flashing ESP32 on Raspberry Pi..."
ssh "$PI_HOST" bash << ENDSSH
    # Install esptool if not present
    if ! command -v esptool.py &> /dev/null; then
        echo "Installing esptool on Raspberry Pi..."
        pip3 install esptool
    fi
    
    # Flash the binaries
    esptool.py --chip esp32 --port "$ESP_PORT" --baud 460800 \
        --before default_reset --after hard_reset write_flash -z \
        --flash_mode dio --flash_freq 40m --flash_size detect \
        0x1000 /tmp/bootloader.bin \
        0x8000 /tmp/partition-table.bin \
        0x10000 /tmp/3.2inch_ESP32_LVGL.bin
    
    # Cleanup
    rm /tmp/bootloader.bin /tmp/partition-table.bin /tmp/3.2inch_ESP32_LVGL.bin
ENDSSH

echo ""
echo "✅ Flash complete via Raspberry Pi!"

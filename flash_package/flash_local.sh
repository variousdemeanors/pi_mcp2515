#!/bin/bash
# Flash ESP32 from local machine
# Usage: ./flash_local.sh [PORT]
# Example: ./flash_local.sh /dev/ttyUSB0

PORT="${1:-/dev/ttyUSB0}"

echo "Flashing ESP32 on port: $PORT"
echo ""

# Check if esptool is installed
if ! command -v esptool.py &> /dev/null; then
    echo "Installing esptool..."
    pip install esptool
fi

# Flash the binaries
esptool.py --chip esp32 --port "$PORT" --baud 460800 \
    --before default_reset --after hard_reset write_flash -z \
    --flash_mode dio --flash_freq 40m --flash_size detect \
    0x1000 bootloader.bin \
    0x8000 partition-table.bin \
    0x10000 3.2inch_ESP32_LVGL.bin

echo ""
echo "✅ Flash complete! Reset your ESP32."

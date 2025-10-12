#!/bin/bash

# ESP32 Flash Script
# Usage: ./flash_esp32.sh [receiver|transmitter] [port]

if [ $# -lt 2 ]; then
    echo "Usage: $0 [receiver|transmitter] [port]"
    echo "Example: $0 receiver COM3"
    echo "Example: $0 transmitter /dev/ttyUSB0"
    exit 1
fi

DEVICE_TYPE=$1
PORT=$2

case $DEVICE_TYPE in
    "receiver")
        BUILD_DIR=".pio/build/esp32dev-receiver"
        echo "Flashing ESP32-32E Display Board (receiver) to $PORT..."
        ;;
    "transmitter")
        BUILD_DIR=".pio/build/esp32dev-transmitter"
        echo "Flashing ESP32 transmitter to $PORT..."
        ;;
    *)
        echo "Invalid device type. Use 'receiver' or 'transmitter'"
        exit 1
        ;;
esac

# Check if binaries exist
if [ ! -f "$BUILD_DIR/firmware.bin" ]; then
    echo "Error: Firmware binaries not found in $BUILD_DIR"
    echo "Please run 'pio run -e esp32dev-$DEVICE_TYPE' first"
    exit 1
fi

echo "Using binaries from: $BUILD_DIR"
echo "Port: $PORT"
echo ""

# Flash the ESP32
esptool.py --chip esp32 --port $PORT --baud 921600 write_flash \
    0x1000 "$BUILD_DIR/bootloader.bin" \
    0x8000 "$BUILD_DIR/partitions.bin" \
    0x10000 "$BUILD_DIR/firmware.bin"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Flash successful!"
    echo "You can now monitor the device with:"
    echo "   pio device monitor -p $PORT -b 115200"
else
    echo ""
    echo "❌ Flash failed! Check your connection and port."
    echo "Troubleshooting:"
    echo "- Make sure ESP32 is connected"
    echo "- Try holding BOOT button while pressing RESET"
    echo "- Verify the correct port"
fi
#!/bin/bash

# prepare_flash_package.sh
# Builds the ESP-IDF project in Codespace and packages binaries for local flashing
# Usage: ./prepare_flash_package.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}ESP32 Flash Package Builder${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Build the project
echo -e "${YELLOW}[1/3] Building ESP-IDF project...${NC}"
idf.py build

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Build completed successfully${NC}"
echo ""

# Step 2: Create flash package directory
FLASH_PKG_DIR="flash_package"
rm -rf "$FLASH_PKG_DIR"
mkdir -p "$FLASH_PKG_DIR"

echo -e "${YELLOW}[2/3] Packaging flash binaries...${NC}"

# Copy binary files
cp build/bootloader/bootloader.bin "$FLASH_PKG_DIR/"
cp build/partition_table/partition-table.bin "$FLASH_PKG_DIR/"
cp build/3.2inch_ESP32_LVGL.bin "$FLASH_PKG_DIR/"

# Get file sizes
BOOTLOADER_SIZE=$(stat -f%z "$FLASH_PKG_DIR/bootloader.bin" 2>/dev/null || stat -c%s "$FLASH_PKG_DIR/bootloader.bin" 2>/dev/null)
PARTITION_SIZE=$(stat -f%z "$FLASH_PKG_DIR/partition-table.bin" 2>/dev/null || stat -c%s "$FLASH_PKG_DIR/partition-table.bin" 2>/dev/null)
APP_SIZE=$(stat -f%z "$FLASH_PKG_DIR/3.2inch_ESP32_LVGL.bin" 2>/dev/null || stat -c%s "$FLASH_PKG_DIR/3.2inch_ESP32_LVGL.bin" 2>/dev/null)

echo -e "${GREEN}✅ Binaries packaged:${NC}"
echo "   - bootloader.bin ($(numfmt --to=iec-i --suffix=B $BOOTLOADER_SIZE 2>/dev/null || echo "$BOOTLOADER_SIZE bytes"))"
echo "   - partition-table.bin ($(numfmt --to=iec-i --suffix=B $PARTITION_SIZE 2>/dev/null || echo "$PARTITION_SIZE bytes"))"
echo "   - 3.2inch_ESP32_LVGL.bin ($(numfmt --to=iec-i --suffix=B $APP_SIZE 2>/dev/null || echo "$APP_SIZE bytes"))"
echo ""

# Step 3: Create flash scripts for different platforms
echo -e "${YELLOW}[3/3] Creating flash scripts...${NC}"

# Linux/macOS script for local flashing
cat > "$FLASH_PKG_DIR/flash_local.sh" << 'EOF'
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
EOF

# Windows script for local flashing
cat > "$FLASH_PKG_DIR/flash_local.bat" << 'EOF'
@echo off
REM Flash ESP32 from local machine (Windows)
REM Usage: flash_local.bat [PORT]
REM Example: flash_local.bat COM3

set PORT=%1
if "%PORT%"=="" set PORT=COM3

echo Flashing ESP32 on port: %PORT%
echo.

REM Check if esptool is installed
where esptool.py >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing esptool...
    pip install esptool
)

REM Flash the binaries
esptool.py --chip esp32 --port %PORT% --baud 460800 ^
    --before default_reset --after hard_reset write_flash -z ^
    --flash_mode dio --flash_freq 40m --flash_size detect ^
    0x1000 bootloader.bin ^
    0x8000 partition-table.bin ^
    0x10000 3.2inch_ESP32_LVGL.bin

echo.
echo Flash complete! Reset your ESP32.
pause
EOF

# Script for flashing via Raspberry Pi
cat > "$FLASH_PKG_DIR/flash_via_pi.sh" << 'EOF'
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
EOF

chmod +x "$FLASH_PKG_DIR/flash_local.sh"
chmod +x "$FLASH_PKG_DIR/flash_via_pi.sh"

# Create README
cat > "$FLASH_PKG_DIR/README.md" << 'EOF'
# ESP32 Flash Package

This package contains pre-built binaries for the ESP32 LVGL project.

## Files Included

- `bootloader.bin` - ESP32 bootloader (flash at 0x1000)
- `partition-table.bin` - Partition table (flash at 0x8000)
- `3.2inch_ESP32_LVGL.bin` - Application binary (flash at 0x10000)

## Flashing Instructions

### Option 1: Direct from Local Machine

**Linux/macOS:**
```bash
./flash_local.sh /dev/ttyUSB0
```

**Windows:**
```cmd
flash_local.bat COM3
```

### Option 2: Via Raspberry Pi

If your ESP32 is connected to a Raspberry Pi:

```bash
./flash_via_pi.sh pi@raspberrypi.local /dev/ttyUSB0
```

### Option 3: Manual Flash

If you prefer to flash manually:

```bash
esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 \
    --before default_reset --after hard_reset write_flash -z \
    --flash_mode dio --flash_freq 40m --flash_size detect \
    0x1000 bootloader.bin \
    0x8000 partition-table.bin \
    0x10000 3.2inch_ESP32_LVGL.bin
```

## Requirements

- Python 3
- esptool (`pip install esptool`)
- USB drivers for your ESP32 board

## Troubleshooting

**Permission denied on Linux:**
```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

**Can't find port:**
- Linux: Usually `/dev/ttyUSB0` or `/dev/ttyACM0`
- macOS: Usually `/dev/cu.usbserial-*`
- Windows: Usually `COM3`, `COM4`, etc. (check Device Manager)

**Flash fails:**
- Hold BOOT button while flashing
- Try lower baud rate: change `460800` to `115200`
- Check USB cable (data cable, not charge-only)
EOF

echo -e "${GREEN}✅ Flash scripts created${NC}"
echo ""

# Create a tarball for easy download
TARBALL="flash_package_$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czf "$TARBALL" -C "$FLASH_PKG_DIR" .

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Flash package ready!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Package location:${NC} $FLASH_PKG_DIR/"
echo -e "${YELLOW}Archive:${NC} $TARBALL"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Download the flash_package/ folder or $TARBALL from VS Code"
echo "   (Right-click in Explorer > Download)"
echo ""
echo "2. Extract on your local machine"
echo ""
echo "3. Run the appropriate flash script:"
echo "   - Linux/macOS: ./flash_local.sh /dev/ttyUSB0"
echo "   - Windows: flash_local.bat COM3"
echo "   - Via Pi: ./flash_via_pi.sh pi@raspberrypi.local /dev/ttyUSB0"
echo ""
echo -e "${GREEN}Happy flashing! 🚀${NC}"

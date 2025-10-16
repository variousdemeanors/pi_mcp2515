# ESP32 LVGL Build & Deploy Guide

## Overview

This project uses **ESP-IDF v5.3.2** for the manufacturer's 3.2" ESP32 Display with LVGL.

## ⚠️ Important: Codespace Networking Limitations

**GitHub Codespaces run in Microsoft Azure** and cannot directly access devices on your local network (Raspberry Pi, ESP32). 

### Choose Your Workflow:

#### Option A: Build in Codespace, Flash Locally ⭐ RECOMMENDED
1. Build in Codespace (fast cloud resources)
2. Download binaries
3. Flash from your local machine

#### Option B: Build Everything on Raspberry Pi
1. Clone repo on Pi
2. Build and flash locally
3. Slower build but no network complexity

---

## Quick Start - Option A (Codespace Build)

### Step 1: Build and Package Binaries

In your Codespace terminal:
```bash
./prepare_flash_package.sh
```

This will:
- Build the ESP-IDF project
- Package all necessary binaries
- Create flash scripts for different platforms
- Generate a tarball for easy download

### Step 2: Download the Package

1. In VS Code Explorer, locate the `flash_package/` folder
2. Right-click on `flash_package_XXXXXXXX_XXXXXX.tar.gz`
3. Select **Download**

### Step 3: Flash from Local Machine

Extract the downloaded tarball on your local machine, then:

**Linux/macOS (Direct USB):**
```bash
cd flash_package
./flash_local.sh /dev/ttyUSB0
```

**Windows (Direct USB):**
```cmd
cd flash_package
flash_local.bat COM3
```

**Via Raspberry Pi:**
```bash
cd flash_package
./flash_via_pi.sh pi@raspberrypi.local /dev/ttyUSB0
```

---

## Alternative: Deploy via Raspberry Pi (Legacy)

**Note:** This only works if you can access your Raspberry Pi from the Codespace (requires tunneling/VPN).

## Prerequisites

### On Raspberry Pi
1. **SSH access** from codespace to Pi (requires port forwarding/tunnel)
2. **esptool** will be auto-installed if missing
3. **ESP32 connected** to Pi via USB

### Setup SSH Keys (One-time)
```bash
# In codespace
ssh-keygen -t ed25519 -C "codespace-to-pi"

# Manual key copy (since Pi is not directly accessible)
cat ~/.ssh/id_ed25519.pub
# Copy the output and add it to ~/.ssh/authorized_keys on your Pi
```

## Quick Start (If Network Access Available)

### Method 1: VS Code Task (Recommended)
1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P`)
2. Type: `Tasks: Run Task`
3. Select: **Deploy to Pi (Quick)**
4. Wait for build and flash to complete ✅

### Method 2: Command Line
```bash
# Default: raspberrypi.local and /dev/ttyUSB0
./deploy_to_pi.sh

# Custom Pi and port
./deploy_to_pi.sh pi4.local /dev/ttyACM0
```

### Method 3: Custom Task
1. Press `Ctrl+Shift+P`
2. Select: **Deploy to Raspberry Pi**
3. Enter your Pi hostname (e.g., `192.168.1.100`)
4. Enter ESP32 port (e.g., `/dev/ttyUSB0`)

## What the Script Does

1. 📦 **Builds** firmware with `idf.py build`
2. 📤 **Copies** binaries to Pi via SCP:
   - `bootloader.bin`
   - `partition-table.bin`
   - `3.2inch_ESP32_LVGL.bin`
3. ⚡ **Flashes** ESP32 on Pi using esptool
4. ✅ **Reports** success/failure

## Monitor Serial Output

After flashing, monitor the ESP32:

```bash
# SSH to Pi
ssh pi@raspberrypi.local

# Monitor serial (115200 baud)
screen /dev/ttyUSB0 115200

# Exit screen: Ctrl+A, then K, then Y
```

## Build Only (No Deploy)

```bash
idf.py build
```

## Clean Build

```bash
idf.py fullclean
idf.py build
```

## Configuration

Edit LVGL/ESP32 settings:
```bash
idf.py menuconfig
```

## Troubleshooting

### Cannot connect to Pi
```bash
# Test SSH connection
ssh pi@raspberrypi.local

# Check if Pi is reachable
ping raspberrypi.local
```

### Wrong serial port
```bash
# On Pi, list USB devices
ls /dev/tty*

# Common ports:
# - /dev/ttyUSB0, /dev/ttyUSB1
# - /dev/ttyACM0
# - /dev/serial0
```

### Flash permission denied
```bash
# On Pi, add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Binary size too large
Current: **522 KB / 1 MB** (50% free)

If you add features and exceed 1MB:
```bash
idf.py menuconfig
# → Partition Table → Partition Table → Custom partition table CSV
```

## Current Configuration

- **ESP-IDF**: v5.3.2
- **Target**: ESP32
- **Display**: ILI9341 (320x240)
- **Touch**: XPT2046 (Resistive)
- **LVGL**: v8.x with widgets demo
- **Memory**: 48 KB heap

## Project Structure

```
.
├── main/                    # Main application code
├── components/
│   ├── lvgl/               # LVGL library
│   ├── lvgl_esp32_drivers/ # ESP32 display/touch drivers
│   └── lv_porting/         # LVGL port layer
├── build/                  # Build output (binaries)
├── sdkconfig              # ESP-IDF configuration
└── deploy_to_pi.sh        # Deploy script
```

## Tips

- **Faster builds**: Use `idf.py build` in codespace (parallel compilation)
- **Save SSH password**: Use `ssh-copy-id` for passwordless deployment
- **Auto-rebuild**: The deploy script rebuilds before flashing
- **Multiple devices**: Specify different ports for different ESP32s

## Support

ESP-IDF Documentation: https://docs.espressif.com/projects/esp-idf/en/v5.3.2/

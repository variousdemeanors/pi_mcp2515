# 🚀 Quick Start - Build in Codespace, Flash Locally

## TL;DR
```bash
# In GitHub Codespace:
./prepare_flash_package.sh

# Download flash_package_*.tar.gz from VS Code
# Extract on your local machine, then:

# Linux/macOS:
./flash_local.sh /dev/ttyUSB0

# Windows:
flash_local.bat COM3

# Via Raspberry Pi:
./flash_via_pi.sh pi@raspberrypi.local /dev/ttyUSB0
```

---

## Why This Workflow?

**Problem:** GitHub Codespaces run in Azure cloud ☁️  
**Your devices:** Raspberry Pi and ESP32 are on your local network 🏠  
**Solution:** Build in fast cloud environment, flash from local machine 💡

---

## Step-by-Step

### 1️⃣ Build in Codespace
```bash
./prepare_flash_package.sh
```

**What this does:**
- ✅ Builds ESP-IDF project (fast cloud resources!)
- ✅ Packages all 3 required binaries
- ✅ Creates ready-to-use flash scripts
- ✅ Generates tarball for easy download

### 2️⃣ Download Package

**In VS Code Explorer:**
1. Locate `flash_package_YYYYMMDD_HHMMSS.tar.gz`
2. Right-click → **Download**
3. Save to your local machine

### 3️⃣ Extract & Flash

**On your local machine:**
```bash
# Extract
tar -xzf flash_package_*.tar.gz
cd flash_package

# Flash (choose your platform)
./flash_local.sh /dev/ttyUSB0        # Linux/macOS direct
flash_local.bat COM3                  # Windows direct
./flash_via_pi.sh pi@192.168.1.100 /dev/ttyUSB0  # Via Raspberry Pi
```

---

## Finding Your Port

**Linux:**
```bash
ls /dev/ttyUSB* /dev/ttyACM*
# Usually /dev/ttyUSB0 or /dev/ttyACM0
```

**macOS:**
```bash
ls /dev/cu.usbserial-*
# Usually /dev/cu.usbserial-XXXXXXXX
```

**Windows:**
- Open Device Manager
- Look under "Ports (COM & LPT)"
- Usually COM3, COM4, etc.

---

## Troubleshooting

### Permission Denied (Linux)
```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Flash Fails
1. **Hold BOOT button** on ESP32 while flashing
2. Try lower baud rate: Edit script, change `460800` to `115200`
3. Check USB cable (must be data cable, not charge-only)

### Can't Find esptool
```bash
pip install esptool
# or
pip3 install esptool
```

---

## Manual Flash Command

If scripts don't work, use this directly:

```bash
esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 \
    --before default_reset --after hard_reset write_flash -z \
    --flash_mode dio --flash_freq 40m --flash_size detect \
    0x1000 bootloader.bin \
    0x8000 partition-table.bin \
    0x10000 3.2inch_ESP32_LVGL.bin
```

---

## What Gets Flashed?

| Address | File | Purpose |
|---------|------|---------|
| 0x1000 | bootloader.bin | ESP32 bootloader (~27KB) |
| 0x8000 | partition-table.bin | Partition layout (~3KB) |
| 0x10000 | 3.2inch_ESP32_LVGL.bin | Your LVGL app (~510KB) |

---

## Alternative: Build on Raspberry Pi

If you prefer to build everything locally on your Pi:

```bash
# On Raspberry Pi
git clone https://github.com/variousdemeanors/pi_mcp2515.git
cd pi_mcp2515
git checkout LVGL-Manufacturers-ESP-IDF

# Install ESP-IDF v5.3.2
# ... follow ESP-IDF installation guide ...

# Build and flash
idf.py build
idf.py -p /dev/ttyUSB0 flash
```

**Pros:** Simpler, no network complexity  
**Cons:** Slower builds (Pi vs cloud compute)

---

## Need Help?

📖 Full documentation: [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)  
🔧 Project README: [README.md](README.md)

Happy flashing! 🎉

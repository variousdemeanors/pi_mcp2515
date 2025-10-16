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

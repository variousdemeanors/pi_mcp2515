# ESP32 Flashing Instructions

Since you're working in a dev container/codespace, you'll need to flash the ESP32 devices from your local machine. Here are the instructions:

## Option 1: Using PlatformIO Locally (Recommended)

1. **Install PlatformIO locally** (if not already installed):
   ```bash
   pip install platformio
   ```

2. **Clone this repository to your local machine**:
   ```bash
   git clone https://github.com/variousdemeanors/pi_mcp2515.git
   cd pi_mcp2515
   ```

3. **Connect your ESP32 and upload**:
   ```bash
   # For receiver (ESP32-32E Display Board)
   pio run -t upload -e esp32dev-receiver

   # For transmitter (regular ESP32)
   pio run -t upload -e esp32dev-transmitter
   ```

## Option 2: Manual Binary Flashing

If you prefer to use the binaries generated in the codespace:

### Download the Binary Files

The built binaries are located in:
- **Receiver**: `.pio/build/esp32dev-receiver/`
- **Transmitter**: `.pio/build/esp32dev-transmitter/`

Each contains:
- `bootloader.bin`
- `partitions.bin`
- `firmware.bin`

### Flash using ESP Tool

1. **Install esptool** (if not already installed):
   ```bash
   pip install esptool
   ```

2. **Find your ESP32's COM port**:
   - Windows: Check Device Manager (usually COM3, COM4, etc.)
   - Linux: `ls /dev/ttyUSB*` or `ls /dev/ttyACM*`
   - macOS: `ls /dev/cu.usbserial*`

3. **Flash the ESP32**:

   **For Receiver (ESP32-32E Display Board):**
   ```bash
   esptool.py --chip esp32 --port COM3 --baud 921600 write_flash \
     0x1000 bootloader.bin \
     0x8000 partitions.bin \
     0x10000 firmware.bin
   ```

   **For Transmitter:**
   ```bash
   esptool.py --chip esp32 --port COM4 --baud 921600 write_flash \
     0x1000 bootloader.bin \
     0x8000 partitions.bin \
     0x10000 firmware.bin
   ```

   Replace `COM3`/`COM4` with your actual port.

## Option 3: Using Arduino IDE (Alternative)

1. Install ESP32 board support in Arduino IDE
2. Copy the `.ino` files to Arduino IDE
3. Configure the board settings and upload

## Monitoring Serial Output

After flashing, you can monitor the serial output:

```bash
# Using PlatformIO
pio device monitor -b 115200

# Using esptool/pyserial
python -m serial.tools.miniterm COM3 115200
```

## Troubleshooting

- **"Failed to connect"**: Put ESP32 in flash mode by holding BOOT button while pressing RESET
- **Wrong port**: Check Device Manager (Windows) or use `pio device list`
- **Permission denied** (Linux): Add user to dialout group: `sudo usermod -a -G dialout $USER`

## Notes

- The receiver is configured for the ESP32-32E Display Board with proper pin mappings
- The transmitter uses standard ESP32 pins
- Both use ESP-NOW for wireless communication on channel 1
- Baud rate is set to 115200 for serial monitoring
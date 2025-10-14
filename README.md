# LVGL Display Dashboard

A complete ESP32-based automotive pressure monitoring system with LVGL touchscreen interface.

## Features

- **LVGL-based Touch Interface**: Modern automotive-style gauges and controls
- **ESP-NOW Wireless Communication**: Real-time pressure data transmission
- **Dual Pressure Monitoring**: Pre-solenoid and post-solenoid pressure sensors
- **Touch-responsive Controls**: Navigate between live data and statistics screens
- **Working Uptime Counter**: Proper system timing and status display
- **Clean Architecture**: Fresh repository with optimized configurations

## Hardware Requirements

### Receiver (Display Unit)
- ESP32 development board
- 3.2" TFT display with ST7789 driver
- Touch screen interface
- Pin configuration:
  - TFT_CS: GPIO 15
  - TFT_DC: GPIO 2
  - TFT_SCLK: GPIO 14
  - TFT_MOSI: GPIO 13
  - TFT_MISO: GPIO 12
  - TFT_BL: GPIO 27
  - TOUCH_CS: GPIO 33

### Transmitter (Sensor Unit)
- ESP32 development board
- Pressure sensors (analog or I2C)
- Power supply

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/variousdemeanors/LVGL-display-dashboard.git
cd LVGL-display-dashboard
```

### 2. Build and Upload

#### Option A: Direct Upload (Recommended)
Use pre-built firmware for immediate testing:

**Minimal Test (Blinking Screen)**:
- Run task: "Direct: Upload minimal test"
- Should see RED/BLUE blinking screen with uptime counter

**Full LVGL Dashboard**:
- Run task: "Direct: Upload LVGL receiver"
- Complete automotive dashboard with touch interface

#### Option B: Build from Source
```bash
# Build receiver
pio run -e esp32dev-receiver

# Upload receiver
pio run -t upload -e esp32dev-receiver

# Monitor serial output
pio device monitor -b 115200
```

### 3. Setup Transmitter
```bash
# Build and upload transmitter
pio run -t upload -e esp32dev-transmitter
```

## Development

### Project Structure
```
src/
├── receiver/           # LVGL display firmware
│   └── main.cpp       # Complete automotive dashboard
├── transmitter/       # Sensor data transmitter
│   └── main.cpp       # ESP-NOW data sender
└── test_minimal/      # Simple test firmware
    └── main.cpp       # Blinking verification test
```

### Configuration
- **platformio.ini**: Complete build configuration with optimized LVGL settings
- **tasks.json**: VS Code tasks for building and direct firmware upload
- Pin assignments and display settings pre-configured for ESP32 display boards

### Features
- **Touch Calibration**: Pre-configured for ST7789 displays
- **LVGL Integration**: Full v8.x support with custom automotive theme
- **ESP-NOW Protocol**: Reliable wireless sensor communication
- **Statistics Tracking**: Min/max/average pressure monitoring
- **Status Indicators**: Connection status and system uptime

## Troubleshooting

### Upload Issues
1. Use "Direct: Upload minimal test" first to verify upload mechanism
2. Check COM port in tasks.json (default: COM10)
3. Ensure ESP32 is in download mode

### Display Issues
1. Verify pin connections match platformio.ini configuration
2. Check touch calibration values in receiver code
3. Monitor serial output for debugging information

### Communication Issues
1. Ensure both devices use same WiFi channel (default: 1)
2. Check MAC addresses in transmitter code
3. Verify ESP-NOW initialization in serial monitor

## License

This project is open source and available under the MIT License.
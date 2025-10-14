<<<<<<< HEAD
# ESP32 LVGL Automotive Dashboard

A complete ESP32-based automotive pressure monitoring system with LVGL touch interface and ESP-NOW wireless communication.

## 🎯 Features

- **Touch-Responsive Dashboard**: Dual pressure gauges with LVGL interface
- **Wireless Communication**: ESP-NOW between transmitter and receiver
- **ST7789 Display**: 320x240 LCD with landscape orientation
- **Real-time Monitoring**: Live pressure readings with visual gauges
- **Automotive Styling**: Professional dashboard appearance
- **PlatformIO Remote**: Develop in Codespace, upload to local ESP32

## 🏗️ Project Structure

```
src/
├── test_minimal/          # Minimal blinking test for upload verification
├── transmitter/           # ESP-NOW pressure data transmitter
└── receiver/              # LVGL dashboard receiver with touch interface

firmware_builds/           # Pre-built binaries for direct upload
├── minimal_test.bin       # Blinking test firmware
├── lvgl_receiver.bin      # Complete dashboard firmware
├── bootloader.bin         # ESP32 bootloader
├── partitions.bin         # Partition table
└── boot_app0.bin          # Boot application

.vscode/tasks.json         # VS Code build/upload tasks
platformio.ini             # PlatformIO configuration
lv_conf.h                  # LVGL configuration
```

## 🚀 Quick Start

### 1. Hardware Setup
- **ESP32 DevKit** (receiver with display)
- **ST7789 320x240 LCD** with touch
- **ESP32 DevKit** (transmitter with pressure sensors)

### 2. Display Wiring (ST7789)
```
ESP32    →    ST7789
GPIO 23  →    MOSI (SDA)
GPIO 18  →    SCLK (SCL)
GPIO 2   →    DC
GPIO 15  →    CS
GPIO 4   →    RST
3.3V     →    VCC
GND      →    GND
```

### 3. Upload Verification Test

**Always test upload mechanism first:**
- Run task: `Direct: Upload minimal test`
- **Expected**: Red/blue blinking with "NEW REPO" messages
- **Confirms**: Upload mechanism working properly

### 4. Deploy Dashboard

**Once minimal test works:**
- Run task: `Direct: Upload LVGL receiver`
- **Expected**: Complete automotive dashboard with touch gauges

## 📋 Available Tasks

### Build Tasks
- `PIO: Build minimal test` - Compile blinking test
- `PIO: Build receiver` - Compile LVGL dashboard
- `PIO: Build transmitter` - Compile pressure transmitter

### Upload Tasks  
- `Direct: Upload minimal test` - Upload blinking verification
- `Direct: Upload LVGL receiver` - Upload complete dashboard
- `PIO: Upload transmitter` - Upload pressure transmitter

### Development
- `PIO: Monitor` - Serial monitor at 115200 baud

## 🔧 PlatformIO Environments

- **minimal-test**: Simple blinking verification firmware
- **esp32dev-receiver**: Complete LVGL automotive dashboard  
- **esp32dev-transmitter**: ESP-NOW pressure data transmitter

## 📡 ESP-NOW Communication

The system uses ESP-NOW for wireless communication between transmitter and receiver:

- **Transmitter**: Reads pressure sensors, sends data via ESP-NOW
- **Receiver**: Receives pressure data, displays on LVGL dashboard
- **Real-time**: Low latency wireless communication for live updates

## 🎨 Dashboard Features

- **Dual Pressure Gauges**: Primary and secondary pressure displays
- **Touch Interface**: Interactive gauges respond to touch
- **Automotive Styling**: Professional dashboard appearance  
- **Live Updates**: Real-time pressure readings from transmitter
- **Status Indicators**: Connection status and data freshness

## 🐛 Troubleshooting

### Upload Issues
1. **Test minimal firmware first** - Verify upload mechanism works
2. **Check COM port** - Update port in `.vscode/tasks.json`
3. **Use direct upload tasks** - Bypass build dependencies
4. **Try different baud rates** - 115200, 460800, 921600

### Display Issues  
1. **Check wiring** - Verify ST7789 connections
2. **Touch calibration** - May need adjustment for specific display
3. **Orientation** - Currently set to landscape (rotation 1)

### ESP-NOW Issues
1. **Check MAC addresses** - Verify transmitter/receiver pairing
2. **Distance** - Keep devices within range during testing
3. **Power** - Ensure both devices have stable power supply

## 🔄 Development Workflow

1. **Develop in Codespace** - Use browser-based VS Code
2. **PlatformIO Remote** - Build in cloud, upload to local ESP32
3. **Serial Monitoring** - Debug via PlatformIO monitor
4. **Iterative Testing** - Use minimal test for upload verification

## 📖 Technical Details

- **LVGL Version**: 8.4.0 with optimized configuration
- **Display Driver**: TFT_eSPI with ST7789 support  
- **Color Depth**: RGB565 (16-bit) for optimal performance
- **Touch Support**: Resistive touch with calibration
- **Wireless**: ESP-NOW for low-latency communication
- **Build System**: PlatformIO with ESP32 Arduino framework

---

## 🎯 Project Goals

This project demonstrates:
- Professional LVGL interface development
- ESP-NOW wireless communication
- Remote development workflow (Codespace → local ESP32)
- Automotive-style dashboard design
- Real-time sensor monitoring and display
=======
LVGL Port
>>>>>>> 32263cd45bfc211cdf8535048ff2c2b7ebe17ed9

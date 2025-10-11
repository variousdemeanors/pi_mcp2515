# Pressure Sensor System Setup Guide

## Overview
This system consists of two ESP32 devices that communicate wirelessly using ESP-NOW:
1. **Transmitter** (`pressure_sensor_transmitter.ino`) - ESP32 WROVER board with two analog pressure sensors
2. **Receiver** (`pressure_display_receiver.ino`) - 3.2" ESP32-32E Display Board

## Hardware Configuration

### Transmitter (ESP32 WROVER)
- **Sensor 1 (Pre-Solenoid)**: Connected to GPIO 34
- **Sensor 2 (Post-Solenoid)**: Connected to GPIO 35
- Both sensors output 0.5V-4.5V (0-300 PSI range)
- ADC configured for 12-bit resolution with 11dB attenuation (0-3.3V range)

### Receiver (ESP32-32E Display)
- **Display**: 3.2" TFT with ST7789 controller via TFT_eSPI library
- **Features**:
  - Real-time pressure display for both sensors
  - Statistics (Min/Max/Average) tracking
  - Touchscreen reset button

## Communication Setup

### MAC Address Configuration
The transmitter is configured to send data to the receiver's MAC address:
```c++
uint8_t broadcastAddress[] = {0x1C, 0x69, 0x20, 0x95, 0x9F, 0x50};
```

**Important**: This MAC address must match your actual receiver ESP32 board. To find your receiver's MAC address:
1. Upload `get_mac_address.ino` to the receiver board
2. Open Serial Monitor at 115200 baud
3. Copy the MAC address and update `broadcastAddress[]` in `pressure_sensor_transmitter.ino`

### Data Structure
Both devices use the same data structure for communication:
```c++
typedef struct struct_message {
  float pressure1;  // Pre-solenoid pressure in PSI
  float pressure2;  // Post-solenoid pressure in PSI
} struct_message;
```

**Critical**: The data structure MUST be identical on both transmitter and receiver for proper communication.

## Calibration

### Sensor Calibration Formula (Currently in Transmitter)
```c++
pressure1 = 85.979958 * voltage1 - 22.706608;
pressure2 = 177.700058 * voltage2 - 8.912875;
```

These formulas were calibrated for the specific sensors. If you use different sensors, you'll need to recalibrate.

## Upload Instructions

1. **Upload to Transmitter**:
   - Open `pressure_sensor_transmitter.ino` in Arduino IDE
   - Select Board: "ESP32 Dev Module" or "ESP32 Wrover Module"
   - Update the `broadcastAddress[]` with your receiver's MAC
   - Upload

2. **Upload to Receiver**:
   - Open `pressure_display_receiver.ino` in Arduino IDE
   - Select Board: "ESP32 Dev Module"
   - Ensure TFT_eSPI library is properly configured for ESP32-32E
   - Upload

## Testing

1. Power on both devices
2. Open Serial Monitor on transmitter (115200 baud) to see:
   - Sensor readings
   - ESP-NOW send status
3. The receiver display should show:
   - Current pressure readings for both sensors
   - Running statistics (Min/Max/Avg)
   - Yellow "RESET" button to clear statistics

## Troubleshooting

### No Data on Display
- Check MAC address configuration
- Verify both devices are powered on
- Check Serial Monitor on transmitter for "Delivery Success" messages
- Ensure devices are within WiFi range (~30 meters line of sight)

### Incorrect Readings
- Verify sensor wiring to GPIO 34 and 35
- Check sensor power supply (typically 5V)
- Recalibrate using known pressure values
- Verify ADC attenuation setting matches sensor voltage range

### Compilation Errors
- Ensure ESP32 board support is installed (Tools > Board > Board Manager > ESP32)
- Install required libraries: TFT_eSPI, ESP-NOW (built into ESP32 core)
- Use ESP32 Arduino core version 2.0.0 or later

## Technical Notes

- **Update Rate**: Transmitter sends data ~4 times per second (250ms delay)
- **ESP-NOW Protocol**: Connectionless, low-latency communication
- **Range**: Typically 100-200 meters outdoors, 30-50 meters indoors
- **Power Consumption**: Both devices can run on USB or battery power

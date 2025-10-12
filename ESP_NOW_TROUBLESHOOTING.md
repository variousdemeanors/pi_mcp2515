# ESP-NOW Communication Troubleshooting Guide

## Common Issues and Solutions

### 1. ✅ **MAC Address Verification**

**Status**: MAC address `{0x1C, 0x69, 0x20, 0x95, 0x9F, 0x50}` is confirmed correct for the display board.

**Verification Steps**:
1. Upload the fixed transmitter code to verify the MAC addresses match
2. Check transmitter serial output for: `🎯 Target MAC: 1C:69:20:95:9F:50`
3. Check receiver serial output for: `🔍 Receiver MAC: 1C:69:20:95:9F:50`
4. If they don't match exactly, there may be a casing issue or board substitution

**Note**: Since MAC address is confirmed correct, focus on the other issues below.

### 2. 📡 **WiFi Channel Mismatch**

**Problem**: Transmitter and receiver are on different WiFi channels.

**Solution**:
- Both devices must use the same WiFi channel (currently set to channel 1)
- Check that `WIFI_CHANNEL` is identical in both sketches
- Restart both devices after changing

### 3. 🔧 **Data Structure Mismatch**

**Problem**: The `struct_message` definition differs between transmitter and receiver.

**Solution**:
- Ensure the struct definition is **exactly identical** in both sketches
- Pay attention to data types, order, and naming
- The fixed versions include timestamp and packet_id for debugging

### 4. ⚡ **Power Issues**

**Problem**: Insufficient or unstable power supply.

**Solution**:
- Use quality USB cables and power supplies
- Avoid long or thin USB cables
- Try different USB ports
- Consider using external 5V power supply for ESP32

### 5. 📶 **Range and Interference**

**Problem**: Devices are too far apart or WiFi interference.

**Solution**:
- Start with devices close together (1-2 meters)
- Avoid areas with heavy WiFi traffic
- Try different physical orientations
- Check for obstacles (walls, metal objects)

### 6. 🏗️ **ESP32 Board Selection**

**Problem**: Wrong board selected in Arduino IDE.

**Solution**:
- **Transmitter**: Select "ESP32 Dev Module" or "ESP32 Wrover Module"
- **Receiver**: Select "ESP32 Dev Module" 
- Check if your display board has specific requirements

### 7. 📚 **Library Issues**

**Problem**: Missing or incompatible libraries.

**Solution**:
- ESP-NOW is built into ESP32 core (no separate library needed)
- For display: Install **TFT_eSPI** library
- Use ESP32 Arduino Core version 2.0.0 or later
- Update to latest ESP32 core if issues persist

## 🔍 **Diagnostic Steps**

### Step 1: Check Hardware Connections
```
Transmitter (ESP32 WROVER):
- Sensor 1 → GPIO 34
- Sensor 2 → GPIO 35
- Power: 5V or USB
- Ground: Common ground

Receiver (ESP32-32E Display):
- Display: Pre-configured via TFT_eSPI
- Power: 5V or USB
```

### Step 2: Verify MAC Addresses
1. Upload `get_mac_address.ino` to receiver
2. Note the MAC address displayed
3. Update transmitter code with correct MAC
4. Verify in transmitter serial output during setup

### Step 3: Test Communication
1. Upload fixed transmitter code (`pressure_sensor_transmitter_fixed.ino`)
2. Upload fixed receiver code (`pressure_display_receiver_fixed.ino`)
3. Open Serial Monitor on transmitter (115200 baud)
4. Look for "✅ Delivery Success" messages

### Step 4: Use Diagnostic Script
```bash
cd /workspaces/pi_mcp2515/scripts
python3 esp_now_diagnostics.py
```
Select option 1 to monitor transmitter output.

## 📊 **What Success Looks Like**

### Transmitter Serial Output (Good):
```
🚀 ESP-NOW Pressure Sensor Transmitter v6
🔍 Transmitter MAC: AA:BB:CC:DD:EE:FF
🎯 Target MAC: 1C:69:20:95:9F:50
✅ ESP-NOW initialized successfully
✅ Send callback registered
✅ Peer added successfully
📡 Starting transmission...

✅ Packet #1 sent successfully to 1C:69:20:95:9F:50
✅ Packet #2 sent successfully to 1C:69:20:95:9F:50
📊 [10] S1: 45.2 PSI (1.25V, 1548) | S2: 32.1 PSI (0.98V, 1211)
```

### Receiver Serial Output (Good):
```
📺 ESP-NOW Pressure Display Receiver v5
🔍 Receiver MAC: 1C:69:20:95:9F:50
✅ ESP-NOW initialized successfully
✅ Receive callback registered
📡 Receiver ready. Waiting for data...

📨 [#1] Pre: 45.2 PSI | Post: 32.1 PSI
📨 [#2] Pre: 45.3 PSI | Post: 32.0 PSI
```

### Display Should Show:
- **Title**: "WMI Pressure Monitor"
- **Yellow Reset Button**: Top right
- **Real-time pressure values**: Large white text
- **Statistics**: Min/Max/Avg in cyan
- **Green status dot**: When receiving data
- **Packet counter**: At bottom

## 🚨 **Red Flags (Problems)**

### Transmitter Issues:
```
❌ Error initializing ESP-NOW
❌ Failed to add peer
❌ Packet #X failed to 1C:69:20:95:9F:50
⚠️  No successful transmissions in 10 seconds
```

### Receiver Issues:
```
❌ Error initializing ESP-NOW
❌ Invalid data length received
⚠️  Data timeout - no packets received recently
📉 Missed X packets
```

### Display Issues:
- Black screen (power/connection problem)
- "ESP-NOW Init Failed!" (initialization problem)
- Red status dot (no data being received)
- No statistics updating (communication problem)

## 🛠️ **Advanced Debugging**

### Check ESP32 Core Version:
```cpp
// Add this to setup() for version check
Serial.printf("ESP32 Core Version: %s\n", ESP.getSdkVersion());
```

### Monitor Packet Loss:
The fixed receiver code shows packet statistics at the bottom of the display and in serial output.

### Test with Minimal Distance:
Place devices within 1 meter of each other to eliminate range issues.

### Factory Reset ESP32:
If persistent issues occur, try erasing flash:
```bash
esptool --port /dev/ttyUSB0 erase_flash
```

## 📞 **Getting Help**

If issues persist after following this guide:

1. **Document your setup**:
   - ESP32 board models
   - Arduino IDE version
   - ESP32 core version
   - Library versions

2. **Collect debug output**:
   - Full serial output from both devices
   - Photos of display (if applicable)
   - Wiring photos

3. **Test with minimal setup**:
   - Use the diagnostic script
   - Try different ESP32 boards if available
   - Test without sensors (hardcode values)

The fixed code includes extensive debugging output to help identify exactly where communication is failing.
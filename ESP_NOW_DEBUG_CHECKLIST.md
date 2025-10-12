# ESP-NOW Debugging Checklist (MAC Address Confirmed Correct)

Since the MAC address `{0x1C, 0x69, 0x20, 0x95, 0x9F, 0x50}` is confirmed correct for your display board, let's focus on other potential issues.

## 🔍 **Priority Debugging Steps**

### Step 1: Verify ESP32 Core Version Compatibility
```cpp
// Add this to both transmitter and receiver setup():
Serial.printf("ESP32 Core Version: %s\n", ESP.getSdkVersion());
Serial.printf("Arduino Core Version: %s\n", ESP_ARDUINO_VERSION_STR);
```

**Requirements**:
- ESP32 Arduino Core 2.0.0 or later
- Matching versions on both devices recommended

### Step 2: Check WiFi Channel Synchronization
The fixed code sets both devices to channel 1. If there's interference:

```cpp
// Try different channels in both sketches:
#define WIFI_CHANNEL 6   // or 11
```

Common good channels: 1, 6, 11 (avoid channels 2-5, 7-10, 12-13)

### Step 3: Test Power Supply Stability
**Symptoms of power issues**:
- Intermittent "Delivery Fail" messages
- ESP32 resets during transmission
- Inconsistent sensor readings

**Solutions**:
- Use high-quality USB cables (short, thick)
- Try different USB ports or external 5V supply
- Add 100µF capacitor across VCC/GND if needed

### Step 4: Minimize Code for Testing
Create a minimal test version to isolate the problem:

```cpp
// Transmitter test code (remove sensors temporarily)
void loop() {
  sensorReadings.pressure1 = 45.5;  // Fixed test values
  sensorReadings.pressure2 = 32.1;
  sensorReadings.timestamp = millis();
  sensorReadings.packet_id = ++packet_counter;
  
  esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *) &sensorReadings, sizeof(sensorReadings));
  Serial.printf("Test packet #%u: %s\n", packet_counter, 
                result == ESP_OK ? "Sent" : "Failed");
  delay(1000);  // Slower for testing
}
```

### Step 5: Check Board Selection in Arduino IDE
**Critical Settings**:
- **Transmitter**: "ESP32 Dev Module" or "ESP32 Wrover Module"
- **Receiver**: "ESP32 Dev Module" (check your display board documentation)
- **Upload Speed**: 921600 or 115200 (try both)
- **CPU Frequency**: 240MHz
- **Flash Frequency**: 80MHz

### Step 6: Test Physical Proximity
- Place devices 1-2 meters apart initially
- Ensure clear line of sight
- Avoid metal objects between devices
- Try different orientations

### Step 7: Monitor Both Devices Simultaneously
```bash
# Use two terminals or USB ports
# Terminal 1: Monitor transmitter
python3 scripts/esp_now_diagnostics.py  # Option 1

# Terminal 2: Monitor receiver  
python3 scripts/esp_now_diagnostics.py  # Option 2
```

## 🚨 **Common Failure Patterns**

### Pattern 1: "Failed to add peer" 
```
❌ Failed to add peer: ESP_ERR_ESPNOW_NOT_INIT
```
**Fix**: ESP-NOW initialization issue, check ESP32 core version

### Pattern 2: "Delivery Fail" but ESP-NOW initializes
```
✅ ESP-NOW initialized successfully
❌ Packet #1 failed to 1C:69:20:95:9F:50
```
**Fix**: Channel mismatch, power issues, or range problems

### Pattern 3: Receiver never receives data
```
Transmitter: ✅ Packet sent successfully
Receiver: (no "📨 Received" messages)
```
**Fix**: Receiver ESP-NOW callback not registered or channel mismatch

### Pattern 4: Intermittent communication
```
✅ Packet #1 sent successfully
❌ Packet #2 failed
✅ Packet #3 sent successfully
```
**Fix**: Power supply instability or RF interference

## 🔧 **Advanced Debugging Commands**

### Check ESP32 Memory and Status:
```cpp
// Add to setup() for both devices:
Serial.printf("Free heap: %d bytes\n", ESP.getFreeHeap());
Serial.printf("CPU Frequency: %d MHz\n", ESP.getCpuFreqMHz());
Serial.printf("Flash size: %d bytes\n", ESP.getFlashChipSize());
```

### Force Channel and Power Settings:
```cpp
// In setup(), after WiFi.mode(WIFI_STA):
esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);
esp_wifi_set_max_tx_power(78);  // Maximum power (19.5 dBm)
```

### Test with Different Data Sizes:
```cpp
// Try smaller data structure to test:
typedef struct test_message {
  float value1;
  float value2;
} test_message;
```

## 📋 **Systematic Testing Protocol**

1. **Hardware Test**: Upload minimal ESP-NOW example to both boards
2. **Range Test**: Start with devices 50cm apart
3. **Channel Test**: Try channels 1, 6, and 11
4. **Power Test**: Use external power supplies
5. **Core Test**: Verify ESP32 Arduino core versions match
6. **Interference Test**: Test in different physical locations

## 🎯 **Quick Win Attempts**

Try these quick fixes first:

1. **Restart both ESP32s**: Power cycle both devices
2. **Different USB ports**: Try different computers/ports
3. **Swap ESP32 roles**: Test transmitter code on display board
4. **Factory reset**: Erase flash completely and reprogram
5. **Different ESP32 boards**: Test with known-good ESP32 if available

The enhanced debugging in the fixed code will show exactly where the failure occurs. Focus on the specific error messages to narrow down the root cause.
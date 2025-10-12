/*
  ESP-NOW Simple Test Receiver
  
  Minimal version for testing ESP-NOW communication with the display board.
  Use this to isolate communication issues from display/UI problems.
  
  Expected MAC address: {0x1C, 0x69, 0x20, 0x95, 0x9F, 0x50}
*/

#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <SPI.h>
#include <TFT_eSPI.h>

TFT_eSPI tft = TFT_eSPI();

// Test data structure (must match transmitter)
typedef struct struct_message {
  float pressure1;
  float pressure2;
  uint32_t timestamp;
  uint32_t packet_id;
} struct_message;

struct_message receivedData;
uint32_t total_received = 0;
uint32_t last_packet_id = 0;
uint32_t missed_packets = 0;
unsigned long last_receive_time = 0;
bool display_available = true;

void printSystemInfo() {
  Serial.println("🔍 SYSTEM INFORMATION:");
  Serial.printf("ESP32 Core: %s\n", ESP.getSdkVersion());
  Serial.printf("Free Heap: %d bytes\n", ESP.getFreeHeap());
  Serial.printf("CPU Freq: %d MHz\n", ESP.getCpuFreqMHz());
  
  uint8_t mac[6];
  WiFi.macAddress(mac);
  Serial.printf("Receiver MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  Serial.printf("Expected MAC: 1C:69:20:95:9F:50\n");
  
  if (mac[0] == 0x1C && mac[1] == 0x69 && mac[2] == 0x20 && 
      mac[3] == 0x95 && mac[4] == 0x9F && mac[5] == 0x50) {
    Serial.println("✅ MAC ADDRESS MATCH CONFIRMED!");
  } else {
    Serial.println("❌ WARNING: MAC address doesn't match expected value!");
    Serial.println("   Update transmitter with correct MAC address:");
    Serial.printf("   uint8_t broadcastAddress[] = {0x%02X, 0x%02X, 0x%02X, 0x%02X, 0x%02X, 0x%02X};\n",
                  mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  }
  Serial.println();
}

// Helper for Arduino core version comparison if not defined
#ifndef ESP_ARDUINO_VERSION_VAL
#define ESP_ARDUINO_VERSION_VAL(major, minor, patch) ((major << 16) | (minor << 8) | (patch))
#endif

// ESP-NOW receive callback (version-guarded)
#if defined(ESP_ARDUINO_VERSION) && (ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3,0,0))
void OnDataRecv(const uint8_t *mac_addr, const uint8_t *incomingData, int len) {
#else
void OnDataRecv(const esp_now_recv_info *recv_info, const uint8_t *incomingData, int len) {
#endif
  // Validate packet size
  if (len != sizeof(struct_message)) {
    Serial.printf("❌ Bad packet size: %d (expected %d)\n", len, sizeof(struct_message));
    return;
  }
  
  // Copy data
  memcpy(&receivedData, incomingData, sizeof(receivedData));
  total_received++;
  
  // Check for missed packets
  if (last_packet_id > 0 && receivedData.packet_id > last_packet_id + 1) {
    uint32_t missed = receivedData.packet_id - last_packet_id - 1;
    missed_packets += missed;
    Serial.printf("⚠️  Missed %u packets (got #%u, expected #%u)\n", 
                  missed, receivedData.packet_id, last_packet_id + 1);
  }
  
  last_packet_id = receivedData.packet_id;
  last_receive_time = millis();
  
  // Print received data
  Serial.printf("📨 Packet #%u: P1=%.1f PSI, P2=%.1f PSI\n", 
                receivedData.packet_id, receivedData.pressure1, receivedData.pressure2);
  
  // Update simple display
  if (display_available) {
    updateDisplay();
  }
  
  // Print statistics every 10 packets
  if (total_received % 10 == 0) {
    float loss_rate = (float)missed_packets / (total_received + missed_packets) * 100.0;
    Serial.printf("📊 Total: %u | Missed: %u | Loss: %.1f%%\n", 
                  total_received, missed_packets, loss_rate);
  }
}

void updateDisplay() {
  // Clear old data area
  tft.fillRect(0, 60, 320, 120, TFT_BLACK);
  
  // Display current values
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(3);
  tft.setCursor(10, 70);
  tft.printf("P1: %.1f PSI", receivedData.pressure1);
  tft.setCursor(10, 110);
  tft.printf("P2: %.1f PSI", receivedData.pressure2);
  
  // Display packet info
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 150);
  tft.printf("Packet #%u", receivedData.packet_id);
  
  // Display statistics
  tft.setTextSize(1);
  tft.setCursor(10, 180);
  tft.printf("Received: %u | Missed: %u", total_received, missed_packets);
  
  // Connection status indicator
  unsigned long time_since_last = millis() - last_receive_time;
  if (time_since_last < 2000) {
    tft.fillCircle(300, 20, 8, TFT_GREEN);
    tft.setTextColor(TFT_GREEN);
    tft.setCursor(250, 30);
    tft.print("ONLINE");
  } else {
    tft.fillCircle(300, 20, 8, TFT_RED);
    tft.setTextColor(TFT_RED);
    tft.setCursor(240, 30);
    tft.print("TIMEOUT");
  }
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("🧪 ESP-NOW TEST RECEIVER");
  Serial.println("=========================");
  
  // Initialize display
  Serial.println("📺 Initializing display...");
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 10);
  tft.print("ESP-NOW Test Receiver");
  tft.setTextSize(1);
  tft.setCursor(10, 40);
  tft.print("Waiting for data...");
  
  // Print system information
  printSystemInfo();
  
  // Initialize WiFi
  WiFi.mode(WIFI_STA);
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);
  
  Serial.println("📡 WiFi initialized (Station mode, Channel 1)");
  
  // Initialize ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("❌ CRITICAL: ESP-NOW initialization failed!");
    tft.fillScreen(TFT_RED);
    tft.setTextColor(TFT_WHITE, TFT_RED);
    tft.setCursor(10, 50);
    tft.print("ESP-NOW INIT FAILED!");
    while(1) {
      delay(1000);
      Serial.println("💀 HALTED - Fix ESP-NOW init issue");
    }
  }
  
  Serial.println("✅ ESP-NOW initialized successfully");
  
  // Register receive callback
  if (esp_now_register_recv_cb(OnDataRecv) != ESP_OK) {
    Serial.println("❌ WARNING: Receive callback registration failed");
  } else {
    Serial.println("✅ Receive callback registered");
  }
  
  Serial.println("🎯 Ready to receive test packets");
  Serial.println("   (Watch for 📨 Packet messages)\n");
  
  last_receive_time = millis();
}

void loop() {
  // Check for communication timeout
  unsigned long time_since_last = millis() - last_receive_time;
  
  if (time_since_last > 5000) {  // 5 second timeout
    static unsigned long last_timeout_msg = 0;
    if (millis() - last_timeout_msg > 5000) {
      Serial.println("⚠️  No data received for 5+ seconds");
      Serial.println("   Check transmitter power and operation");
      last_timeout_msg = millis();
    }
  }
  
  // Update display timeout indicator
  if (display_available && time_since_last > 1000) {
    static unsigned long last_display_update = 0;
    if (millis() - last_display_update > 1000) {
      updateDisplay();  // Update timeout indicator
      last_display_update = millis();
    }
  }
  
  delay(100);
}

/*
  EXPECTED OUTPUT (Success):
  🧪 ESP-NOW TEST RECEIVER
  =========================
  📺 Initializing display...
  🔍 SYSTEM INFORMATION:
  ESP32 Core: v4.4.7-dirty
  Receiver MAC: 1C:69:20:95:9F:50
  Expected MAC: 1C:69:20:95:9F:50
  ✅ MAC ADDRESS MATCH CONFIRMED!

  📡 WiFi initialized (Station mode, Channel 1)
  ✅ ESP-NOW initialized successfully
  ✅ Receive callback registered
  🎯 Ready to receive test packets

  📨 Packet #1: P1=45.0 PSI, P2=30.0 PSI
  📨 Packet #2: P1=46.0 PSI, P2=31.0 PSI
  📊 Total: 10 | Missed: 0 | Loss: 0.0%
  
  EXPECTED OUTPUT (No Communication):
  ⚠️  No data received for 5+ seconds
     Check transmitter power and operation
*/
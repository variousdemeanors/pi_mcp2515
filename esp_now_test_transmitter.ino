/*
  ESP-NOW Simple Test Transmitter
  
  Minimal version for testing ESP-NOW communication without sensors.
  Use this to isolate communication issues from sensor/hardware problems.
  
  MAC address confirmed: {0x1C, 0x69, 0x20, 0x95, 0x9F, 0x50}
*/

#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>

// Confirmed MAC address of your display board
uint8_t broadcastAddress[] = {0x1C, 0x69, 0x20, 0x95, 0x9F, 0x50};

// Simple test data structure
typedef struct struct_message {
  float pressure1;
  float pressure2;
  uint32_t timestamp;
  uint32_t packet_id;
} struct_message;

struct_message testData;
uint32_t packet_counter = 0;
uint32_t success_count = 0;
uint32_t fail_count = 0;

// Helper for Arduino core version comparison if not defined
#ifndef ESP_ARDUINO_VERSION_VAL
#define ESP_ARDUINO_VERSION_VAL(major, minor, patch) ((major << 16) | (minor << 8) | (patch))
#endif

// ESP-NOW send callback (version-guarded for ESP32 core 2.x vs 3.x)
#if defined(ESP_ARDUINO_VERSION) && (ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3,0,0))
void OnDataSent(const wifi_tx_info_t *tx_info, esp_now_send_status_t status) {
  (void)tx_info; // Destination MAC not exposed consistently in 3.x; ignore
#else
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
#endif
  if (status == ESP_NOW_SEND_SUCCESS) {
    success_count++;
    #if defined(ESP_ARDUINO_VERSION) && (ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3,0,0))
      Serial.printf("✅ SUCCESS: Packet #%u delivered\n", packet_counter);
    #else
      Serial.printf("✅ SUCCESS: Packet #%u delivered to %02X:%02X:%02X:%02X:%02X:%02X\n", 
                    packet_counter, mac_addr[0], mac_addr[1], mac_addr[2], 
                    mac_addr[3], mac_addr[4], mac_addr[5]);
    #endif
  } else {
    fail_count++;
    #if defined(ESP_ARDUINO_VERSION) && (ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3,0,0))
      Serial.printf("❌ FAILED: Packet #%u not delivered\n", packet_counter);
    #else
      Serial.printf("❌ FAILED: Packet #%u not delivered to %02X:%02X:%02X:%02X:%02X:%02X\n", 
                    packet_counter, mac_addr[0], mac_addr[1], mac_addr[2], 
                    mac_addr[3], mac_addr[4], mac_addr[5]);
    #endif
  }
  
  // Print success rate every 10 packets
  if (packet_counter % 10 == 0) {
    float rate = packet_counter ? ((float)success_count / packet_counter * 100.0f) : 0.0f;
    Serial.printf("📊 Success Rate: %.1f%% (%u/%u)\n", rate, success_count, packet_counter);
  }
}

void printSystemInfo() {
  Serial.println("🔍 SYSTEM INFORMATION:");
  Serial.printf("ESP32 Core (SDK): %s\n", ESP.getSdkVersion());
#ifdef ESP_ARDUINO_VERSION
  Serial.printf("Arduino Core: %d.%d.%d\n", 
                (ESP_ARDUINO_VERSION >> 16) & 0xFF, 
                (ESP_ARDUINO_VERSION >> 8) & 0xFF, 
                ESP_ARDUINO_VERSION & 0xFF);
#endif
  Serial.printf("Free Heap: %d bytes\n", ESP.getFreeHeap());
  Serial.printf("CPU Freq: %d MHz\n", ESP.getCpuFreqMHz());
  
  uint8_t mac[6];
  WiFi.macAddress(mac);
  Serial.printf("Transmitter MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  Serial.printf("Target MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                broadcastAddress[0], broadcastAddress[1], broadcastAddress[2],
                broadcastAddress[3], broadcastAddress[4], broadcastAddress[5]);
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("🧪 ESP-NOW COMMUNICATION TEST");
  Serial.println("==============================");
  
  // Print system information
  printSystemInfo();
  
  // Initialize WiFi
  WiFi.mode(WIFI_STA);
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);
  
  Serial.println("📡 WiFi initialized (Station mode, Channel 1)");
  
  // Initialize ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("❌ CRITICAL: ESP-NOW initialization failed!");
    Serial.println("   - Check ESP32 board selection");
    Serial.println("   - Verify ESP32 core version");
    Serial.println("   - Try different USB port/cable");
    while(1) {
      delay(1000);
      Serial.println("💀 HALTED - Fix ESP-NOW init issue");
    }
  }
  
  Serial.println("✅ ESP-NOW initialized successfully");
  
  // Register send callback
  if (esp_now_register_send_cb(OnDataSent) != ESP_OK) {
    Serial.println("❌ WARNING: Send callback registration failed");
  } else {
    Serial.println("✅ Send callback registered");
  }
  
  // Add peer
  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(esp_now_peer_info_t));
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 1;
  peerInfo.encrypt = false;
  peerInfo.ifidx = WIFI_IF_STA;
  
  esp_err_t add_result = esp_now_add_peer(&peerInfo);
  if (add_result != ESP_OK) {
    Serial.printf("❌ CRITICAL: Add peer failed - %s\n", esp_err_to_name(add_result));
    Serial.println("   - Verify target MAC address");
    Serial.println("   - Check WiFi channel settings");
    while(1) {
      delay(1000);
      Serial.println("💀 HALTED - Fix peer add issue");
    }
  }
  
  Serial.println("✅ Peer added successfully");
  Serial.println("🚀 Starting test transmission...");
  Serial.println("   (Watch for ✅ SUCCESS or ❌ FAILED messages)\n");
}

void loop() {
  // Generate test data (simulating sensor readings)
  testData.pressure1 = 45.0 + (packet_counter % 10);  // 45-54 PSI
  testData.pressure2 = 30.0 + (packet_counter % 8);   // 30-37 PSI
  testData.timestamp = millis();
  testData.packet_id = ++packet_counter;
  
  // Send test packet
  esp_err_t result = esp_now_send(broadcastAddress, (uint8_t*)&testData, sizeof(testData));
  
  if (result != ESP_OK) {
    Serial.printf("🚨 ESP-NOW send failed: %s\n", esp_err_to_name(result));
  }
  
  // Show test values every 5 packets
  if (packet_counter % 5 == 0) {
    Serial.printf("📤 Packet #%u: P1=%.1f, P2=%.1f\n", 
                  packet_counter, testData.pressure1, testData.pressure2);
  }
  
  delay(1000);  // Send every second for easy monitoring
}

/*
  EXPECTED OUTPUT (Success):
  🧪 ESP-NOW COMMUNICATION TEST
  ==============================
  🔍 SYSTEM INFORMATION:
  ESP32 Core: v4.4.7-dirty
  Free Heap: 295516 bytes
  CPU Freq: 240 MHz
  Transmitter MAC: AA:BB:CC:DD:EE:FF
  Target MAC: 1C:69:20:95:9F:50

  📡 WiFi initialized (Station mode, Channel 1)
  ✅ ESP-NOW initialized successfully
  ✅ Send callback registered
  ✅ Peer added successfully
  🚀 Starting test transmission...

  ✅ SUCCESS: Packet #1 delivered
  ✅ SUCCESS: Packet #2 delivered
  📤 Packet #5: P1=49.0, P2=34.0
  ✅ SUCCESS: Packet #5 delivered
  📊 Success Rate: 100.0% (10/10)
  
  EXPECTED OUTPUT (Failure):
  ❌ FAILED: Packet #1 not delivered
  ❌ FAILED: Packet #2 not delivered
  📊 Success Rate: 0.0% (0/10)
*/
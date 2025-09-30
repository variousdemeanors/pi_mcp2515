# ESP32 Methanol Pressure Sensors (Sends data via ESP-NOW)
# Flash this to the ESP32 connected to methanol pressure sensors

#include <WiFi.h>
#include <esp_now.h>

// Pressure sensor pins
#define PRESSURE_PRE_PIN 34   // ADC pin for pre-solenoid pressure sensor
#define PRESSURE_POST_PIN 35  // ADC pin for post-solenoid pressure sensor

// ESP-NOW setup
uint8_t coordinatorMac[] = {0xB0, 0xB2, 0x1C, 0x09, 0xD8, 0x3C};

// Methanol sensor data structure
typedef struct {
  float pressurePre;   // PSI
  float pressurePost;  // PSI
} MethanolData;

MethanolData methanolData;

// Convert ADC reading to PSI (calibrate based on your sensor specs)
// Assuming 0.5V-4.5V = 0-300PSI linear relationship
float adcToPsi(int adcValue) {
  // ADC range: 0-4095 for ESP32 (12-bit)
  // Voltage range: 0.5V-4.5V = 0-300PSI
  // ADC values: ~205-3686 (0.5V/3.3V*4095 ≈ 205, 4.5V/3.3V*4095 ≈ 3686)

  const float minVoltage = 0.5;
  const float maxVoltage = 4.5;
  const float maxPsi = 300.0;
  const float adcMin = (minVoltage / 3.3) * 4095;
  const float adcMax = (maxVoltage / 3.3) * 4095;

  if (adcValue < adcMin) return 0.0;
  if (adcValue > adcMax) return maxPsi;

  return ((adcValue - adcMin) / (adcMax - adcMin)) * maxPsi;
}

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 Methanol Pressure Sensors starting...");

  // Initialize ADC pins
  pinMode(PRESSURE_PRE_PIN, INPUT);
  pinMode(PRESSURE_POST_PIN, INPUT);

  // Initialize ESP-NOW
  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }

  // Register send callback (optional)
  // esp_now_register_send_cb([](const uint8_t *mac_addr, esp_now_send_status_t status) {
  //   Serial.print("Send status: ");
  //   Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Success" : "Fail");
  // });

  // Add coordinator as peer
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, coordinatorMac, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add coordinator peer");
    return;
  }

  Serial.println("Setup complete - methanol sensors ready");
}

void loop() {
  // Read pressure sensors
  int adcPre = analogRead(PRESSURE_PRE_PIN);
  int adcPost = analogRead(PRESSURE_POST_PIN);

  // Convert to PSI
  methanolData.pressurePre = adcToPsi(adcPre);
  methanolData.pressurePost = adcToPsi(adcPost);

  // Send data via ESP-NOW
  esp_now_send(coordinatorMac, (uint8_t *)&methanolData, sizeof(MethanolData));

  // Debug output
  Serial.printf("Pre: %.1f PSI, Post: %.1f PSI\n", methanolData.pressurePre, methanolData.pressurePost);

  delay(100); // 10Hz
}
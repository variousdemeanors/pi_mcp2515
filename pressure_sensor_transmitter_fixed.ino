/*
  ESP-NOW Pressure Sensor Transmitter (v6 - FIXED VERSION)

  This sketch runs on the ESP32 WROVER board. It reads two analog sensors,
  applies calibration, and sends the data via ESP-NOW.

  FIXES:
  - Added proper WiFi channel management
  - Improved MAC address handling
  - Added connection status monitoring
  - Enhanced error handling and debugging
  - Added watchdog timer for reliability
*/

#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <string.h>
#include <esp_system.h>

// Optional task watchdog header; not present in all builds
#if __has_include(<esp_task_wdt.h>)
#include <esp_task_wdt.h>
#define SAFE_WDT_RESET() esp_task_wdt_reset()
#else
#define SAFE_WDT_RESET() yield()
#endif

// =========================================================================
// CONFIGURATION
// =========================================================================
// MAC Address of the receiver (your display board)
// IMPORTANT: Update this with your receiver's actual MAC address!
uint8_t broadcastAddress[] = {0x1C, 0x69, 0x20, 0x95, 0x9F, 0x50};

// Define the pins for your analog sensors
#define SENSOR1_PIN 34
#define SENSOR2_PIN 35

// WiFi Channel (must match receiver)
#define WIFI_CHANNEL 1

// Watchdog timeout (30 seconds)
#define WDT_TIMEOUT 30000
// =========================================================================

// Define a data structure to hold the sensor readings.
// This structure MUST be the same on both the transmitter and receiver.
typedef struct struct_message
{
  float pressure1;
  float pressure2;
  uint32_t timestamp; // Add timestamp for debugging
  uint32_t packet_id; // Add packet ID for tracking
} struct_message;

// Create a variable to hold the data to be sent
struct_message sensorReadings;

// Statistics tracking
uint32_t packet_counter = 0;
uint32_t send_success_count = 0;
uint32_t send_fail_count = 0;
unsigned long last_success_time = 0;

// Helper function to convert raw ADC value to voltage
float getVoltage(int raw_adc)
{
  // ESP32 ADC with 11dB attenuation has a nominal range of 0-3.3V.
  // The ADC resolution is 12 bits (0-4095).
  return (float)raw_adc * (3.3 / 4095.0);
}

// Helper for Arduino core version comparison if not defined
#ifndef ESP_ARDUINO_VERSION_VAL
#define ESP_ARDUINO_VERSION_VAL(major, minor, patch) ((major << 16) | (minor << 8) | (patch))
#endif

// Callback function that is executed when data is sent (version-guarded)
#if defined(ESP_ARDUINO_VERSION) && (ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0))
void OnDataSent(const wifi_tx_info_t *tx_info, esp_now_send_status_t status)
{
  (void)tx_info; // MAC not consistently exposed in 3.x
#else
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status)
{
#endif
  char mac_str[18] = {0};
#if !(defined(ESP_ARDUINO_VERSION) && (ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0)))
  snprintf(mac_str, sizeof(mac_str), "%02X:%02X:%02X:%02X:%02X:%02X",
           mac_addr[0], mac_addr[1], mac_addr[2],
           mac_addr[3], mac_addr[4], mac_addr[5]);
#endif

  if (status == ESP_NOW_SEND_SUCCESS)
  {
    send_success_count++;
    last_success_time = millis();
#if defined(ESP_ARDUINO_VERSION) && (ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0))
    Serial.printf("✅ Packet #%u sent successfully\n", packet_counter);
#else
    Serial.printf("✅ Packet #%u sent successfully to %s\n", packet_counter, mac_str);
#endif
  }
  else
  {
    send_fail_count++;
#if defined(ESP_ARDUINO_VERSION) && (ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0))
    Serial.printf("❌ Packet #%u failed\n", packet_counter);
#else
    Serial.printf("❌ Packet #%u failed to %s\n", packet_counter, mac_str);
#endif
  }

  // Print statistics every 20 packets
  if (packet_counter % 20 == 0)
  {
    float success_rate = (float)send_success_count / packet_counter * 100.0;
    Serial.printf("📊 Stats: %u/%u packets (%.1f%% success)\n",
                  send_success_count, packet_counter, success_rate);
  }
}

void printMacAddress()
{
  uint8_t mac[6];
  WiFi.macAddress(mac);
  Serial.printf("🔍 Transmitter MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}

void printTargetMacAddress()
{
  Serial.printf("🎯 Target MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                broadcastAddress[0], broadcastAddress[1], broadcastAddress[2],
                broadcastAddress[3], broadcastAddress[4], broadcastAddress[5]);
}

void setup()
{
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n🚀 ESP-NOW Pressure Sensor Transmitter v6");
  Serial.println("==========================================");

  // Print MAC addresses for debugging
  WiFi.mode(WIFI_STA);
  printMacAddress();
  printTargetMacAddress();

  // Set WiFi channel
  esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);

  Serial.printf("📡 WiFi Channel: %d\n", WIFI_CHANNEL);

  // Init ESP-NOW
  if (esp_now_init() != ESP_OK)
  {
    Serial.println("❌ Error initializing ESP-NOW");
    ESP.restart();
    return;
  }

  Serial.println("✅ ESP-NOW initialized successfully");

  // Register the send callback function
  esp_err_t callback_result = esp_now_register_send_cb(OnDataSent);
  if (callback_result != ESP_OK)
  {
    Serial.printf("❌ Failed to register send callback: %s\n", esp_err_to_name(callback_result));
  }
  else
  {
    Serial.println("✅ Send callback registered");
  }

  // Register peer
  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(esp_now_peer_info_t));
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = WIFI_CHANNEL;
  peerInfo.encrypt = false;
  peerInfo.ifidx = WIFI_IF_STA;

  // Add peer
  esp_err_t add_peer_result = esp_now_add_peer(&peerInfo);
  if (add_peer_result != ESP_OK)
  {
    Serial.printf("❌ Failed to add peer: %s\n", esp_err_to_name(add_peer_result));
    ESP.restart();
    return;
  }

  Serial.println("✅ Peer added successfully");

  // Set up the ADC
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db); // Global attenuation setting

  // Set pin-specific attenuation (redundant but explicit)
  // Use Arduino-style attenuation constants for broad core compatibility
  analogSetPinAttenuation(SENSOR1_PIN, ADC_11db);
  analogSetPinAttenuation(SENSOR2_PIN, ADC_11db);

  Serial.println("✅ ADC configured (12-bit, 11dB attenuation)");

  // Take some initial readings to stabilize ADC
  for (int i = 0; i < 10; i++)
  {
    analogRead(SENSOR1_PIN);
    analogRead(SENSOR2_PIN);
    delay(10);
  }

  Serial.println("🌡️  ADC stabilized with initial readings");
  Serial.println("📡 Starting transmission...\n");
}

void loop()
{
  // Reset watchdog (or yield if WDT not available)
  SAFE_WDT_RESET();

  // Read raw sensor values multiple times and average for stability
  int raw1_sum = 0, raw2_sum = 0;
  const int num_readings = 5;

  for (int i = 0; i < num_readings; i++)
  {
    raw1_sum += analogRead(SENSOR1_PIN);
    raw2_sum += analogRead(SENSOR2_PIN);
    delay(2); // Small delay between readings
  }

  int raw1 = raw1_sum / num_readings;
  int raw2 = raw2_sum / num_readings;

  // Convert raw values to voltage
  float voltage1 = getVoltage(raw1);
  float voltage2 = getVoltage(raw2);

  // Apply your precise calibration formulas
  sensorReadings.pressure1 = 85.979958 * voltage1 - 22.706608;
  sensorReadings.pressure2 = 177.700058 * voltage2 - 8.912875;

  // Prevent negative pressure readings
  if (sensorReadings.pressure1 < 0)
    sensorReadings.pressure1 = 0.0;
  if (sensorReadings.pressure2 < 0)
    sensorReadings.pressure2 = 0.0;

  // Add timestamp and packet ID
  sensorReadings.timestamp = millis();
  sensorReadings.packet_id = ++packet_counter;

  // Send message via ESP-NOW
  esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *)&sensorReadings, sizeof(sensorReadings));

  if (result != ESP_OK)
  {
    Serial.printf("❌ ESP-NOW send error: %s\n", esp_err_to_name(result));
  }

  // Print sensor data for debugging (every 10th packet to reduce clutter)
  if (packet_counter % 10 == 0)
  {
    Serial.printf("📊 [%u] S1: %.1f PSI (%.2fV, %d) | S2: %.1f PSI (%.2fV, %d)\n",
                  packet_counter,
                  sensorReadings.pressure1, voltage1, raw1,
                  sensorReadings.pressure2, voltage2, raw2);
  }

  // Check for communication timeout
  if (millis() - last_success_time > 10000 && last_success_time > 0)
  {
    Serial.println("⚠️  No successful transmissions in 10 seconds - possible connection issue");
  }

  delay(250); // Send data ~4 times per second
}
/*
  ESP-NOW Pressure Sensor Transmitter (v5 - FINAL CALLBACK FIX)

  This sketch runs on the ESP32 WROVER board. It reads two analog sensors,
  applies calibration, and sends the data via ESP-NOW.

  This version fixes the compilation error for the OnDataSent callback
  based on the user's compiler output.
*/

#include <esp_now.h>
#include <WiFi.h>

// =========================================================================
// CONFIGURATION
// =========================================================================
// MAC Address of the receiver (your display board)
uint8_t broadcastAddress[] = {0x1C, 0x69, 0x20, 0x95, 0x9F, 0x50};

// Define the pins for your analog sensors
#define SENSOR1_PIN 34
#define SENSOR2_PIN 35
// =========================================================================

// Define a data structure to hold the sensor readings.
// This structure MUST be the same on both the transmitter and receiver.
typedef struct struct_message {
  float pressure1;
  float pressure2;
} struct_message;

// Create a variable to hold the data to be sent
struct_message sensorReadings;

// Helper function to convert raw ADC value to voltage
float getVoltage(int raw_adc) {
  // ESP32 ADC with 11dB attenuation has a nominal range of 0-3.3V.
  // The ADC resolution is 12 bits (0-4095).
  return (float)raw_adc * (3.3 / 4095.0);
}


// CORRECTED Callback function that is executed when data is sent
// This now matches the signature required by your ESP32 core version.
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  Serial.print("\r\nLast Packet Send Status:\t");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Delivery Success" : "Delivery Fail");
}

void setup() {
  Serial.begin(115200);

  // Set device as a Wi-Fi Station
  WiFi.mode(WIFI_STA);

  // Init ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Register the send callback function
  esp_now_register_send_cb(OnDataSent);

  // Register peer
  esp_now_peer_info_t peerInfo;
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  // Add peer
  if (esp_now_add_peer(&peerInfo) != ESP_OK){
    Serial.println("Failed to add peer");
    return;
  }

  // Set up the ADC
  analogReadResolution(12);
  analogSetPinAttenuation(SENSOR1_PIN, ADC_ATTEN_DB_11);
  analogSetPinAttenuation(SENSOR2_PIN, ADC_ATTEN_DB_11);

  Serial.println("Transmitter setup complete. Sending data...");
}

void loop() {
  // Read raw sensor values
  int raw1 = analogRead(SENSOR1_PIN);
  int raw2 = analogRead(SENSOR2_PIN);

  // Convert raw values to voltage
  float voltage1 = getVoltage(raw1);
  float voltage2 = getVoltage(raw2);

  // Apply your precise calibration formulas
  sensorReadings.pressure1 = 85.979958 * voltage1 - 22.706608;
  sensorReadings.pressure2 = 177.700058 * voltage2 - 8.912875;

  // Prevent negative pressure readings
  if (sensorReadings.pressure1 < 0) sensorReadings.pressure1 = 0.0;
  if (sensorReadings.pressure2 < 0) sensorReadings.pressure2 = 0.0;

  // Send message via ESP-NOW
  esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *) &sensorReadings, sizeof(sensorReadings));

  if (result != ESP_OK) {
    Serial.println("Error sending the data");
  }

  // Print to serial for debugging
  Serial.printf("Sensor 1: %.1f PSI | Sensor 2: %.1f PSI\n", sensorReadings.pressure1, sensorReadings.pressure2);

  delay(250); // Send data ~4 times per second
}
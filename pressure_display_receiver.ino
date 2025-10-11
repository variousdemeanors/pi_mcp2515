/*
  ESP-NOW Pressure Display Receiver (v2 - Correct Labels)

  This sketch runs on the 3.2" ESP32-32E Display Board.
  It receives pressure data wirelessly via ESP-NOW from the transmitter board
  and displays it on the ST7789 TFT screen with corrected labels.
*/

#include <esp_now.h>
#include <WiFi.h>
#include <SPI.h>
#include <TFT_eSPI.h>

// Create an instance of the TFT_eSPI library
TFT_eSPI tft = TFT_eSPI();

// Define a data structure to hold the incoming sensor readings.
// This structure MUST be the same on both the transmitter and receiver.
typedef struct struct_message {
  float pressure1;
  float pressure2;
} struct_message;

// Create a variable to hold the received data
struct_message sensorReadings;

// Flag to indicate when new data has been received
volatile bool newData = false;

// Callback function that is executed when data is received
void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {
  memcpy(&sensorReadings, incomingData, sizeof(sensorReadings));
  newData = true; // Set the flag to true
}

void setup() {
  Serial.begin(115200);

  // Initialize the TFT display
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);

  tft.setCursor(10, 10);
  tft.setTextSize(2); // Slightly smaller text for the title
  tft.println("WMI Pressure Monitor");
  tft.setTextSize(3); // Larger text for the data

  // Set device as a Wi-Fi Station
  WiFi.mode(WIFI_STA);

  // Initialize ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    tft.setCursor(10, 50);
    tft.println("ESP-NOW Init Failed!");
    return;
  }

  // Register the receive callback function
  esp_now_register_recv_cb(OnDataRecv);

  Serial.println("Receiver setup complete. Waiting for data...");
}

void loop() {
  // Check if new data has arrived
  if (newData) {
    newData = false; // Reset the flag

    // Display Sensor 1: Pre-Solenoid
    tft.setCursor(10, 60);
    tft.print("Pre-Solenoid: ");
    tft.print(sensorReadings.pressure1, 1);
    tft.print(" PSI "); // Add units and padding

    // Display Sensor 2: Post-Solenoid
    tft.setCursor(10, 110);
    tft.print("Post-Solenoid:");
    tft.print(sensorReadings.pressure2, 1);
    tft.print(" PSI ");

    // Print to Serial monitor for debugging
    Serial.printf("Received Data -> Pre: %.1f PSI, Post: %.1f PSI\n", sensorReadings.pressure1, sensorReadings.pressure2);
  }
  // No delay here - we want to update the screen as soon as data arrives.
}
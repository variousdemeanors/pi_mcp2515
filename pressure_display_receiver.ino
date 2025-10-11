/*
  ESP-NOW Pressure Display Receiver

  This sketch runs on the 3.2" ESP32-32E Display Board.
  It receives pressure data wirelessly via ESP-NOW from the transmitter board
  and displays it on the ST7789 TFT screen.

  HARDWARE:
  - 3.2inch ESP32-32E Display Board
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
  tft.setTextSize(3);

  tft.setCursor(10, 10);
  tft.println("Waiting for data...");

  // Set device as a Wi-Fi Station
  WiFi.mode(WIFI_STA);

  // Initialize ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    tft.setCursor(10, 40);
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

    // Display the received values on the TFT screen
    tft.setCursor(20, 50);
    tft.print("Tank PSI: ");
    tft.print(sensorReadings.pressure1, 1);
    tft.print("  ");

    tft.setCursor(20, 100);
    tft.print("Line PSI: ");
    tft.print(sensorReadings.pressure2, 1);
    tft.print("  ");

    // Print to Serial monitor for debugging
    Serial.printf("Received Data -> Tank: %.1f PSI, Line: %.1f PSI\n", sensorReadings.pressure1, sensorReadings.pressure2);
  }
  // No delay here - we want to update the screen as soon as data arrives.
}
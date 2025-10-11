/*
  ESP-NOW Pressure Display Receiver (v4 - With Statistics)

  This sketch runs on the 3.2" ESP32-32E Display Board.
  It receives pressure data wirelessly via ESP-NOW, displays it,
  and calculates and displays Min, Max, and Average pressure statistics.
  Includes a touchscreen button to reset the statistics.
*/

#include <esp_now.h>
#include <WiFi.h>
#include <SPI.h>
#include <TFT_eSPI.h>

// =========================================================================
// Configuration
// =========================================================================
TFT_eSPI tft = TFT_eSPI();

// Define the coordinates for the "Reset" button
#define RESET_BUTTON_X 220
#define RESET_BUTTON_Y 10
#define RESET_BUTTON_W 90
#define RESET_BUTTON_H 40
// =========================================================================

// Data structure to hold the incoming sensor readings.
typedef struct struct_message {
  float pressure1;
  float pressure2;
} struct_message;

struct_message sensorReadings;

// Data structure to hold the statistics for one sensor.
typedef struct struct_stats {
  float min = 999.0;
  float max = 0.0;
  float total = 0.0;
  long count = 0;
} struct_stats;

struct_stats stats1; // For Pre-Solenoid
struct_stats stats2; // For Post-Solenoid

volatile bool newData = false;

// Function Prototypes
void updateStats(struct_stats &stats, float newValue);
void drawStats();
void resetStats();

// Callback function for receiving data
void OnDataRecv(const esp_now_recv_info * info, const uint8_t *incomingData, int len) {
  memcpy(&sensorReadings, incomingData, sizeof(sensorReadings));
  updateStats(stats1, sensorReadings.pressure1);
  updateStats(stats2, sensorReadings.pressure2);
  newData = true;
}

void setup() {
  Serial.begin(115200);

  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);

  // Draw the static UI elements
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 10);
  tft.print("WMI Pressure Monitor");

  // Draw the reset button
  tft.drawRect(RESET_BUTTON_X, RESET_BUTTON_Y, RESET_BUTTON_W, RESET_BUTTON_H, TFT_YELLOW);
  tft.setTextColor(TFT_YELLOW);
  tft.setCursor(RESET_BUTTON_X + 15, RESET_BUTTON_Y + 12);
  tft.print("RESET");

  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    tft.setCursor(10, 50);
    tft.print("ESP-NOW Init Failed!");
    return;
  }

  esp_now_register_recv_cb(OnDataRecv);
  Serial.println("Receiver setup complete. Waiting for data...");
}

void loop() {
  // Check for touch events to reset stats
  uint16_t t_x, t_y;
  if (tft.getTouch(&t_x, &t_y)) {
    // Check if the touch coordinates are within the button area
    if (t_x > RESET_BUTTON_X && t_x < (RESET_BUTTON_X + RESET_BUTTON_W) && t_y > RESET_BUTTON_Y && t_y < (RESET_BUTTON_Y + RESET_BUTTON_H)) {
      resetStats();
    }
  }

  // If new data has arrived, update the screen
  if (newData) {
    newData = false;
    drawStats();
  }
}

void updateStats(struct_stats &stats, float newValue) {
  if (newValue < stats.min) stats.min = newValue;
  if (newValue > stats.max) stats.max = newValue;
  stats.total += newValue;
  stats.count++;
}

void resetStats() {
  // Reset stats for sensor 1
  stats1.min = 999.0;
  stats1.max = 0.0;
  stats1.total = 0.0;
  stats1.count = 0;
  // Reset stats for sensor 2
  stats2.min = 999.0;
  stats2.max = 0.0;
  stats2.total = 0.0;
  stats2.count = 0;

  // Clear the screen area and redraw
  tft.fillScreen(TFT_BLACK); // Easiest way to clear everything
  setup(); // Redraw the static UI elements
  Serial.println("Statistics have been reset.");
}

void drawStats() {
  // --- Display Pre-Solenoid Data ---
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 50);
  tft.print("Pre-Solenoid: ");
  tft.setTextSize(3);
  tft.print(sensorReadings.pressure1, 1);
  tft.print(" PSI   "); // Padding

  // --- Display Post-Solenoid Data ---
  tft.setTextSize(2);
  tft.setCursor(10, 100);
  tft.print("Post-Solenoid:");
  tft.setTextSize(3);
  tft.print(sensorReadings.pressure2, 1);
  tft.print(" PSI   "); // Padding

  // --- Display Statistics ---
  tft.setTextSize(2);
  tft.setTextColor(TFT_CYAN, TFT_BLACK);

  // Pre-Solenoid Stats
  tft.setCursor(10, 150);
  tft.printf("Min:%.1f Max:%.1f Avg:%.1f ", stats1.min == 999.0 ? 0.0 : stats1.min, stats1.max, stats1.count > 0 ? stats1.total/stats1.count : 0.0);

  // Post-Solenoid Stats
  tft.setCursor(10, 180);
  tft.printf("Min:%.1f Max:%.1f Avg:%.1f ", stats2.min == 999.0 ? 0.0 : stats2.min, stats2.max, stats2.count > 0 ? stats2.total/stats2.count : 0.0);

  Serial.printf("Pre:%.1f, Post:%.1f | Stats1(Min:%.1f,Max:%.1f,Avg:%.1f) | Stats2(Min:%.1f,Max:%.1f,Avg:%.1f)\n",
    sensorReadings.pressure1, sensorReadings.pressure2,
    stats1.min, stats1.max, stats1.total/stats1.count,
    stats2.min, stats2.max, stats2.total/stats2.count);
}
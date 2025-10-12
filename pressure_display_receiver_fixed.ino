/*
  ESP-NOW Pressure Display Receiver (v5 - FIXED VERSION)

  This sketch runs on the 3.2" ESP32-32E Display Board.
  It receives pressure data wirelessly via ESP-NOW, displays it,
  and calculates and displays Min, Max, and Average pressure statistics.
  Includes a touchscreen button to reset the statistics.

  FIXES:
  - Improved ESP-NOW initialization and error handling
  - Added proper WiFi channel management
  - Enhanced data validation and timeout detection
  - Better display error handling
  - Added connection status indicators
*/

#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <SPI.h>
#include <TFT_eSPI.h>
#include <string.h>
#include <FS.h>
#include <SPIFFS.h>

// =========================================================================
// Configuration
// =========================================================================
TFT_eSPI tft = TFT_eSPI();

// Define UI buttons
#define PAGE_BUTTON_X 120
#define PAGE_BUTTON_Y 10
#define PAGE_BUTTON_W 90
#define PAGE_BUTTON_H 40

#define RESET_BUTTON_X 220
#define RESET_BUTTON_Y 10
#define RESET_BUTTON_W 90
#define RESET_BUTTON_H 40

// WiFi Channel (must match transmitter)
#define WIFI_CHANNEL 1

// Data timeout (if no data received for this time, show warning)
#define DATA_TIMEOUT_MS 2000

// RGB LED Pins (from manufacturer documentation)
#define LED_RED_PIN 22
#define LED_GREEN_PIN 16
#define LED_BLUE_PIN 17

// Other hardware pins for reference
#define BATTERY_ADC_PIN 34
#define AUDIO_ENABLE_PIN 4
#define AUDIO_DAC_PIN 26
// =========================================================================

// Gauge ranges (PSI)
#define GAUGE_MIN_PSI 0.0f
#define GAUGE_MAX_PSI 200.0f

// Smooth font file paths in SPIFFS (optional)
#define FONT_NUM_LARGE "/fonts/Roboto-Bold-36.vlw"
#define FONT_NUM_SMALL "/fonts/Roboto-Regular-20.vlw"
#define FONT_LABEL "/fonts/RobotoCondensed-Regular-18.vlw"

// Track SPIFFS and font state
bool spiffs_ok = false;
enum ActiveFont
{
  FONT_NONE = 0,
  FONT_SMALL,
  FONT_LARGE,
  FONT_LABEL_F
};
ActiveFont activeFont = FONT_NONE;

// Forward declarations for fonts/graphics helpers
void setFontSmall();
void setFontLarge();
void setFontLabel();
void resetToDefaultFont();
uint16_t color565(uint8_t r, uint8_t g, uint8_t b);
uint16_t gaugeGradientColor(float t);
void drawColorBarGauge(int x, int y, int w, int h, float value, float vmin, float vmax, const char *label);

// Data structure to hold the incoming sensor readings.
// MUST match the transmitter structure exactly!
typedef struct struct_message
{
  float pressure1;
  float pressure2;
  uint32_t timestamp; // Timestamp from transmitter
  uint32_t packet_id; // Packet ID for tracking
} struct_message;

struct_message sensorReadings;

// Data structure to hold the statistics for one sensor.
typedef struct struct_stats
{
  float min = 999.0;
  float max = 0.0;
  float total = 0.0;
  long count = 0;
} struct_stats;

struct_stats stats1; // For Pre-Solenoid
struct_stats stats2; // For Post-Solenoid

volatile bool newData = false;
unsigned long lastDataTime = 0;
uint32_t lastPacketId = 0;
uint32_t totalPacketsReceived = 0;
uint32_t missedPackets = 0;

// Connection status
bool esp_now_initialized = false;
bool data_timeout = false;

// Page control: 0 = Live values, 1 = Statistics page
uint8_t currentPage = 0;

// Function Prototypes
void updateStats(struct_stats &stats, float newValue);
void drawUI();
void drawData();
void drawConnectionStatus();
void resetStats();
void printMacAddress();
void drawButtons();
void drawLivePage();
void drawStatsPage();

// Helper for Arduino core version comparison if not defined
#ifndef ESP_ARDUINO_VERSION_VAL
#define ESP_ARDUINO_VERSION_VAL(major, minor, patch) ((major << 16) | (minor << 8) | (patch))
#endif

// Callback function for receiving data (version-guarded)
#if defined(ESP_ARDUINO_VERSION) && (ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0))
// ESP32 core 3.x uses esp_now_recv_info*
void OnDataRecv(const esp_now_recv_info *recv_info, const uint8_t *incomingData, int len)
{
  (void)recv_info; // not used
#else
// ESP32 core 2.x uses mac_addr first
void OnDataRecv(const uint8_t *mac_addr, const uint8_t *incomingData, int len)
{
  (void)mac_addr; // not used
#endif
  // Validate data length
  if (len != sizeof(struct_message))
  {
    Serial.printf("❌ Invalid data length received: %d (expected %d)\n", len, sizeof(struct_message));
    return;
  }

  // Copy data
  memcpy(&sensorReadings, incomingData, sizeof(sensorReadings));

  // Validate data ranges (basic sanity check)
  if (sensorReadings.pressure1 < 0 || sensorReadings.pressure1 > 500 ||
      sensorReadings.pressure2 < 0 || sensorReadings.pressure2 > 500)
  {
    Serial.printf("⚠️  Suspicious pressure values: P1=%.1f, P2=%.1f\n",
                  sensorReadings.pressure1, sensorReadings.pressure2);
  }

  // Track packet statistics
  totalPacketsReceived++;
  if (lastPacketId > 0 && sensorReadings.packet_id > lastPacketId + 1)
  {
    missedPackets += (sensorReadings.packet_id - lastPacketId - 1);
    Serial.printf("📉 Missed %u packets (got #%u, expected #%u)\n",
                  sensorReadings.packet_id - lastPacketId - 1,
                  sensorReadings.packet_id, lastPacketId + 1);
  }
  lastPacketId = sensorReadings.packet_id;

  // Update statistics
  updateStats(stats1, sensorReadings.pressure1);
  updateStats(stats2, sensorReadings.pressure2);

  // Update timing
  lastDataTime = millis();
  data_timeout = false;
  newData = true;

  // Print debug info (every 20th packet to reduce clutter)
  if (totalPacketsReceived % 20 == 0)
  {
    float packet_loss = (float)missedPackets / (totalPacketsReceived + missedPackets) * 100.0;
    Serial.printf("📊 Received %u packets, missed %u (%.1f%% loss)\n",
                  totalPacketsReceived, missedPackets, packet_loss);
  }
}

void printMacAddress()
{
  uint8_t mac[6];
  WiFi.macAddress(mac);
  Serial.printf("🔍 Receiver MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}

void setup()
{
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n📺 ESP-NOW Pressure Display Receiver v5");
  Serial.println("=========================================");

  // Initialize display first
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextWrap(false); // Prevent text wrapping to the next line
  tft.setTextSize(2);
  tft.setCursor(10, 10);
  tft.print("Initializing...");

  // Mount SPIFFS for smooth fonts (and future assets)
  if (SPIFFS.begin(true))
  {
    spiffs_ok = true;
    Serial.println("✅ SPIFFS mounted");
  }
  else
  {
    spiffs_ok = false;
    Serial.println("⚠️  SPIFFS mount failed - using built-in bitmap fonts");
  }

  // Initialize WiFi
  WiFi.mode(WIFI_STA);
  printMacAddress();

  // Set WiFi channel
  esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
  Serial.printf("📡 WiFi Channel: %d\n", WIFI_CHANNEL);

  // Initialize ESP-NOW
  esp_err_t init_result = esp_now_init();
  if (init_result != ESP_OK)
  {
    Serial.printf("❌ Error initializing ESP-NOW: %s\n", esp_err_to_name(init_result));
    tft.fillScreen(TFT_RED);
    tft.setCursor(10, 50);
    tft.setTextColor(TFT_WHITE, TFT_RED);
    tft.print("ESP-NOW Init Failed!");
    tft.setCursor(10, 80);
    tft.printf("Error: %s", esp_err_to_name(init_result));
    while (1)
      delay(1000); // Halt execution
  }

  esp_now_initialized = true;
  Serial.println("✅ ESP-NOW initialized successfully");

  // Register receive callback
  esp_err_t callback_result = esp_now_register_recv_cb(OnDataRecv);
  if (callback_result != ESP_OK)
  {
    Serial.printf("❌ Failed to register receive callback: %s\n", esp_err_to_name(callback_result));
  }
  else
  {
    Serial.println("✅ Receive callback registered");
  }

  // Draw the UI
  drawUI();

  Serial.println("📡 Receiver ready. Waiting for data...\n");
  lastDataTime = millis(); // Initialize timeout timer
}

void loop()
{
  // Check for data timeout
  if (millis() - lastDataTime > DATA_TIMEOUT_MS)
  {
    if (!data_timeout)
    {
      data_timeout = true;
      Serial.println("⚠️  Data timeout - no packets received recently");
    }
  }

  // Check for touch events to reset stats
  uint16_t t_x = 0, t_y = 0;
  bool touched = false;

// Only try to get touch if touch is available (avoid compilation errors)
#ifdef TOUCH_CS
  touched = tft.getTouch(&t_x, &t_y);
#endif

  if (touched)
  {
    Serial.printf("👆 Touch detected at (%d, %d)\n", t_x, t_y);

    // PAGE button
    if (t_x >= PAGE_BUTTON_X && t_x <= (PAGE_BUTTON_X + PAGE_BUTTON_W) &&
        t_y >= PAGE_BUTTON_Y && t_y <= (PAGE_BUTTON_Y + PAGE_BUTTON_H))
    {
      currentPage = (currentPage == 0) ? 1 : 0;
      Serial.printf("📄 Switched to %s page\n", currentPage == 0 ? "LIVE" : "STATS");
      drawUI();
      delay(200);
    }

    // RESET button
    if (t_x >= RESET_BUTTON_X && t_x <= (RESET_BUTTON_X + RESET_BUTTON_W) &&
        t_y >= RESET_BUTTON_Y && t_y <= (RESET_BUTTON_Y + RESET_BUTTON_H))
    {
      Serial.println("🔄 Reset button pressed");
      resetStats();
      drawUI();   // Redraw the UI after clearing
      delay(200); // Debounce touch
    }
  }

  // If new data has arrived, update the screen
  if (newData)
  {
    newData = false;
    drawData();
  }

  // Update connection status every second
  static unsigned long lastStatusUpdate = 0;
  if (millis() - lastStatusUpdate > 1000)
  {
    drawConnectionStatus();
    lastStatusUpdate = millis();
  }

  delay(50); // Small delay to prevent excessive CPU usage
}

void updateStats(struct_stats &stats, float newValue)
{
  if (newValue < stats.min)
    stats.min = newValue;
  if (newValue > stats.max)
    stats.max = newValue;
  stats.total += newValue;
  stats.count++;
}

void resetStats()
{
  stats1.min = 999.0;
  stats1.max = 0.0;
  stats1.total = 0.0;
  stats1.count = 0;

  stats2.min = 999.0;
  stats2.max = 0.0;
  stats2.total = 0.0;
  stats2.count = 0;

  totalPacketsReceived = 0;
  missedPackets = 0;
  lastPacketId = 0;
  Serial.println("🔄 Statistics have been reset.");
}

void drawUI()
{
  tft.fillScreen(TFT_BLACK);
  drawButtons();

  if (currentPage == 0)
  {
    drawLivePage();
  }
  else
  {
    drawStatsPage();
  }
}

void drawConnectionStatus()
{
  // Draw connection status indicator in top-right corner
  int status_x = 280;
  int status_y = 5;
  int status_size = 8;

  if (data_timeout)
  {
    tft.fillCircle(status_x, status_y, status_size, TFT_RED);
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.setTextSize(1);
    tft.setCursor(status_x - 25, status_y + 10);
    tft.print("NO DATA");
  }
  else
  {
    tft.fillCircle(status_x, status_y, status_size, TFT_GREEN);
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.setTextSize(1);
    tft.setCursor(status_x - 25, status_y + 10);
    tft.print("ONLINE ");
  }
}

void drawData()
{
  if (currentPage == 0)
  {
    drawLivePage();
  }
  else
  {
    drawStatsPage();
  }
}

void drawButtons()
{
  // PAGE button
  tft.drawRect(PAGE_BUTTON_X, PAGE_BUTTON_Y, PAGE_BUTTON_W, PAGE_BUTTON_H, TFT_YELLOW);
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(PAGE_BUTTON_X + 14, PAGE_BUTTON_Y + 12);
  tft.print(currentPage == 0 ? "STATS" : "LIVE");

  // RESET button
  tft.drawRect(RESET_BUTTON_X, RESET_BUTTON_Y, RESET_BUTTON_W, RESET_BUTTON_H, TFT_YELLOW);
  tft.setCursor(RESET_BUTTON_X + 15, RESET_BUTTON_Y + 12);
  tft.print("RESET");
}

void drawLivePage()
{
  // Clear content area
  tft.fillRect(0, 50, 320, 170, TFT_BLACK);

  // Draw two horizontal color bar gauges with labels and numerical values
  int gx = 10, gy1 = 70, gy2 = 150, gw = 300, gh = 24;
  drawColorBarGauge(gx, gy1, gw, gh, sensorReadings.pressure1, GAUGE_MIN_PSI, GAUGE_MAX_PSI, "Pre-Solenoid");
  drawColorBarGauge(gx, gy2, gw, gh, sensorReadings.pressure2, GAUGE_MIN_PSI, GAUGE_MAX_PSI, "Post-Solenoid");

  // Packet info
  tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  tft.setTextSize(1);
  tft.setCursor(10, 230);
  tft.printf("Packet #%u | Received: %u | Lost: %u     ",
             sensorReadings.packet_id, totalPacketsReceived, missedPackets);

  // Serial debug (throttled)
  static uint32_t last_debug_packet = 0;
  if (sensorReadings.packet_id != last_debug_packet)
  {
    Serial.printf("📨 [#%u] Pre: %.1f PSI | Post: %.1f PSI\n",
                  sensorReadings.packet_id, sensorReadings.pressure1, sensorReadings.pressure2);
    last_debug_packet = sensorReadings.packet_id;
  }
}

void drawStatsPage()
{
  tft.fillRect(0, 50, 320, 190, TFT_BLACK); // Clear content area

  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 60);
  tft.print("Statistics (Min/Max/Avg)");

  tft.setTextColor(TFT_WHITE, TFT_BLACK);
// Slightly smaller numbers for the stats page
#ifdef SMOOTH_FONT
  if (spiffs_ok && SPIFFS.exists(FONT_NUM_SMALL))
  {
    setFontSmall();
  }
  else
  {
    tft.setTextSize(1);
  }
#else
  tft.setTextSize(1);
#endif

  // Pre-Solenoid
  float avg1 = stats1.count > 0 ? stats1.total / stats1.count : 0.0;
  float min1 = stats1.min == 999.0 ? 0.0 : stats1.min;
  tft.setCursor(10, 100);
  tft.printf("Pre:  %5.1f / %5.1f / %5.1f   ", min1, stats1.max, avg1);

  // Post-Solenoid
  float avg2 = stats2.count > 0 ? stats2.total / stats2.count : 0.0;
  float min2 = stats2.min == 999.0 ? 0.0 : stats2.min;
  tft.setCursor(10, 140);
  tft.printf("Post: %5.1f / %5.1f / %5.1f   ", min2, stats2.max, avg2);

  // Hint
  tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  tft.setTextSize(1);
  tft.setCursor(10, 200);
  tft.print("Tap STATS/LIVE to switch pages. Tap RESET to clear stats.");
  resetToDefaultFont();
}

// ========================= Graphics & Fonts Helpers =========================

void setFontSmall()
{
#ifdef SMOOTH_FONT
  if (spiffs_ok && SPIFFS.exists(FONT_NUM_SMALL))
  {
    tft.loadFont(FONT_NUM_SMALL);
    activeFont = FONT_SMALL;
    return;
  }
#endif
  resetToDefaultFont();
}

void setFontLarge()
{
#ifdef SMOOTH_FONT
  if (spiffs_ok && SPIFFS.exists(FONT_NUM_LARGE))
  {
    tft.loadFont(FONT_NUM_LARGE);
    activeFont = FONT_LARGE;
    return;
  }
#endif
  resetToDefaultFont();
}

void setFontLabel()
{
#ifdef SMOOTH_FONT
  if (spiffs_ok && SPIFFS.exists(FONT_LABEL))
  {
    tft.loadFont(FONT_LABEL);
    activeFont = FONT_LABEL_F;
    return;
  }
#endif
  resetToDefaultFont();
}

void resetToDefaultFont()
{
#ifdef SMOOTH_FONT
  if (activeFont != FONT_NONE)
  {
    tft.unloadFont();
  }
#endif
  tft.setTextFont(1); // Built-in small font
  tft.setTextSize(1);
  activeFont = FONT_NONE;
}

uint16_t color565(uint8_t r, uint8_t g, uint8_t b)
{
  return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

// t in [0,1] from green to yellow to red
uint16_t gaugeGradientColor(float t)
{
  if (t < 0)
    t = 0;
  if (t > 1)
    t = 1;
  uint8_t r, g;
  if (t < 0.5f)
  {
    // Green to Yellow
    float k = t / 0.5f; // 0..1
    r = (uint8_t)(255 * k);
    g = 255;
  }
  else
  {
    // Yellow to Red
    float k = (t - 0.5f) / 0.5f; // 0..1
    r = 255;
    g = (uint8_t)(255 * (1.0f - k));
  }
  return color565(r, g, 0);
}

void drawColorBarGauge(int x, int y, int w, int h, float value, float vmin, float vmax, const char *label)
{
  // Frame
  tft.drawRect(x, y, w, h, TFT_DARKGREY);

  // Normalize
  if (value < vmin)
    value = vmin;
  if (value > vmax)
    value = vmax;
  float t = (value - vmin) / (vmax - vmin + 1e-6f);

  // Filled part width
  int fw = (int)(t * (w - 2));
  // Draw background
  tft.fillRect(x + 1, y + 1, w - 2, h - 2, TFT_BLACK);

  // Draw gradient fill in segments for speed
  int segments = 20;
  for (int i = 0; i < segments; i++)
  {
    float a0 = (float)i / segments;
    float a1 = (float)(i + 1) / segments;
    int sx = x + 1 + (int)(a0 * (w - 2));
    int sw = (int)((a1 - a0) * (w - 2));
    uint16_t col = gaugeGradientColor(a0);
    // Clip to filled width
    if (sx + sw > x + 1 + fw)
      sw = max(0, x + 1 + fw - sx);
    if (sw > 0)
      tft.fillRect(sx, y + 1, sw, h - 2, col);
  }

  // Label above
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  resetToDefaultFont();
  tft.setTextSize(2);
  tft.setCursor(x, y - 18);
  tft.print(label);

  // Numeric value on right with PSI
  char buf[24];
  snprintf(buf, sizeof(buf), "%5.1f PSI", value);
#ifdef SMOOTH_FONT
  if (spiffs_ok && SPIFFS.exists(FONT_NUM_LARGE))
  {
    setFontLarge();
    int16_t bx = x + w - 10; // right align
    int16_t by = y + h + 8;  // below bar
    // Simple text width estimation instead of getTextBounds
    int text_width = strlen(buf) * 12; // rough estimate
    tft.setCursor(bx - text_width, by);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.print(buf);
    resetToDefaultFont();
    return;
  }
#endif
  tft.setTextSize(2);
  tft.setCursor(x, y + h + 6);
  tft.print(buf);
}
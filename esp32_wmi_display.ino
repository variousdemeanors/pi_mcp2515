#include <WiFi.h>
#include <esp_now.h>
#include <TFT_eSPI.h>
#include <XPT2046_Touchscreen.h>
#include <SPI.h>
#include <FS.h>
#include <SPIFFS.h>
#include <Preferences.h>

// Display and Touchscreen pins (ESP32-32E)
#define TFT_CS   15
#define TFT_DC   2
#define TFT_RST  -1  // Connected to ESP32 EN
#define TFT_BL   27

#define TOUCH_CS  33
#define TOUCH_IRQ 36

// RGB LED pins
#define LED_R 22
#define LED_G 16
#define LED_B 17

// ESP-NOW settings
uint8_t coordinatorMac[6] = {0xB0, 0xB2, 0x1C, 0x09, 0xD8, 0x3C}; // Will be configured from web dashboard
Preferences preferences;

// Display objects
TFT_eSPI tft = TFT_eSPI();
XPT2046_Touchscreen ts(TOUCH_CS, TOUCH_IRQ);

// Data structure for ESP-NOW messages
typedef struct {
  float methanolPressurePre;    // PSI
  float methanolPressurePost;   // PSI
  int rpm;                      // RPM
  float boostPressure;          // PSI
  float intakeTemp;             // °F
  float fuelTrimShort;          // %
  float fuelTrimLong;           // %
  float commandedAfr;           // AFR
  float measuredAfr;            // AFR
  float widebandVoltage;        // V
  bool wmiArmed;                // WMI system status
  bool systemHealthy;           // Overall system health
  unsigned long timestamp;      // Data timestamp
} SystemData;

SystemData currentData = {0};
bool dataReceived = false;

// Touchscreen calibration
#define CALIBRATION_FILE "/calibration.txt"
#define REPEAT_CAL true

// Gauge positions and sizes
#define GAUGE_RADIUS 35
#define GAUGE_SPACING 10
#define GAUGE_Y_START 50

// Colors
#define BG_COLOR TFT_BLACK
#define GAUGE_BG TFT_DARKGREY
#define NEEDLE_COLOR TFT_RED
#define TEXT_COLOR TFT_WHITE
#define WARNING_COLOR TFT_ORANGE
#define ERROR_COLOR TFT_RED
#define SUCCESS_COLOR TFT_GREEN

// WMI control
bool wmiArmed = false;
unsigned long lastTouchTime = 0;

// Function prototypes
void updateStatusLED();

// ESP-NOW callback
void OnDataRecv(const esp_now_recv_info *info, const uint8_t *incomingData, int len) {
  if (len == sizeof(SystemData)) {
    memcpy(&currentData, incomingData, sizeof(SystemData));
    dataReceived = true;

    // Update RGB LED based on system status
    updateStatusLED();

    Serial.println("Data received via ESP-NOW");
  } else if (len == 1) {
    // WMI toggle command from coordinator
    uint8_t command = *incomingData;
    wmiArmed = (command == 1);
    Serial.printf("WMI toggle received: %s\n", wmiArmed ? "ARM" : "DISARM");
  }
}

// Initialize ESP-NOW
bool initESPNow() {
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return false;
  }

  esp_now_register_recv_cb(OnDataRecv);

  // Add coordinator as peer
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, coordinatorMac, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add coordinator peer");
    return false;
  }
}

// Load coordinator MAC from preferences
void loadCoordinatorMac() {
  preferences.begin("wmi_display", false);
  if (preferences.isKey("coord_mac")) {
    preferences.getBytes("coord_mac", coordinatorMac, 6);
    Serial.printf("Loaded coordinator MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                  coordinatorMac[0], coordinatorMac[1], coordinatorMac[2],
                  coordinatorMac[3], coordinatorMac[4], coordinatorMac[5]);
  } else {
    Serial.println("No coordinator MAC stored, using broadcast");
  }
  preferences.end();
}

// Save coordinator MAC to preferences
void saveCoordinatorMac(uint8_t* mac) {
  preferences.begin("wmi_display", false);
  preferences.putBytes("coord_mac", mac, 6);
  preferences.end();
  memcpy(coordinatorMac, mac, 6);
  Serial.printf("Saved coordinator MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}
void touchCalibration() {
  Serial.println("Initializing touchscreen...");

  if (!ts.begin()) {
    Serial.println("Touchscreen not found!");
    return;
  }

  ts.setRotation(1); // Adjust rotation as needed
  Serial.println("Touchscreen initialized");

  // Load calibration if available
  if (SPIFFS.exists(CALIBRATION_FILE)) {
    File f = SPIFFS.open(CALIBRATION_FILE, "r");
    if (f) {
      String cal = f.readString();
      f.close();
      // Parse calibration data (simplified)
      Serial.println("Calibration loaded");
    }
  } else {
    Serial.println("No calibration file found");
  }
}

// Initialize display
void initDisplay() {
  Serial.println("Initializing TFT display...");

  // Initialize SPI explicitly
  SPI.begin();

  tft.init();
  Serial.println("TFT init complete");

  tft.setRotation(1); // Landscape
  Serial.println("Rotation set");

  tft.fillScreen(BG_COLOR);
  Serial.println("Screen filled");

  tft.setTextColor(TEXT_COLOR);
  tft.setTextSize(1);

  // Enable backlight
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);
  Serial.println("Backlight enabled");

  // Test display with some text
  tft.setCursor(10, 10);
  tft.print("Display Test");
  Serial.println("Display initialization complete");
}

// Initialize RGB LEDs
void initLEDs() {
  pinMode(LED_R, OUTPUT);
  pinMode(LED_G, OUTPUT);
  pinMode(LED_B, OUTPUT);

  // Start with blue (initializing)
  digitalWrite(LED_R, HIGH);
  digitalWrite(LED_G, HIGH);
  digitalWrite(LED_B, LOW);
}

// Update RGB LED based on system status
void updateStatusLED() {
  if (!currentData.systemHealthy) {
    // Red - system error
    digitalWrite(LED_R, LOW);
    digitalWrite(LED_G, HIGH);
    digitalWrite(LED_B, HIGH);
  } else if (currentData.boostPressure > 25.0) {
    // Yellow/Orange - high boost warning
    digitalWrite(LED_R, LOW);
    digitalWrite(LED_G, LOW);
    digitalWrite(LED_B, HIGH);
  } else if (currentData.wmiArmed) {
    // Green - WMI armed and healthy
    digitalWrite(LED_R, HIGH);
    digitalWrite(LED_G, LOW);
    digitalWrite(LED_B, HIGH);
  } else {
    // Blue - system healthy, WMI disarmed
    digitalWrite(LED_R, HIGH);
    digitalWrite(LED_G, HIGH);
    digitalWrite(LED_B, LOW);
  }
}

// Draw circular gauge
void drawGauge(int x, int y, float value, float minVal, float maxVal, String label, String unit) {
  // Gauge background
  tft.drawCircle(x, y, GAUGE_RADIUS, GAUGE_BG);
  tft.fillCircle(x, y, GAUGE_RADIUS - 2, BG_COLOR);

  // Scale markings
  for (int i = 0; i <= 10; i++) {
    float angle = map(i, 0, 10, -150, 150) * PI / 180.0;
    int x1 = x + (GAUGE_RADIUS - 5) * cos(angle);
    int y1 = y + (GAUGE_RADIUS - 5) * sin(angle);
    int x2 = x + (GAUGE_RADIUS - 10) * cos(angle);
    int y2 = y + (GAUGE_RADIUS - 10) * sin(angle);
    tft.drawLine(x1, y1, x2, y2, GAUGE_BG);
  }

  // Needle
  float angle = map(value, minVal, maxVal, -150, 150) * PI / 180.0;
  int needleX = x + (GAUGE_RADIUS - 15) * cos(angle);
  int needleY = y + (GAUGE_RADIUS - 15) * sin(angle);
  tft.drawLine(x, y, needleX, needleY, NEEDLE_COLOR);
  tft.fillCircle(x, y, 3, NEEDLE_COLOR);

  // Value text
  tft.setCursor(x - 20, y + GAUGE_RADIUS + 5);
  tft.printf("%.1f", value);

  // Unit
  tft.setCursor(x - 10, y + GAUGE_RADIUS + 15);
  tft.print(unit);

  // Label
  tft.setCursor(x - tft.textWidth(label) / 2, y - GAUGE_RADIUS - 15);
  tft.print(label);
}

// Draw WMI status and control
void drawWMIStatus() {
  int x = 200;
  int y = 200;

  // WMI Status box
  tft.drawRect(x - 50, y - 20, 100, 40, currentData.wmiArmed ? SUCCESS_COLOR : TFT_DARKGREY);
  tft.fillRect(x - 49, y - 19, 98, 38, currentData.wmiArmed ? SUCCESS_COLOR : TFT_DARKGREY);

  tft.setCursor(x - 25, y - 5);
  tft.setTextColor(TFT_BLACK);
  tft.print(currentData.wmiArmed ? "WMI ARMED" : "WMI SAFE");
  tft.setTextColor(TEXT_COLOR);

  // Touch area for toggle (invisible button)
  // Will be handled in touch processing
}

// Draw system health indicators
void drawSystemHealth() {
  int x = 10;
  int y = 10;

  // System health
  tft.setCursor(x, y);
  tft.setTextColor(currentData.systemHealthy ? SUCCESS_COLOR : ERROR_COLOR);
  tft.print("SYS: ");
  tft.print(currentData.systemHealthy ? "OK" : "ERROR");

  // Fuel trims
  tft.setCursor(x, y + 15);
  tft.setTextColor(abs(currentData.fuelTrimShort) > 10 ? WARNING_COLOR : TEXT_COLOR);
  tft.printf("STFT: %.1f%%", currentData.fuelTrimShort);

  tft.setCursor(x, y + 30);
  tft.setTextColor(abs(currentData.fuelTrimLong) > 10 ? WARNING_COLOR : TEXT_COLOR);
  tft.printf("LTFT: %.1f%%", currentData.fuelTrimLong);

  // Data age
  unsigned long age = millis() - currentData.timestamp;
  tft.setCursor(x, y + 45);
  tft.setTextColor(age > 2000 ? WARNING_COLOR : TEXT_COLOR);
  tft.printf("Age: %lu ms", age);
}

// Handle touchscreen input
void handleTouch() {
  if (!ts.touched()) return;

  TS_Point p = ts.getPoint();

  // Convert touchscreen coordinates to display coordinates
  // This will need calibration
  int y = map(p.x, 0, 4095, 0, 320);
  int x = map(p.y, 0, 4095, 0, 240);

  // Check if WMI toggle area touched (around 200,200)
  if (x > 150 && x < 250 && y > 180 && y < 220) {
    if (millis() - lastTouchTime > 1000) { // Debounce
      wmiArmed = !wmiArmed;
      // Send WMI toggle command via ESP-NOW
      sendWMIToggle();
      lastTouchTime = millis();
    }
  }
}

// Send WMI toggle command
void sendWMIToggle() {
  uint8_t command = wmiArmed ? 1 : 0; // 1 = arm, 0 = disarm

  esp_now_send(coordinatorMac, &command, sizeof(command));

  Serial.printf("WMI toggle sent: %s\n", wmiArmed ? "ARM" : "DISARM");
}

// Main display update
void updateDisplay() {
  if (!dataReceived) {
    // Show waiting message
    tft.fillScreen(BG_COLOR);
    tft.setCursor(60, 120);
    tft.print("Waiting for data...");
    return;
  }

  tft.fillScreen(BG_COLOR);

  // Draw gauges
  // Methanol pressure pre-solenoid
  drawGauge(50, GAUGE_Y_START, currentData.methanolPressurePre, 0, 100, "Methanol Pre", "PSI");

  // Methanol pressure post-solenoid
  drawGauge(140, GAUGE_Y_START, currentData.methanolPressurePost, 0, 100, "Methanol Post", "PSI");

  // RPM
  drawGauge(230, GAUGE_Y_START, currentData.rpm, 0, 8000, "RPM", "RPM");

  // Boost pressure
  drawGauge(50, GAUGE_Y_START + GAUGE_RADIUS * 2 + GAUGE_SPACING, currentData.boostPressure, -10, 40, "Boost", "PSI");

  // Intake temperature
  drawGauge(140, GAUGE_Y_START + GAUGE_RADIUS * 2 + GAUGE_SPACING, currentData.intakeTemp, 0, 200, "Intake Temp", "F");

  // WMI status and system health
  drawWMIStatus();
  drawSystemHealth();
}

void setup() {
  Serial.begin(115200);

  // Load coordinator MAC from preferences
  loadCoordinatorMac();

  // Initialize SPIFFS for calibration
  if (!SPIFFS.begin(true)) {
    Serial.println("SPIFFS initialization failed!");
  }

  // Initialize display
  initDisplay();

  // Initialize LEDs
  initLEDs();

  // Initialize touchscreen
  touchCalibration();

  // Initialize WiFi for ESP-NOW
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  // Initialize ESP-NOW
  if (!initESPNow()) {
    Serial.println("ESP-NOW initialization failed!");
    tft.setCursor(20, 120);
    tft.print("ESP-NOW init failed!");
    while (1);
  }

  Serial.println("WMI Display initialized");
  tft.setCursor(40, 120);
  tft.print("WMI Display Ready");
  delay(2000);
}

void loop() {
  // Handle touchscreen
  handleTouch();

  // Update display
  updateDisplay();

  // Small delay to prevent overwhelming the display
  delay(100);
}
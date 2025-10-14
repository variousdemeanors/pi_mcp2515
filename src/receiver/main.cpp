#include <Arduino.h>

// Include the LVGL-based receiver sketch
/*
 * Minimal LVGL ST7789 Display Test
 * 
 * This is a basic test to verify LVGL works with ST7789 display.
 * Once this works, we can gradually add more features.
 */

#include <Arduino.h>
#include <lvgl.h>
#include <TFT_eSPI.h>
#include <esp_now.h>
#include <WiFi.h>

// Display and LVGL setup
TFT_eSPI tft = TFT_eSPI(); // TFT instance
static lv_disp_draw_buf_t draw_buf;
// Use explicit width for buffer lines (landscape 320x240)
static lv_color_t buf[320 * 10]; // Buffer for 10 lines
static lv_disp_drv_t disp_drv;

// Pressure data structure (from ESP-NOW)
typedef struct {
  float pressure;
  bool valid;
  unsigned long timestamp;
} PressureData;

PressureData pressure_data = {0.0, false, 0};

// UI elements
lv_obj_t *pressure_label = NULL;
lv_obj_t *status_label = NULL;
lv_obj_t *time_label = NULL;

// Function declarations
void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p);
void OnDataRecv(const uint8_t *mac, const uint8_t *incomingData, int len);
void create_ui();
void update_ui();

void setup() {
  Serial.begin(115200);
  Serial.println("Starting Minimal LVGL ST7789 Test...");

  // Initialize display
  tft.init();
  tft.setRotation(1); // Landscape mode, adjust as needed

  // Turn on backlight
  pinMode(27, OUTPUT); // TFT_BL pin
  digitalWrite(27, HIGH);

  Serial.println("Display initialized");

  // Initialize LVGL
  lv_init();

  // Initialize the display buffer
  lv_disp_draw_buf_init(&draw_buf, buf, NULL, 320 * 10);

  // Initialize the display driver
  lv_disp_drv_init(&disp_drv);
  disp_drv.hor_res = 320;  // ST7789 width in landscape
  disp_drv.ver_res = 240;  // ST7789 height in landscape
  disp_drv.flush_cb = my_disp_flush;
  disp_drv.draw_buf = &draw_buf;
  lv_disp_drv_register(&disp_drv);

  Serial.println("LVGL initialized");

  // Setup ESP-NOW for receiving pressure data
  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }
  esp_now_register_recv_cb(OnDataRecv);

  Serial.println("ESP-NOW initialized");

  // Create simple UI
  create_ui();

  Serial.println("UI created, starting main loop");
}

void loop() {
  lv_timer_handler(); // Handle LVGL tasks
  delay(5);
  
  // Update UI every second
  static unsigned long last_update = 0;
  if (millis() - last_update > 1000) {
    update_ui();
    last_update = millis();
  }
}

// Display flush callback for LVGL
void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p) {
  uint32_t w = (area->x2 - area->x1 + 1);
  uint32_t h = (area->y2 - area->y1 + 1);

  tft.startWrite();
  tft.setAddrWindow(area->x1, area->y1, w, h);
  tft.pushColors((uint16_t*)&color_p->full, w * h, true);
  tft.endWrite();

  lv_disp_flush_ready(disp);
}

// ESP-NOW receive callback
void OnDataRecv(const uint8_t *mac, const uint8_t *incomingData, int len) {
  if (len == sizeof(float)) {
    float received_pressure;
    memcpy(&received_pressure, incomingData, sizeof(float));
    
    pressure_data.pressure = received_pressure;
    pressure_data.valid = true;
    pressure_data.timestamp = millis();
    
    Serial.print("Received pressure: ");
    Serial.println(received_pressure);
  }
}

// Create simple UI
void create_ui() {
  // Create main screen
  lv_obj_t *scr = lv_scr_act();
  lv_obj_set_style_bg_color(scr, lv_color_black(), 0);

  // Title label
  lv_obj_t *title = lv_label_create(scr);
  lv_label_set_text(title, "Pressure Monitor");
  lv_obj_set_style_text_color(title, lv_color_white(), 0);
  lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 10);

  // Pressure value label  
  pressure_label = lv_label_create(scr);
  lv_label_set_text(pressure_label, "--- PSI");
  lv_obj_set_style_text_color(pressure_label, lv_color_white(), 0);
  lv_obj_align(pressure_label, LV_ALIGN_CENTER, 0, -20);

  // Status label
  status_label = lv_label_create(scr);
  lv_label_set_text(status_label, "Waiting for data...");
  lv_obj_set_style_text_color(status_label, lv_color_hex(0x808080), 0);
  lv_obj_align(status_label, LV_ALIGN_CENTER, 0, 20);

  // Time label
  time_label = lv_label_create(scr);
  lv_label_set_text(time_label, "Uptime: 0s");
  lv_obj_set_style_text_color(time_label, lv_color_hex(0x808080), 0);
  lv_obj_align(time_label, LV_ALIGN_BOTTOM_MID, 0, -10);

  Serial.println("Basic UI elements created");
}

// Update UI with current data
void update_ui() {
  // Update pressure display
  if (pressure_data.valid && (millis() - pressure_data.timestamp < 5000)) {
    // Data is recent
    char pressure_text[32];
    snprintf(pressure_text, sizeof(pressure_text), "%.1f PSI", pressure_data.pressure);
    lv_label_set_text(pressure_label, pressure_text);
    
    // Update pressure label color based on value
    if (pressure_data.pressure < 10.0) {
      lv_obj_set_style_text_color(pressure_label, lv_color_hex(0xFF0000), 0); // Red - low
    } else if (pressure_data.pressure > 30.0) {
      lv_obj_set_style_text_color(pressure_label, lv_color_hex(0xFF8000), 0); // Orange - high  
    } else {
      lv_obj_set_style_text_color(pressure_label, lv_color_hex(0x00FF00), 0); // Green - normal
    }
    
    lv_label_set_text(status_label, "Data OK");
    lv_obj_set_style_text_color(status_label, lv_color_hex(0x00FF00), 0);
  } else {
    // No recent data
    lv_label_set_text(pressure_label, "--- PSI");
    lv_obj_set_style_text_color(pressure_label, lv_color_white(), 0);
    lv_label_set_text(status_label, "No signal");
    lv_obj_set_style_text_color(status_label, lv_color_hex(0xFF0000), 0);
  }

  // Update uptime
  char time_text[32];
  unsigned long uptime_seconds = millis() / 1000;
  snprintf(time_text, sizeof(time_text), "Uptime: %lus", uptime_seconds);
  lv_label_set_text(time_label, time_text);
}

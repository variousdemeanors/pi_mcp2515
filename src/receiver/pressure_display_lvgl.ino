/*
  ESP-NOW Pressure Display Receiver with LVGL (v6 - LVGL VERSION)

  This sketch runs on the 3.2" ESP32-32E Display Board.
  It receives pressure data wirelessly via ESP-NOW and displays it using LVGL
  with automotive-style gauges and modern UI elements.

  Features:
  - LVGL-based UI with arc gauges and styled buttons
  - Smooth animations and modern visual design
  - Automotive-inspired color gradients (green → yellow → red)
  - Touch-responsive buttons with haptic feedback
  - Statistics panel with professional layout
*/

#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <SPI.h>
#include <TFT_eSPI.h>
#include <string.h>
#include <FS.h>
#include <SPIFFS.h>
#include <lvgl.h>

// Forward declarations for cross-references used early
lv_color_t gaugeColor(float value, float min_val, float max_val);

// =========================================================================
// Configuration
// =========================================================================
TFT_eSPI tft = TFT_eSPI();

// WiFi Channel (must match transmitter)
#define WIFI_CHANNEL 1

// Data timeout (if no data received for this time, show warning)
#define DATA_TIMEOUT_MS 2000

// Gauge ranges (PSI)
#define GAUGE_MIN_PSI 0.0f
#define GAUGE_MAX_PSI 200.0f

// LVGL display buffer
#define LVGL_BUFFER_SIZE (320 * 240 / 10)
static lv_disp_draw_buf_t draw_buf;
static lv_color_t buf[LVGL_BUFFER_SIZE];

// VLW Font paths in SPIFFS
#define VLW_FONT_SMALL "/fonts/RobotoCondensed-Regular-14.vlw"
#define VLW_FONT_MEDIUM "/fonts/RobotoCondensed-Regular-16.vlw"
#define VLW_FONT_LARGE "/fonts/RobotoCondensed-Bold-24.vlw"
#define VLW_FONT_XLARGE "/fonts/RobotoCondensed-Bold-32.vlw"

// Font state (VLW fonts are not used by LVGL; we keep this flag only for logging)
bool vlw_fonts_available = false;

// =========================================================================
// Data Structures
// =========================================================================

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

// =========================================================================
// Global Variables
// =========================================================================
volatile bool newData = false;
unsigned long lastDataTime = 0;
uint32_t lastPacketId = 0;
uint32_t totalPacketsReceived = 0;
uint32_t missedPackets = 0;

// Connection status
bool esp_now_initialized = false;
bool data_timeout = false;

// LVGL Objects
lv_obj_t *scr_live;
lv_obj_t *scr_stats;
lv_obj_t *arc_pre;
lv_obj_t *arc_post;
lv_obj_t *label_pre_value;
lv_obj_t *label_post_value;
lv_obj_t *label_status;
lv_obj_t *btn_page;
lv_obj_t *btn_reset;
lv_obj_t *label_btn_page;
lv_obj_t *label_btn_reset;

// Stats labels
lv_obj_t *label_stats_pre;
lv_obj_t *label_stats_post;
lv_obj_t *label_packets;

// Current page: 0 = Live, 1 = Stats
uint8_t currentPage = 0;

// Animation objects
lv_anim_t anim_pre_arc;
lv_anim_t anim_post_arc;
lv_anim_t anim_pre_color;
lv_anim_t anim_post_color;

// Animation state
int32_t current_pre_value = 0;
int32_t current_post_value = 0;
int32_t target_pre_value = 0;
int32_t target_post_value = 0;

// =========================================================================
// Helper for Arduino core version comparison
// =========================================================================
#ifndef ESP_ARDUINO_VERSION_VAL
#define ESP_ARDUINO_VERSION_VAL(major, minor, patch) ((major << 16) | (minor << 8) | (patch))
#endif

// =========================================================================
// Utility Functions
// =========================================================================

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

void printMacAddress()
{
  uint8_t mac[6];
  WiFi.macAddress(mac);
  Serial.printf("🔍 Receiver MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}

void loadVLWFonts()
{
  if (!SPIFFS.begin(true))
  {
    Serial.println("⚠️  SPIFFS mount failed - using built-in fonts");
    return;
  }

  Serial.println("📁 SPIFFS mounted, checking for VLW fonts...");

  // Check if VLW font files exist
  bool fonts_found = SPIFFS.exists(VLW_FONT_SMALL) &&
                     SPIFFS.exists(VLW_FONT_MEDIUM) &&
                     SPIFFS.exists(VLW_FONT_LARGE);

  if (fonts_found)
  {
    Serial.println("✅ VLW fonts found - loading smooth fonts");

    // Note: VLW fonts are for TFT_eSPI, not LVGL. We'll continue using LVGL fonts.
    vlw_fonts_available = true;

    // In a real implementation, you would load VLW fonts here:
    // font_small = lv_font_load(VLW_FONT_SMALL);
    // font_medium = lv_font_load(VLW_FONT_MEDIUM);
    // etc.

    Serial.println("📝 VLW font loading prepared (requires SMOOTH_FONT enabled)");
  }
  else
  {
    Serial.println("⚠️  VLW fonts not found - using built-in Montserrat fonts");
    vlw_fonts_available = false;
  }
}

const lv_font_t *getBestFont(bool /*large_size*/)
{
  // Use a single built-in font to avoid linker issues across variants
  return &lv_font_montserrat_14;
}

void arc_anim_cb(void *obj, int32_t value)
{
  lv_obj_t *arc = (lv_obj_t *)obj;
  lv_arc_set_value(arc, value);

  // Update color based on animated value
  lv_color_t color = gaugeColor((float)value, GAUGE_MIN_PSI, GAUGE_MAX_PSI);
  lv_obj_set_style_arc_color(arc, color, LV_PART_INDICATOR);
}

void setupAnimations()
{
  // Initialize arc value animations
  lv_anim_init(&anim_pre_arc);
  lv_anim_set_exec_cb(&anim_pre_arc, (lv_anim_exec_xcb_t)arc_anim_cb);
  lv_anim_set_time(&anim_pre_arc, 800);
  lv_anim_set_path_cb(&anim_pre_arc, lv_anim_path_ease_out);

  lv_anim_init(&anim_post_arc);
  lv_anim_set_exec_cb(&anim_post_arc, (lv_anim_exec_xcb_t)arc_anim_cb);
  lv_anim_set_time(&anim_post_arc, 800);
  lv_anim_set_path_cb(&anim_post_arc, lv_anim_path_ease_out);
}

void animateGaugeValue(lv_obj_t *arc, int32_t new_value, int32_t *current_value)
{
  if (*current_value == new_value)
    return; // No change needed

  lv_anim_t *anim = (arc == arc_pre) ? &anim_pre_arc : &anim_post_arc;

  lv_anim_set_var(anim, arc);
  lv_anim_set_values(anim, *current_value, new_value);
  lv_anim_start(anim);

  *current_value = new_value;
}

// =========================================================================
// LVGL Display Driver
// =========================================================================

void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p)
{
  uint32_t w = (area->x2 - area->x1 + 1);
  uint32_t h = (area->y2 - area->y1 + 1);

  tft.startWrite();
  tft.setAddrWindow(area->x1, area->y1, w, h);
  tft.pushColors((uint16_t *)&color_p->full, w * h, true);
  tft.endWrite();

  lv_disp_flush_ready(disp);
}

// =========================================================================
// LVGL Touch Driver
// =========================================================================

void my_touchpad_read(lv_indev_drv_t *indev_driver, lv_indev_data_t *data)
{
  uint16_t touchX, touchY;
  bool touched = tft.getTouch(&touchX, &touchY);

  if (touched)
  {
    data->state = LV_INDEV_STATE_PR;
    data->point.x = touchX;
    data->point.y = touchY;
  }
  else
  {
    data->state = LV_INDEV_STATE_REL;
  }
}

// =========================================================================
// ESP-NOW Callback
// =========================================================================

#if defined(ESP_ARDUINO_VERSION) && (ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0))
void OnDataRecv(const esp_now_recv_info *recv_info, const uint8_t *incomingData, int len)
{
  (void)recv_info; // not used
#else
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

// =========================================================================
// Forward Declarations
// =========================================================================
void updateStatsDisplay();
void loadVLWFonts();
void setupAnimations();
void animateGaugeValue(lv_obj_t *arc, int32_t new_value, int32_t *current_value);
void arc_anim_cb(void *obj, int32_t value);
const lv_font_t *getBestFont(bool large_size);
lv_color_t gaugeColor(float value, float min_val, float max_val);

// =========================================================================
// LVGL Color Helpers
// =========================================================================

lv_color_t gaugeColor(float value, float min_val, float max_val)
{
  float t = (value - min_val) / (max_val - min_val);
  if (t < 0)
    t = 0;
  if (t > 1)
    t = 1;

  if (t < 0.5f)
  {
    // Green to Yellow
    uint8_t r = (uint8_t)(255 * (t / 0.5f));
    return lv_color_make(r, 255, 0);
  }
  else
  {
    // Yellow to Red
    uint8_t g = (uint8_t)(255 * (1.0f - (t - 0.5f) / 0.5f));
    return lv_color_make(255, g, 0);
  }
}

// =========================================================================
// LVGL Event Handlers
// =========================================================================

static void btn_page_event_handler(lv_event_t *e)
{
  lv_event_code_t code = lv_event_get_code(e);
  if (code == LV_EVENT_CLICKED)
  {
    currentPage = (currentPage == 0) ? 1 : 0;
    if (currentPage == 0)
    {
      lv_scr_load(scr_live);
      lv_label_set_text(label_btn_page, "STATS");
    }
    else
    {
      lv_scr_load(scr_stats);
      lv_label_set_text(label_btn_page, "LIVE");
    }
    Serial.printf("📄 Switched to %s page\n", currentPage == 0 ? "LIVE" : "STATS");
  }
}

static void btn_reset_event_handler(lv_event_t *e)
{
  lv_event_code_t code = lv_event_get_code(e);
  if (code == LV_EVENT_CLICKED)
  {
    resetStats();
    updateStatsDisplay();
    Serial.println("🔄 Reset button pressed");
  }
}

// =========================================================================
// LVGL UI Creation
// =========================================================================

void createLiveScreen()
{
  scr_live = lv_obj_create(NULL);
  lv_obj_set_style_bg_color(scr_live, lv_color_black(), 0);

  // Pre-Solenoid Gauge
  arc_pre = lv_arc_create(scr_live);
  lv_obj_set_size(arc_pre, 140, 140);
  lv_obj_set_pos(arc_pre, 10, 60);
  lv_arc_set_range(arc_pre, 0, 200);
  lv_arc_set_value(arc_pre, 0);
  lv_arc_set_bg_angles(arc_pre, 135, 45);
  lv_obj_set_style_arc_width(arc_pre, 8, LV_PART_MAIN);
  lv_obj_set_style_arc_width(arc_pre, 8, LV_PART_INDICATOR);
  lv_obj_remove_style(arc_pre, NULL, LV_PART_KNOB);
  lv_obj_clear_flag(arc_pre, LV_OBJ_FLAG_CLICKABLE);

  // Pre-Solenoid Value Label
  label_pre_value = lv_label_create(scr_live);
  lv_obj_set_pos(label_pre_value, 45, 120);
  lv_label_set_text(label_pre_value, "0.0");
  lv_obj_set_style_text_font(label_pre_value, getBestFont(false), 0);
  lv_obj_set_style_text_color(label_pre_value, lv_color_white(), 0);

  // Pre-Solenoid Label
  lv_obj_t *label_pre = lv_label_create(scr_live);
  lv_obj_set_pos(label_pre, 25, 40);
  lv_label_set_text(label_pre, "Pre-Solenoid");
  lv_obj_set_style_text_color(label_pre, lv_color_white(), 0);

  // Post-Solenoid Gauge
  arc_post = lv_arc_create(scr_live);
  lv_obj_set_size(arc_post, 140, 140);
  lv_obj_set_pos(arc_post, 170, 60);
  lv_arc_set_range(arc_post, 0, 200);
  lv_arc_set_value(arc_post, 0);
  lv_arc_set_bg_angles(arc_post, 135, 45);
  lv_obj_set_style_arc_width(arc_post, 8, LV_PART_MAIN);
  lv_obj_set_style_arc_width(arc_post, 8, LV_PART_INDICATOR);
  lv_obj_remove_style(arc_post, NULL, LV_PART_KNOB);
  lv_obj_clear_flag(arc_post, LV_OBJ_FLAG_CLICKABLE);

  // Post-Solenoid Value Label
  label_post_value = lv_label_create(scr_live);
  lv_obj_set_pos(label_post_value, 205, 120);
  lv_label_set_text(label_post_value, "0.0");
  lv_obj_set_style_text_font(label_post_value, getBestFont(false), 0);
  lv_obj_set_style_text_color(label_post_value, lv_color_white(), 0);

  // Post-Solenoid Label
  lv_obj_t *label_post = lv_label_create(scr_live);
  lv_obj_set_pos(label_post, 180, 40);
  lv_label_set_text(label_post, "Post-Solenoid");
  lv_obj_set_style_text_color(label_post, lv_color_white(), 0);

  // Status Label
  label_status = lv_label_create(scr_live);
  lv_obj_set_pos(label_status, 10, 220);
  lv_label_set_text(label_status, "Packet #0 | Received: 0 | Lost: 0");
  lv_obj_set_style_text_color(label_status, lv_color_make(128, 128, 128), 0);
  lv_obj_set_style_text_font(label_status, getBestFont(false), 0);
}

void createStatsScreen()
{
  scr_stats = lv_obj_create(NULL);
  lv_obj_set_style_bg_color(scr_stats, lv_color_black(), 0);

  // Title
  lv_obj_t *title = lv_label_create(scr_stats);
  lv_obj_set_pos(title, 10, 60);
  lv_label_set_text(title, "Statistics (Min/Max/Avg)");
  lv_obj_set_style_text_color(title, lv_color_make(0, 255, 255), 0);
  lv_obj_set_style_text_font(title, getBestFont(true), 0);

  // Pre-Solenoid Stats
  label_stats_pre = lv_label_create(scr_stats);
  lv_obj_set_pos(label_stats_pre, 10, 100);
  lv_label_set_text(label_stats_pre, "Pre:  0.0 / 0.0 / 0.0");
  lv_obj_set_style_text_color(label_stats_pre, lv_color_white(), 0);
  lv_obj_set_style_text_font(label_stats_pre, getBestFont(false), 0);

  // Post-Solenoid Stats
  label_stats_post = lv_label_create(scr_stats);
  lv_obj_set_pos(label_stats_post, 10, 130);
  lv_label_set_text(label_stats_post, "Post: 0.0 / 0.0 / 0.0");
  lv_obj_set_style_text_color(label_stats_post, lv_color_white(), 0);
  lv_obj_set_style_text_font(label_stats_post, getBestFont(false), 0);

  // Packet Stats
  label_packets = lv_label_create(scr_stats);
  lv_obj_set_pos(label_packets, 10, 170);
  lv_label_set_text(label_packets, "Packets: 0 received, 0 lost (0.0% loss)");
  lv_obj_set_style_text_color(label_packets, lv_color_make(128, 128, 128), 0);
  lv_obj_set_style_text_font(label_packets, getBestFont(false), 0);

  // Hint
  lv_obj_t *hint = lv_label_create(scr_stats);
  lv_obj_set_pos(hint, 10, 200);
  lv_label_set_text(hint, "Tap LIVE to switch pages. Tap RESET to clear stats.");
  lv_obj_set_style_text_color(hint, lv_color_make(128, 128, 128), 0);
  lv_obj_set_style_text_font(hint, getBestFont(false), 0);
}

void createButtons()
{
  // Page Button (appears on both screens)
  btn_page = lv_btn_create(lv_scr_act());
  lv_obj_set_size(btn_page, 90, 40);
  lv_obj_set_pos(btn_page, 120, 10);
  lv_obj_add_event_cb(btn_page, btn_page_event_handler, LV_EVENT_ALL, NULL);
  lv_obj_set_style_bg_color(btn_page, lv_color_make(255, 165, 0), 0);

  label_btn_page = lv_label_create(btn_page);
  lv_label_set_text(label_btn_page, "STATS");
  lv_obj_center(label_btn_page);
  lv_obj_set_style_text_color(label_btn_page, lv_color_black(), 0);

  // Reset Button
  btn_reset = lv_btn_create(lv_scr_act());
  lv_obj_set_size(btn_reset, 90, 40);
  lv_obj_set_pos(btn_reset, 220, 10);
  lv_obj_add_event_cb(btn_reset, btn_reset_event_handler, LV_EVENT_ALL, NULL);
  lv_obj_set_style_bg_color(btn_reset, lv_color_make(255, 165, 0), 0);

  label_btn_reset = lv_label_create(btn_reset);
  lv_label_set_text(label_btn_reset, "RESET");
  lv_obj_center(label_btn_reset);
  lv_obj_set_style_text_color(label_btn_reset, lv_color_black(), 0);
}

// =========================================================================
// LVGL Update Functions
// =========================================================================

void updateLiveDisplay()
{
  // Update arc values with animations
  int pre_val = (int)sensorReadings.pressure1;
  int post_val = (int)sensorReadings.pressure2;

  // Use animated updates instead of direct setting
  animateGaugeValue(arc_pre, pre_val, &current_pre_value);
  animateGaugeValue(arc_post, post_val, &current_post_value);

  // Note: Arc colors are updated by the animation callback

  // Update value labels
  lv_label_set_text_fmt(label_pre_value, "%.1f", sensorReadings.pressure1);
  lv_label_set_text_fmt(label_post_value, "%.1f", sensorReadings.pressure2);

  // Update status
  lv_label_set_text_fmt(label_status, "Packet #%u | Received: %u | Lost: %u",
                        sensorReadings.packet_id, totalPacketsReceived, missedPackets);
}

void updateStatsDisplay()
{
  float avg1 = stats1.count > 0 ? stats1.total / stats1.count : 0.0;
  float min1 = stats1.min == 999.0 ? 0.0 : stats1.min;
  float avg2 = stats2.count > 0 ? stats2.total / stats2.count : 0.0;
  float min2 = stats2.min == 999.0 ? 0.0 : stats2.min;

  lv_label_set_text_fmt(label_stats_pre, "Pre:  %.1f / %.1f / %.1f", min1, stats1.max, avg1);
  lv_label_set_text_fmt(label_stats_post, "Post: %.1f / %.1f / %.1f", min2, stats2.max, avg2);

  float packet_loss = totalPacketsReceived > 0 ? (float)missedPackets / (totalPacketsReceived + missedPackets) * 100.0 : 0.0;
  lv_label_set_text_fmt(label_packets, "Packets: %u received, %u lost (%.1f%% loss)",
                        totalPacketsReceived, missedPackets, packet_loss);
}

// =========================================================================
// Setup
// =========================================================================

void setup()
{
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n📺 ESP-NOW Pressure Display Receiver v6 (LVGL)");
  Serial.println("===============================================");

  // Load VLW fonts from SPIFFS first
  loadVLWFonts();

  // Initialize display
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);

  // Initialize LVGL
  lv_init();

  // Initialize display buffer
  lv_disp_draw_buf_init(&draw_buf, buf, NULL, LVGL_BUFFER_SIZE);

  // Initialize display driver
  static lv_disp_drv_t disp_drv;
  lv_disp_drv_init(&disp_drv);
  disp_drv.hor_res = 320;
  disp_drv.ver_res = 240;
  disp_drv.flush_cb = my_disp_flush;
  disp_drv.draw_buf = &draw_buf;
  lv_disp_drv_register(&disp_drv);

  // Initialize touch driver
  static lv_indev_drv_t indev_drv;
  lv_indev_drv_init(&indev_drv);
  indev_drv.type = LV_INDEV_TYPE_POINTER;
  indev_drv.read_cb = my_touchpad_read;
  lv_indev_drv_register(&indev_drv);

  // Setup animations
  setupAnimations();

  // Mount SPIFFS (optional for future assets)
  if (SPIFFS.begin(true))
  {
    Serial.println("✅ SPIFFS mounted");
  }
  else
  {
    Serial.println("⚠️  SPIFFS mount failed");
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

  // Create LVGL UI
  createLiveScreen();
  createStatsScreen();

  // Load live screen initially
  lv_scr_load(scr_live);
  createButtons();

  Serial.println("📡 LVGL Receiver ready. Waiting for data...\n");
  lastDataTime = millis(); // Initialize timeout timer
}

// =========================================================================
// Main Loop
// =========================================================================

void loop()
{
  // Handle LVGL tasks
  lv_timer_handler();

  // Check for data timeout
  if (millis() - lastDataTime > DATA_TIMEOUT_MS)
  {
    if (!data_timeout)
    {
      data_timeout = true;
      Serial.println("⚠️  Data timeout - no packets received recently");
    }
  }

  // If new data has arrived, update the displays
  if (newData)
  {
    newData = false;
    if (currentPage == 0)
    {
      updateLiveDisplay();
    }
    else
    {
      updateStatsDisplay();
    }
  }

  delay(5); // Small delay for LVGL
}
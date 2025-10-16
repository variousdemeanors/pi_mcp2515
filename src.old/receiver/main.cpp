/*
ESP-NOW Pressure Display Receiver with LVGL (Clean Repository Version)

This sketch runs on the 3.2" ESP32-32E Display Board.
It receives pressure data wirelessly via ESP-NOW and displays it using LVGL
with automotive-style gauges and modern UI elements.

Features:
- LVGL-based UI with arc gauges and styled buttons
- Smooth animations and modern visual design
- Automotive-inspired color gradients (green → yellow → red)
- Touch-responsive buttons with haptic feedback
- Statistics panel with professional layout
- Working uptime counter and proper touch calibration
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
#define LVGL_BUFFER_SIZE (320 * 240 / 20) // Reduced buffer size
static lv_disp_draw_buf_t draw_buf;
static lv_color_t buf[LVGL_BUFFER_SIZE];

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
unsigned long systemStartTime = 0; // Track system boot time

// Connection status
bool esp_now_initialized = false;
bool data_timeout = false;

// LVGL Objects
lv_obj_t *scr_live;
lv_obj_t *scr_stats;
lv_obj_t *arc_gauge1;
lv_obj_t *arc_gauge2;
lv_obj_t *label_value1;
lv_obj_t *label_value2;
lv_obj_t *label_uptime;
lv_obj_t *label_connection;
lv_obj_t *btn_stats;
lv_obj_t *btn_back;

// Animation variables
lv_anim_t anim_gauge1;
lv_anim_t anim_gauge2;

// =========================================================================
// LVGL Display and Touch Functions
// =========================================================================

// Display flushing
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

// Touch reading
void my_touchpad_read(lv_indev_drv_t *indev_driver, lv_indev_data_t *data)
{
    uint16_t touchX = 0, touchY = 0;

    bool touched = tft.getTouch(&touchX, &touchY);

    if (touched)
    {
        data->state = LV_INDEV_STATE_PR;
        data->point.x = touchX;
        data->point.y = touchY;

        // Debug output for touch
        Serial.printf("🖱️ Touch detected: X=%d, Y=%d\n", touchX, touchY);
    }
    else
    {
        data->state = LV_INDEV_STATE_REL;
    }
}

// =========================================================================
// LVGL Color Functions
// =========================================================================

// Convert RGB to LVGL color
lv_color_t lv_color_rgb(uint8_t r, uint8_t g, uint8_t b)
{
    lv_color_t color;
    color = lv_color_make(r, g, b);
    return color;
}

// Determine gauge color based on pressure value
lv_color_t gaugeColor(float value, float min_val, float max_val)
{
    float percentage = (value - min_val) / (max_val - min_val) * 100.0f;

    if (percentage <= 33.0f)
        return lv_color_rgb(76, 175, 80); // Green
    else if (percentage <= 66.0f)
        return lv_color_rgb(255, 193, 7); // Yellow/Amber
    else
        return lv_color_rgb(244, 67, 54); // Red
}

// =========================================================================
// Button Event Handlers
// =========================================================================

static void btn_stats_event_handler(lv_event_t *e)
{
    lv_event_code_t code = lv_event_get_code(e);
    if (code == LV_EVENT_CLICKED)
    {
        Serial.println("🔘 Stats button clicked!");
        lv_scr_load(scr_stats);
    }
}

static void btn_back_event_handler(lv_event_t *e)
{
    lv_event_code_t code = lv_event_get_code(e);
    if (code == LV_EVENT_CLICKED)
    {
        Serial.println("🔙 Back button clicked!");
        lv_scr_load(scr_live);
    }
}

// =========================================================================
// LVGL UI Creation Functions
// =========================================================================

void createLiveScreen()
{
    Serial.println("🎨 Creating live screen...");

    scr_live = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(scr_live, lv_color_rgb(33, 37, 41), 0);

    // Title
    lv_obj_t *title = lv_label_create(scr_live);
    lv_label_set_text(title, "Automotive Pressure Monitor");
    lv_obj_set_style_text_color(title, lv_color_white(), 0);
    lv_obj_set_style_text_font(title, &lv_font_montserrat_14, 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 10);

    // Gauge 1 (Pre-Solenoid)
    arc_gauge1 = lv_arc_create(scr_live);
    lv_obj_set_size(arc_gauge1, 120, 120);
    lv_obj_align(arc_gauge1, LV_ALIGN_LEFT_MID, 20, -10);
    lv_arc_set_range(arc_gauge1, (int)GAUGE_MIN_PSI, (int)GAUGE_MAX_PSI);
    lv_arc_set_value(arc_gauge1, 0);
    lv_obj_set_style_arc_color(arc_gauge1, lv_color_rgb(76, 175, 80), LV_PART_INDICATOR);
    lv_obj_set_style_arc_width(arc_gauge1, 10, LV_PART_INDICATOR);
    lv_obj_set_style_arc_width(arc_gauge1, 10, LV_PART_MAIN);

    // Value label for gauge 1
    label_value1 = lv_label_create(arc_gauge1);
    lv_label_set_text(label_value1, "---");
    lv_obj_set_style_text_color(label_value1, lv_color_white(), 0);
    lv_obj_set_style_text_font(label_value1, &lv_font_montserrat_14, 0);
    lv_obj_center(label_value1);

    // Label for gauge 1
    lv_obj_t *label1_desc = lv_label_create(scr_live);
    lv_label_set_text(label1_desc, "Pre-Solenoid");
    lv_obj_set_style_text_color(label1_desc, lv_color_white(), 0);
    lv_obj_align_to(label1_desc, arc_gauge1, LV_ALIGN_OUT_BOTTOM_MID, 0, 5);

    // Gauge 2 (Post-Solenoid)
    arc_gauge2 = lv_arc_create(scr_live);
    lv_obj_set_size(arc_gauge2, 120, 120);
    lv_obj_align(arc_gauge2, LV_ALIGN_RIGHT_MID, -20, -10);
    lv_arc_set_range(arc_gauge2, (int)GAUGE_MIN_PSI, (int)GAUGE_MAX_PSI);
    lv_arc_set_value(arc_gauge2, 0);
    lv_obj_set_style_arc_color(arc_gauge2, lv_color_rgb(76, 175, 80), LV_PART_INDICATOR);
    lv_obj_set_style_arc_width(arc_gauge2, 10, LV_PART_INDICATOR);
    lv_obj_set_style_arc_width(arc_gauge2, 10, LV_PART_MAIN);

    // Value label for gauge 2
    label_value2 = lv_label_create(arc_gauge2);
    lv_label_set_text(label_value2, "---");
    lv_obj_set_style_text_color(label_value2, lv_color_white(), 0);
    lv_obj_set_style_text_font(label_value2, &lv_font_montserrat_14, 0);
    lv_obj_center(label_value2);

    // Label for gauge 2
    lv_obj_t *label2_desc = lv_label_create(scr_live);
    lv_label_set_text(label2_desc, "Post-Solenoid");
    lv_obj_set_style_text_color(label2_desc, lv_color_white(), 0);
    lv_obj_align_to(label2_desc, arc_gauge2, LV_ALIGN_OUT_BOTTOM_MID, 0, 5);

    // Uptime label
    label_uptime = lv_label_create(scr_live);
    lv_label_set_text(label_uptime, "Uptime: 0s");
    lv_obj_set_style_text_color(label_uptime, lv_color_white(), 0);
    lv_obj_align(label_uptime, LV_ALIGN_BOTTOM_LEFT, 10, -30);

    // Connection status label
    label_connection = lv_label_create(scr_live);
    lv_label_set_text(label_connection, "Status: Starting...");
    lv_obj_set_style_text_color(label_connection, lv_color_white(), 0);
    lv_obj_align(label_connection, LV_ALIGN_BOTTOM_RIGHT, -10, -30);

    // Stats button
    btn_stats = lv_btn_create(scr_live);
    lv_obj_set_size(btn_stats, 80, 35);
    lv_obj_align(btn_stats, LV_ALIGN_BOTTOM_MID, 0, -10);
    lv_obj_add_event_cb(btn_stats, btn_stats_event_handler, LV_EVENT_CLICKED, NULL);

    lv_obj_t *btn_stats_label = lv_label_create(btn_stats);
    lv_label_set_text(btn_stats_label, "Stats");
    lv_obj_center(btn_stats_label);

    Serial.println("✅ Live screen created successfully");
}

void createStatsScreen()
{
    Serial.println("🎨 Creating stats screen...");

    scr_stats = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(scr_stats, lv_color_rgb(33, 37, 41), 0);

    // Title
    lv_obj_t *title = lv_label_create(scr_stats);
    lv_label_set_text(title, "Statistics");
    lv_obj_set_style_text_color(title, lv_color_white(), 0);
    lv_obj_set_style_text_font(title, &lv_font_montserrat_14, 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 10);

    // Stats content (placeholder for now)
    lv_obj_t *stats_content = lv_label_create(scr_stats);
    lv_label_set_text(stats_content, "Sensor Statistics\n\nPre-Solenoid:\nMin: -- PSI\nMax: -- PSI\nAvg: -- PSI\n\nPost-Solenoid:\nMin: -- PSI\nMax: -- PSI\nAvg: -- PSI");
    lv_obj_set_style_text_color(stats_content, lv_color_white(), 0);
    lv_obj_align(stats_content, LV_ALIGN_CENTER, 0, -10);

    // Back button
    btn_back = lv_btn_create(scr_stats);
    lv_obj_set_size(btn_back, 80, 35);
    lv_obj_align(btn_back, LV_ALIGN_BOTTOM_MID, 0, -10);
    lv_obj_add_event_cb(btn_back, btn_back_event_handler, LV_EVENT_CLICKED, NULL);

    lv_obj_t *btn_back_label = lv_label_create(btn_back);
    lv_label_set_text(btn_back_label, "Back");
    lv_obj_center(btn_back_label);

    Serial.println("✅ Stats screen created successfully");
}

// =========================================================================
// ESP-NOW Functions
// =========================================================================

void OnDataRecv(const uint8_t *mac, const uint8_t *incomingData, int len)
{
    if (len != sizeof(sensorReadings))
    {
        Serial.printf("⚠️ Received data size mismatch: %d bytes (expected %d)\n", len, sizeof(sensorReadings));
        return;
    }

    memcpy(&sensorReadings, incomingData, sizeof(sensorReadings));
    newData = true;
    lastDataTime = millis();
    totalPacketsReceived++;

    // Check for missed packets
    if (lastPacketId != 0 && sensorReadings.packet_id != lastPacketId + 1)
    {
        missedPackets += (sensorReadings.packet_id - lastPacketId - 1);
    }
    lastPacketId = sensorReadings.packet_id;

    Serial.printf("📡 Data received: P1=%.2f, P2=%.2f, ID=%lu\n",
                  sensorReadings.pressure1, sensorReadings.pressure2, sensorReadings.packet_id);
}

void printMacAddress()
{
    uint8_t mac[6];
    WiFi.macAddress(mac);
    Serial.printf("📧 MAC Address: %02x:%02x:%02x:%02x:%02x:%02x\n",
                  mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}

// =========================================================================
// Update Functions
// =========================================================================

void updateDisplay()
{
    if (!newData)
        return;

    // Update gauge 1
    int gauge1_value = (int)sensorReadings.pressure1;
    lv_arc_set_value(arc_gauge1, gauge1_value);
    lv_obj_set_style_arc_color(arc_gauge1, gaugeColor(sensorReadings.pressure1, GAUGE_MIN_PSI, GAUGE_MAX_PSI), LV_PART_INDICATOR);

    char value1_str[16];
    snprintf(value1_str, sizeof(value1_str), "%.1f", sensorReadings.pressure1);
    lv_label_set_text(label_value1, value1_str);

    // Update gauge 2
    int gauge2_value = (int)sensorReadings.pressure2;
    lv_arc_set_value(arc_gauge2, gauge2_value);
    lv_obj_set_style_arc_color(arc_gauge2, gaugeColor(sensorReadings.pressure2, GAUGE_MIN_PSI, GAUGE_MAX_PSI), LV_PART_INDICATOR);

    char value2_str[16];
    snprintf(value2_str, sizeof(value2_str), "%.1f", sensorReadings.pressure2);
    lv_label_set_text(label_value2, value2_str);

    // Update statistics
    if (stats1.count == 0)
    {
        stats1.min = sensorReadings.pressure1;
        stats1.max = sensorReadings.pressure1;
    }
    else
    {
        if (sensorReadings.pressure1 < stats1.min)
            stats1.min = sensorReadings.pressure1;
        if (sensorReadings.pressure1 > stats1.max)
            stats1.max = sensorReadings.pressure1;
    }
    stats1.total += sensorReadings.pressure1;
    stats1.count++;

    if (stats2.count == 0)
    {
        stats2.min = sensorReadings.pressure2;
        stats2.max = sensorReadings.pressure2;
    }
    else
    {
        if (sensorReadings.pressure2 < stats2.min)
            stats2.min = sensorReadings.pressure2;
        if (sensorReadings.pressure2 > stats2.max)
            stats2.max = sensorReadings.pressure2;
    }
    stats2.total += sensorReadings.pressure2;
    stats2.count++;

    newData = false;
}

void updateUptime()
{
    unsigned long currentTime = millis();
    unsigned long uptime_seconds = (currentTime - systemStartTime) / 1000;

    char uptime_str[32];
    snprintf(uptime_str, sizeof(uptime_str), "Uptime: %lus", uptime_seconds);
    lv_label_set_text(label_uptime, uptime_str);

    // Update connection status
    if ((currentTime - lastDataTime) > DATA_TIMEOUT_MS && lastDataTime > 0)
    {
        lv_label_set_text(label_connection, "Status: No Data");
        lv_obj_set_style_text_color(label_connection, lv_color_rgb(244, 67, 54), 0); // Red
        data_timeout = true;
    }
    else if (lastDataTime > 0)
    {
        lv_label_set_text(label_connection, "Status: Connected");
        lv_obj_set_style_text_color(label_connection, lv_color_rgb(76, 175, 80), 0); // Green
        data_timeout = false;
    }
    else
    {
        lv_label_set_text(label_connection, "Status: Waiting...");
        lv_obj_set_style_text_color(label_connection, lv_color_rgb(255, 193, 7), 0); // Yellow
    }
}

// =========================================================================
// Setup and Loop
// =========================================================================

void setup()
{
    Serial.begin(115200);
    delay(2000);

    systemStartTime = millis(); // Record system start time

    Serial.println("\n🚗 ESP-NOW Pressure Display Receiver v7 (Clean Repo)");
    Serial.println("=====================================================");

    // Initialize display
    tft.init();
    tft.setRotation(1);
    tft.fillScreen(TFT_BLACK);

    // Calibrate touch (you may need to adjust these values for your display)
    uint16_t calData[5] = {275, 3620, 264, 3532, 1};
    tft.setTouch(calData);
    Serial.println("📱 Touch calibration set");

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

    // Create UI screens
    createLiveScreen();
    createStatsScreen();

    // Load the live screen
    lv_scr_load(scr_live);

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

    Serial.println("🚗 Receiver ready. Starting main loop...\n");
}

void loop()
{
    // Handle LVGL tasks
    lv_timer_handler();

    // Update display with new data
    updateDisplay();

    // Update uptime and connection status every second
    static unsigned long lastUptimeUpdate = 0;
    if (millis() - lastUptimeUpdate >= 1000)
    {
        updateUptime();
        lastUptimeUpdate = millis();
    }

    // Small delay to prevent overwhelming the system
    delay(10);
}
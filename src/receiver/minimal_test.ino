/*
MINIMAL TEST FIRMWARE - EXTREMELY OBVIOUS
This is a super simple test to verify firmware uploads work
*/

#include <SPI.h>
#include <TFT_eSPI.h>

TFT_eSPI tft = TFT_eSPI();

bool isRed = true;
unsigned long lastBlink = 0;
unsigned long bootTime = 0;

void setup()
{
    Serial.begin(115200);
    delay(2000);

    bootTime = millis();

    Serial.println("\n🚨🚨🚨 MINIMAL TEST FIRMWARE v3.0 🚨🚨🚨");
    Serial.println("==============================================");
    Serial.println("🔴 This is DEFINITELY the NEW test firmware!");
    Serial.println("💥 Screen should be BLINKING RED/BLUE");
    Serial.println("📡 This message proves NEW firmware running!");
    Serial.println("==============================================");

    // Initialize display
    tft.init();
    tft.setRotation(1); // Landscape

    // Initial red screen
    tft.fillScreen(TFT_RED);
    tft.setTextColor(TFT_WHITE, TFT_RED);
    tft.setTextSize(3);
    tft.drawString("NEW TEST", 70, 70);
    tft.drawString("FIRMWARE", 50, 110);
    tft.drawString("BLINKING!", 40, 150);

    Serial.println("✅ Minimal test setup completed - should see blinking!");
}

void loop()
{
    unsigned long currentTime = millis();

    // Blink every 500ms
    if (currentTime - lastBlink >= 500)
    {
        if (isRed)
        {
            // Switch to BLUE
            tft.fillScreen(TFT_BLUE);
            tft.setTextColor(TFT_WHITE, TFT_BLUE);
            tft.setTextSize(3);
            tft.drawString("BLUE MODE", 60, 70);
            tft.drawString("WORKING!", 70, 110);

            unsigned long uptime = (currentTime - bootTime) / 1000;
            tft.setTextSize(2);
            String uptimeStr = "UP: " + String(uptime) + "s";
            tft.drawString(uptimeStr, 10, 200);

            Serial.println("🔵 BLUE mode - Uptime: " + String(uptime) + " seconds");
        }
        else
        {
            // Switch to RED
            tft.fillScreen(TFT_RED);
            tft.setTextColor(TFT_WHITE, TFT_RED);
            tft.setTextSize(3);
            tft.drawString("RED MODE", 70, 70);
            tft.drawString("WORKING!", 70, 110);

            unsigned long uptime = (currentTime - bootTime) / 1000;
            tft.setTextSize(2);
            String uptimeStr = "UP: " + String(uptime) + "s";
            tft.drawString(uptimeStr, 10, 200);

            Serial.println("🔴 RED mode - Uptime: " + String(uptime) + " seconds");
        }

        isRed = !isRed;
        lastBlink = currentTime;
    }

    // Print periodic status to serial
    static unsigned long lastStatus = 0;
    if (currentTime - lastStatus >= 2000)
    {
        unsigned long uptime = (currentTime - bootTime) / 1000;
        Serial.println("💥 MINIMAL TEST FIRMWARE ACTIVE - Uptime: " + String(uptime) + "s");
        lastStatus = currentTime;
    }

    delay(10);
}
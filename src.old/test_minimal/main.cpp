/*
MINIMAL TEST FIRMWARE - EXTREMELY OBVIOUS
This is a super simple test to verify firmware uploads work
*/

#include <Arduino.h>
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

    Serial.println("\n🚨🚨🚨 MINIMAL TEST FIRMWARE v4.0 🚨🚨🚨");
    Serial.println("==============================================");
    Serial.println("🔴 This is DEFINITELY the NEW test firmware!");
    Serial.println("💥 Screen should be BLINKING RED/BLUE");
    Serial.println("📡 This message proves NEW firmware running!");
    Serial.println("🆕 FRESH REPOSITORY - CLEAN ENVIRONMENT!");
    Serial.println("==============================================");

    // Initialize display
    tft.init();
    tft.setRotation(1); // Landscape

    // Initial red screen
    tft.fillScreen(TFT_RED);
    tft.setTextColor(TFT_WHITE, TFT_RED);
    tft.setTextSize(3);
    tft.drawString("NEW REPO", 70, 50);
    tft.drawString("CLEAN ENV", 50, 90);
    tft.drawString("BLINKING!", 40, 130);
    tft.setTextSize(2);
    tft.drawString("Fresh Start!", 80, 170);

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
            tft.drawString("BLUE MODE", 60, 50);
            tft.drawString("WORKING!", 70, 90);
            tft.setTextSize(2);
            tft.drawString("Clean Repo!", 80, 130);

            unsigned long uptime = (currentTime - bootTime) / 1000;
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
            tft.drawString("RED MODE", 70, 50);
            tft.drawString("WORKING!", 70, 90);
            tft.setTextSize(2);
            tft.drawString("Fresh Start!", 80, 130);

            unsigned long uptime = (currentTime - bootTime) / 1000;
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
        Serial.println("💥 FRESH REPO TEST FIRMWARE ACTIVE - Uptime: " + String(uptime) + "s");
        lastStatus = currentTime;
    }

    delay(10);
}
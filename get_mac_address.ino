// Simple sketch to get ESP32 MAC address
// Upload this to your ESP32 to find its MAC address for ESP-NOW setup

#include <WiFi.h>

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("ESP32 MAC Address Finder");
  Serial.println("========================");

  // Get MAC address
  uint8_t mac[6];
  WiFi.macAddress(mac);

  Serial.print("MAC Address: ");
  for (int i = 0; i < 6; i++) {
    if (mac[i] < 16) Serial.print("0");
    Serial.print(mac[i], HEX);
    if (i < 5) Serial.print(":");
  }
  Serial.println();

  // Also print as array for easy copying
  Serial.print("uint8_t mac[] = {");
  for (int i = 0; i < 6; i++) {
    Serial.print("0x");
    if (mac[i] < 16) Serial.print("0");
    Serial.print(mac[i], HEX);
    if (i < 5) Serial.print(", ");
  }
  Serial.println("};");

  Serial.println();
  Serial.println("Copy the uint8_t array above and paste it into esp32_can_obd.ino");
  Serial.println("Replace the 0xXX values in coordinatorMac[]");
}

void loop() {
  // Nothing to do here
}
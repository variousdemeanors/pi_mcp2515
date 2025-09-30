# ESP32 Coordinator (Receives ESP-NOW, responds to Pi serial)
# Flash this to the ESP32 connected to Pi GPIO

#include <WiFi.h>
#include <esp_now.h>

// ESP-NOW setup
typedef struct {
  float rpm;
  float engineLoad;
  float intakeTemp;
  float manifoldPressure;
  float vehicleSpeed;
  float throttlePos;
  float coolantTemp;
  // float mafRate;  // Not used - car has MAP sensor
} OBDData;

OBDData latestData;

// Serial communication with Pi
#define SERIAL_BAUD 115200

void setup() {
  Serial.begin(SERIAL_BAUD);
  Serial.println("ESP32 Coordinator starting...");

  // Initialize ESP-NOW
  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }

  esp_now_register_recv_cb([](const esp_now_recv_info *esp_now_info, const uint8_t *data, int len) {
    if (len == sizeof(OBDData)) {
      memcpy(&latestData, data, sizeof(OBDData));
    }
  });

  Serial.println("Setup complete");
}

void loop() {
  // Check for serial commands from Pi
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "PING") {
      Serial.println("PONG");
    } else if (command == "GET_DATA") {
      // Send latest data as JSON
      Serial.print("{");
      Serial.print("\"rpm\":"); Serial.print(latestData.rpm); Serial.print(",");
      Serial.print("\"engineLoad\":"); Serial.print(latestData.engineLoad); Serial.print(",");
      Serial.print("\"intakeTemp\":"); Serial.print(latestData.intakeTemp); Serial.print(",");
      Serial.print("\"manifoldPressure\":"); Serial.print(latestData.manifoldPressure); Serial.print(",");
      Serial.print("\"vehicleSpeed\":"); Serial.print(latestData.vehicleSpeed); Serial.print(",");
      Serial.print("\"throttlePos\":"); Serial.print(latestData.throttlePos); Serial.print(",");
      Serial.print("\"coolantTemp\":"); Serial.print(latestData.coolantTemp);
      // Serial.print(",\"mafRate\":"); Serial.print(latestData.mafRate);  // Not used - car has MAP sensor
      Serial.println("}");
    }
  }

  delay(10);
}
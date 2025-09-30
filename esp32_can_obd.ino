# ESP32 CAN Bus OBD Reader (Sends data via ESP-NOW)
# Flash this to the ESP32 connected to MCP2515 and CAN bus

#include <WiFi.h>
#include <esp_now.h>
#include <mcp2515.h>

// CAN Bus setup
#define CAN_CS 5  // SPI CS pin for MCP2515
MCP2515 mcp2515(CAN_CS);

// ESP-NOW setup
uint8_t coordinatorMac[] = {0xXX, 0xXX, 0xXX, 0xXX, 0xXX, 0xXX}; // Replace with coordinator ESP32 MAC address

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

OBDData obdData;

// OBD PID definitions
#define PID_RPM 0x0C
#define PID_ENGINE_LOAD 0x04
#define PID_INTAKE_TEMP 0x0F
#define PID_INTAKE_PRESSURE 0x0B
#define PID_SPEED 0x0D
#define PID_THROTTLE_POS 0x11
#define PID_COOLANT_TEMP 0x05
//#define PID_MAF 0x10  // Not used - car has MAP sensor

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 CAN OBD Reader starting...");

  // Initialize SPI for MCP2515
  SPI.begin();
  mcp2515.reset();
  mcp2515.setBitrate(CAN_500KBPS, MCP_8MHZ); // 500 kbps CAN bus speed
  mcp2515.setNormalMode();

  // Initialize ESP-NOW
  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }

  esp_now_register_send_cb([](const uint8_t *mac_addr, esp_now_send_status_t status) {
    Serial.print("Send status: ");
    Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Success" : "Fail");
  });

  esp_now_peer_info_t peerInfo;
  memcpy(peerInfo.peer_addr, coordinatorMac, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add peer");
    return;
  }

  Serial.println("Setup complete");
}

void loop() {
  // Query OBD PIDs
  obdData.rpm = queryPID(PID_RPM);
  obdData.engineLoad = queryPID(PID_ENGINE_LOAD);
  obdData.intakeTemp = queryPID(PID_INTAKE_TEMP);
  obdData.manifoldPressure = queryPID(PID_INTAKE_PRESSURE);
  obdData.vehicleSpeed = queryPID(PID_SPEED);
  obdData.throttlePos = queryPID(PID_THROTTLE_POS);
  obdData.coolantTemp = queryPID(PID_COOLANT_TEMP);
  // obdData.mafRate = queryPID(PID_MAF);  // Not used - car has MAP sensor

  // Send data via ESP-NOW
  esp_now_send(coordinatorMac, (uint8_t *)&obdData, sizeof(OBDData));

  delay(50); // 20Hz
}

float queryPID(uint8_t pid) {
  // Send OBD request
  struct can_frame txFrame;
  txFrame.can_id = 0x7DF; // OBD request ID
  txFrame.can_dlc = 8;
  txFrame.data[0] = 0x02; // Number of additional bytes
  txFrame.data[1] = 0x01; // Service 01 (current data)
  txFrame.data[2] = pid;
  txFrame.data[3] = 0x00;
  txFrame.data[4] = 0x00;
  txFrame.data[5] = 0x00;
  txFrame.data[6] = 0x00;
  txFrame.data[7] = 0x00;

  mcp2515.sendMessage(&txFrame);

  // Wait for response
  unsigned long startTime = millis();
  while (millis() - startTime < 100) { // 100ms timeout
    if (mcp2515.readMessage(&txFrame) == MCP2515::ERROR_OK) {
      if (txFrame.can_id == 0x7E8 && txFrame.data[1] == 0x41 && txFrame.data[2] == pid) {
        // Parse response based on PID
        return parsePIDResponse(pid, txFrame.data);
      }
    }
  }

  return 0.0; // Timeout or no response
}

float parsePIDResponse(uint8_t pid, uint8_t* data) {
  switch (pid) {
    case PID_RPM:
      return ((data[3] * 256) + data[4]) / 4.0;
    case PID_ENGINE_LOAD:
      return data[3] / 2.55;
    case PID_INTAKE_TEMP:
      return data[3] - 40;
    case PID_INTAKE_PRESSURE:
      return data[3];
    case PID_SPEED:
      return data[3];
    case PID_THROTTLE_POS:
      return data[3] / 2.55;
    case PID_COOLANT_TEMP:
      return data[3] - 40;
    // case PID_MAF:
    //   return ((data[3] * 256) + data[4]) / 100.0;  // Not used - car has MAP sensor
    default:
      return 0.0;
  }
}
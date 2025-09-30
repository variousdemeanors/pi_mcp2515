# ESP32 CAN Bus OBD Reader with WMI Relay Control (Sends data via ESP-NOW)
# Flash this to the ESP32 connected to MCP2515 and CAN bus

#include <WiFi.h>
#include <esp_now.h>
#include <mcp_can.h>
#include <SPI.h>

// OBD-II PID definitions
#define PID_RPM 0x0C
#define PID_ENGINE_LOAD 0x04
#define PID_INTAKE_TEMP 0x0F
#define PID_INTAKE_PRESSURE 0x0B
#define PID_THROTTLE_POS 0x11
#define PID_COOLANT_TEMP 0x05
#define PID_STFT 0x06
#define PID_LTFT 0x07
#define PID_LAMBDA 0x44
#define PID_WIDEBAND_VOLTAGE 0x24

// CAN Bus setup
#define CAN_CS 5  // SPI CS pin for MCP2515
MCP_CAN mcp2515(CAN_CS);
bool canInitialized = false;

// WMI Relay control
#define WMI_RELAY_PIN 12  // GPIO pin connected to relay module
bool wmiArmed = false;

// ESP-NOW setup
uint8_t coordinatorMac[] = {0xB0, 0xB2, 0x1C, 0x09, 0xD8, 0x3C};



typedef struct {
  float rpm;
  float engineLoad;
  float intakeTemp;
  float manifoldPressure;
  float throttlePos;
  float coolantTemp;
  float stft;
  float ltft;
  float commandedAfr;
  float measuredAfr;
  float widebandVoltage;
  // float mafRate;  // Not used - car has MAP sensor
} OBDData;

OBDData obdData;

// ESP-NOW receive callback for WMI commands
void OnDataRecv(const esp_now_recv_info *info, const uint8_t *incomingData, int len) {
  if (len == 1) {
    // WMI toggle command
    uint8_t command = *incomingData;
    wmiArmed = (command == 1);
    
    // Control relay
    digitalWrite(WMI_RELAY_PIN, wmiArmed ? HIGH : LOW);
    
    Serial.printf("WMI relay %s\n", wmiArmed ? "ARMED (12V ON)" : "DISARMED (12V OFF)");
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 CAN OBD Reader with WMI Control starting...");

  // Initialize WMI relay pin
  pinMode(WMI_RELAY_PIN, OUTPUT);
  digitalWrite(WMI_RELAY_PIN, LOW); // Start disarmed
  Serial.println("WMI relay initialized (disarmed)");

  // Initialize SPI for MCP2515
  SPI.begin();
  Serial.println("Initializing MCP2515...");
  if (mcp2515.begin(MCP_ANY, CAN_500KBPS, MCP_8MHZ) != CAN_OK) {
    Serial.println("MCP2515 initialization failed!");
    Serial.println("Possible causes:");
    Serial.println("- Wrong crystal frequency (try MCP_16MHZ if board has 16MHz crystal)");
    Serial.println("- CAN bus not connected or not terminated");
    Serial.println("- Wrong CAN_CS pin (currently GPIO 5)");
    Serial.println("- SPI pins not connected properly");
    Serial.println("- Power supply issues");
    canInitialized = false;
    return;
  }
  mcp2515.setMode(MCP_NORMAL);
  canInitialized = true;
  Serial.println("MCP2515 initialized successfully");

  // Initialize ESP-NOW
  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }

  // Register receive callback for WMI commands
  esp_now_register_recv_cb(OnDataRecv);

  // Send callback removed due to ESP32 Arduino version compatibility issues
  // esp_now_register_send_cb([](const uint8_t *mac_addr, esp_now_send_status_t status) {
  //   Serial.print("Send status: ");
  //   Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Success" : "Fail");
  // });

  esp_now_peer_info_t peerInfo;
  memcpy(peerInfo.peer_addr, coordinatorMac, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add coordinator peer");
    return;
  }

  Serial.println("Setup complete - WMI system ready");
}

void loop() {
  if (!canInitialized) {
    Serial.println("CAN not initialized - skipping PID queries");
    delay(1000);
    return;
  }

  // Query OBD PIDs
  obdData.rpm = queryPID(PID_RPM);
  obdData.engineLoad = queryPID(PID_ENGINE_LOAD);
  obdData.intakeTemp = queryPID(PID_INTAKE_TEMP);
  obdData.manifoldPressure = queryPID(PID_INTAKE_PRESSURE);
  obdData.throttlePos = queryPID(PID_THROTTLE_POS);
  obdData.coolantTemp = queryPID(PID_COOLANT_TEMP);
  obdData.stft = queryPID(PID_STFT);
  obdData.ltft = queryPID(PID_LTFT);
  obdData.commandedAfr = 14.7; // Stoichiometric AFR for gasoline (target/commanded)
  obdData.measuredAfr = queryPID(PID_LAMBDA);
  obdData.widebandVoltage = queryPID(PID_WIDEBAND_VOLTAGE);
  // obdData.mafRate = queryPID(PID_MAF);  // Not used - car has MAP sensor

  // Send data via ESP-NOW
  esp_now_send(coordinatorMac, (uint8_t *)&obdData, sizeof(OBDData));

  delay(50); // 20Hz
}

float queryPID(uint8_t pid) {
  // Send OBD request
  uint8_t data[8] = {0x02, 0x01, pid, 0x00, 0x00, 0x00, 0x00, 0x00};
  
  if (mcp2515.sendMsgBuf(0x7DF, 0, 8, data) != CAN_OK) {
    Serial.println("CAN send failed");
    return 0.0;
  }

  // Wait for response
  unsigned long startTime = millis();
  while (millis() - startTime < 100) { // 100ms timeout
    if (mcp2515.checkReceive() == CAN_MSGAVAIL) {
      uint8_t len = 0;
      uint8_t buf[8];
      uint32_t canId;
      
      mcp2515.readMsgBuf(&canId, &len, buf);
      
      if (canId == 0x7E8 && len >= 3 && buf[1] == 0x41 && buf[2] == pid) {
        // Parse response based on PID
        return parsePIDResponse(pid, buf);
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
    case PID_THROTTLE_POS:
      return data[3] / 2.55;
    case PID_COOLANT_TEMP:
      return data[3] - 40;
    case PID_STFT:
      return (data[3] - 128) * 100.0 / 128.0;
    case PID_LTFT:
      return (data[3] - 128) * 100.0 / 128.0;
    case PID_LAMBDA:
      return (((data[3] * 256) + data[4]) / 32768.0) * 14.7; // Lambda to AFR conversion
    case PID_WIDEBAND_VOLTAGE:
      return ((data[3] * 256) + data[4]) / 20000.0;
    // case PID_MAF:
    //   return ((data[3] * 256) + data[4]) / 100.0;  // Not used - car has MAP sensor
    default:
      return 0.0;
  }
}
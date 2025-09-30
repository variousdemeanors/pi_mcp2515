# ESP32 Coordinator (Receives ESP-NOW from CAN unit, responds to Pi serial, forwards to WMI display)
# Flash this to the ESP32 connected to Pi GPIO

#include <WiFi.h>
#include <esp_now.h>

// ESP-NOW setup for CAN data
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

OBDData latestData;

// WMI Display data structure
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
} WMIData;

// MAC addresses (configure these)
uint8_t canEsp32Mac[] = {0x08, 0xA6, 0xF7, 0xBB, 0x64, 0x60}; // CAN ESP32 MAC - Acebott board MAC
uint8_t wmiDisplayMac[] = {0x1C, 0x69, 0x20, 0x95, 0x9F, 0x50}; // WMI Display MAC

// WMI state
bool wmiArmed = false;
bool systemHealthy = true;

// Serial communication with Pi
#define SERIAL_BAUD 115200

// ESP-NOW receive callback
void OnDataRecv(const esp_now_recv_info *esp_now_info, const uint8_t *data, int len) {
  if (len == sizeof(OBDData)) {
    memcpy(&latestData, data, sizeof(OBDData));

    // Forward to WMI display
    sendToWMIDisplay();
  } else if (len == sizeof(uint8_t)) {
    // WMI toggle command from display - forward to CAN ESP32
    uint8_t command = *data;
    wmiArmed = (command == 1);
    
    // Forward command to CAN ESP32 for relay control
    esp_now_send(canEsp32Mac, &command, sizeof(command));
    
    Serial.printf("WMI command forwarded to CAN ESP32: %s\n", wmiArmed ? "ARMED" : "SAFE");
  }
}

// Send data to WMI display
void sendToWMIDisplay() {
  WMIData wmiData = {
    45.0,  // methanolPressurePre (placeholder - would come from sensors)
    42.0,  // methanolPressurePost (placeholder)
    (int)latestData.rpm,
    latestData.manifoldPressure - 14.7,  // Convert to boost pressure (absolute to gauge)
    latestData.intakeTemp,
    latestData.stft,   // fuelTrimShort
    latestData.ltft,   // fuelTrimLong
    latestData.commandedAfr,
    latestData.measuredAfr,
    latestData.widebandVoltage,
    wmiArmed,
    systemHealthy,
    millis()
  };

  esp_now_send(wmiDisplayMac, (uint8_t*)&wmiData, sizeof(WMIData));
}

// Add ESP-NOW peers
void addPeers() {
  // Add CAN ESP32 as peer
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, canEsp32Mac, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);

  // Add WMI display as peer
  memcpy(peerInfo.peer_addr, wmiDisplayMac, 6);
  esp_now_add_peer(&peerInfo);
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  Serial.println("ESP32 Coordinator starting...");

  // Initialize ESP-NOW
  WiFi.mode(WIFI_STA);
  
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }

  esp_now_register_recv_cb(OnDataRecv);

  // Add peers
  addPeers();

  Serial.println("Setup complete - ready for CAN data and WMI commands");
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
      Serial.print("\"throttlePos\":"); Serial.print(latestData.throttlePos); Serial.print(",");
      Serial.print("\"coolantTemp\":"); Serial.print(latestData.coolantTemp); Serial.print(",");
      Serial.print("\"stft\":"); Serial.print(latestData.stft); Serial.print(",");
      Serial.print("\"ltft\":"); Serial.print(latestData.ltft); Serial.print(",");
      Serial.print("\"commandedAfr\":"); Serial.print(latestData.commandedAfr); Serial.print(",");
      Serial.print("\"measuredAfr\":"); Serial.print(latestData.measuredAfr); Serial.print(",");
      Serial.print("\"widebandVoltage\":"); Serial.print(latestData.widebandVoltage);
      // Serial.print(",\"mafRate\":"); Serial.print(latestData.mafRate);  // Not used - car has MAP sensor
      Serial.println("}");
    }
  }

  delay(10);
}
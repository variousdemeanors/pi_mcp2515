/*
  ESP32C6 CAN Bus to MQTT Publisher (v2 - Corrected)

  This sketch reads all raw CAN bus frames from an MCP2515 module
  and publishes them to an MQTT server. It uses mDNS to automatically
  discover the MQTT server (e.g., 'raspberrypi.local').

  Designed for a Seeed Studio XIAO ESP32C6.

  Wiring between XIAO ESP32C6 and MCP2515 Module:
  - 3V3    -> VCC
  - GND    -> GND
  - D7     -> SCK  (SPI Clock)
  - D6     -> MOSI (SPI Data Out)
  - D5     -> MISO (SPI Data In)
  - D4     -> CS   (Chip Select)
*/

// Libraries for WiFi, MQTT, and CAN bus
#include <WiFi.h>
#include <PubSubClient.h> // MQTT Client
#include <mcp_can.h>
#include <SPI.h>
#include <ESPmDNS.h>      // For resolving local hostnames (e.g., raspberrypi.local)

// =================================================================
// TODO: USER CONFIGURATION
// =================================================================
// WiFi Credentials
const char* ssid = "YOUR_WIFI_SSID";       // <-- REPLACE with your Wi-Fi network name (KEEP THE QUOTES)
const char* password = "YOUR_WIFI_PASSWORD"; // <-- REPLACE with your Wi-Fi password (KEEP THE QUOTES)

// MQTT Server Configuration
const char* mqtt_server_hostname = "raspberrypi.local"; // Hostname for the Pi
const int mqtt_port = 1883;
const char* mqtt_topic = "can/raw"; // Topic to publish raw CAN data to

// CAN Bus Configuration
#define CAN_CS_PIN 4 // CS pin for MCP2515 is connected to D4 on the XIAO ESP32C6
MCP_CAN mcp2515(CAN_CS_PIN);

// MQTT Client Setup
WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect_mqtt() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    if (client.connect("ESP32C6-CAN-Client")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial); // Wait for serial port to connect

  Serial.println("ESP32C6 CAN to MQTT Publisher");

  // Initialize WiFi
  setup_wifi();

  // Setup MQTT client
  Serial.println("Resolving MQTT server hostname...");
  if (!MDNS.begin("esp32c6")) {
    Serial.println("Error setting up MDNS responder!");
    while(1) {
      delay(1000);
    }
  }

  IPAddress mqtt_server_ip;
  int retries = 0;
  while (retries < 5) {
    mqtt_server_ip = MDNS.queryHost(mqtt_server_hostname);
    if (mqtt_server_ip) {
      break;
    }
    // -- CORRECTED CODE --
    Serial.print("Could not resolve hostname: ");
    Serial.print(mqtt_server_hostname);
    Serial.println(". Retrying...");
    retries++;
    delay(1000);
  }

  if (!mqtt_server_ip) {
    // -- CORRECTED CODE --
    Serial.print("ERROR: Could not resolve hostname '");
    Serial.print(mqtt_server_hostname);
    Serial.println("' after several retries.");
    Serial.println("Please check the Pi is on the same network and accessible.");
    while(1); // Halt
  }

  Serial.print("MQTT Server IP found: ");
  Serial.println(mqtt_server_ip);
  client.setServer(mqtt_server_ip, mqtt_port);

  // Initialize SPI and MCP2515
  SPI.begin();
  Serial.println("Initializing MCP2515...");
  if (mcp2515.begin(MCP_ANY, CAN_500KBPS, MCP_8MHZ) != CAN_OK) {
    Serial.println("ERROR: MCP2515 initialization failed!");
    Serial.println("Check your wiring and crystal frequency (try MCP_16MHZ if needed).");
    while (1); // Halt execution
  }
  mcp2515.setMode(MCP_NORMAL);
  Serial.println("MCP2515 Initialized Successfully.");
}

void loop() {
  // Ensure MQTT client is connected
  if (!client.connected()) {
    reconnect_mqtt();
  }
  client.loop();

  // Check for incoming CAN messages
  if (mcp2515.checkReceive() == CAN_MSGAVAIL) {
    long unsigned int canId;
    unsigned char len = 0;
    unsigned char buf[8];

    // Read message
    mcp2515.readMsgBuf(&canId, &len, buf);

    // Format the message for MQTT publication
    // Format: "ID:LEN:B0,B1,B2,B3,B4,B5,B6,B7"
    char msg[50]; // Buffer for the MQTT message string
    sprintf(msg, "%lX:%d:", canId, len);

    char byte_str[4];
    for (int i = 0; i < len; i++) {
      sprintf(byte_str, "%02X", buf[i]);
      strcat(msg, byte_str);
      if (i < len - 1) {
        strcat(msg, ",");
      }
    }

    // Publish the message
    Serial.print("Publishing message: ");
    Serial.println(msg);
    client.publish(mqtt_topic, msg);
  }
}
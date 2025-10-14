/*
ESP-NOW Pressure Sensor Transmitter

This sketch runs on an ESP32 with pressure sensors connected.
It reads pressure data and transmits it wirelessly via ESP-NOW to the receiver.
*/

#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>

// WiFi Channel (must match receiver)
#define WIFI_CHANNEL 1

// Data structure - MUST match receiver structure exactly!
typedef struct struct_message
{
    float pressure1;
    float pressure2;
    uint32_t timestamp;
    uint32_t packet_id;
} struct_message;

struct_message sensorData;

// Replace with receiver's MAC address
uint8_t receiverMAC[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF}; // Broadcast address for testing

uint32_t packetCounter = 0;

void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status)
{
    Serial.printf("📡 Packet %lu sent: %s\n", packetCounter, (status == ESP_NOW_SEND_SUCCESS) ? "Success" : "Failed");
}

void setup()
{
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n📡 ESP-NOW Pressure Transmitter v2");
    Serial.println("===================================");

    // Initialize WiFi
    WiFi.mode(WIFI_STA);

    // Print MAC address
    uint8_t mac[6];
    WiFi.macAddress(mac);
    Serial.printf("📧 MAC Address: %02x:%02x:%02x:%02x:%02x:%02x\n",
                  mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    // Set WiFi channel
    esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
    Serial.printf("📡 WiFi Channel: %d\n", WIFI_CHANNEL);

    // Initialize ESP-NOW
    if (esp_now_init() != ESP_OK)
    {
        Serial.println("❌ Error initializing ESP-NOW");
        while (1)
            delay(1000);
    }

    Serial.println("✅ ESP-NOW initialized successfully");

    // Register send callback
    esp_now_register_send_cb(OnDataSent);

    // Add peer (receiver)
    esp_now_peer_info_t peerInfo;
    memset(&peerInfo, 0, sizeof(peerInfo));
    memcpy(peerInfo.peer_addr, receiverMAC, 6);
    peerInfo.channel = WIFI_CHANNEL;
    peerInfo.encrypt = false;

    if (esp_now_add_peer(&peerInfo) != ESP_OK)
    {
        Serial.println("❌ Failed to add peer");
        while (1)
            delay(1000);
    }

    Serial.println("✅ Peer added successfully");
    Serial.println("🚀 Starting transmission...\n");
}

void loop()
{
    // Simulate pressure sensor readings
    sensorData.pressure1 = 45.0 + (sin(millis() / 1000.0) * 10.0); // Simulate varying pressure
    sensorData.pressure2 = 38.0 + (cos(millis() / 1500.0) * 8.0);  // Different pattern
    sensorData.timestamp = millis();
    sensorData.packet_id = ++packetCounter;

    // Send data
    esp_err_t result = esp_now_send(receiverMAC, (uint8_t *)&sensorData, sizeof(sensorData));

    if (result == ESP_OK)
    {
        Serial.printf("📊 Sending: P1=%.2f PSI, P2=%.2f PSI, ID=%lu\n",
                      sensorData.pressure1, sensorData.pressure2, sensorData.packet_id);
    }
    else
    {
        Serial.printf("❌ Send error: %s\n", esp_err_to_name(result));
    }

    delay(1000); // Send every second
}
/*
  SPI Hardware-Level Diagnostic Tool

  This sketch checks for a valid SPI connection on a specific Chip Select pin.
  It sends a basic "read status" command to the connected device.
  If it receives any valid response, the wiring is correct.
  If it fails, the problem is guaranteed to be in the hardware wiring or a faulty module.
*/
#include <SPI.h>

// Define the Chip Select pin you are using for the MCP2515
#define CS_PIN 4

void setup() {
  Serial.begin(115200);
  while (!Serial); // Wait for serial port to connect

  Serial.println("");
  Serial.println("--- SPI Hardware Diagnostic ---");

  // Initialize SPI bus
  SPI.begin();

  // Prepare the Chip Select pin
  pinMode(CS_PIN, OUTPUT);
  digitalWrite(CS_PIN, HIGH); // Deselect the device initially

  Serial.println("Pinging device on SPI bus...");

  // --- The Test ---
  // We will try to read the MCP2515's STATUS register.

  // 1. Select the chip to talk to
  digitalWrite(CS_PIN, LOW);

  // 2. Send the "Read Status" command byte (0xA0)
  SPI.transfer(0b10101100);

  // 3. Read the single byte response from the chip
  byte status_response = SPI.transfer(0x00);

  // 4. Deselect the chip
  digitalWrite(CS_PIN, HIGH);

  // --- The Verdict ---
  // A floating or non-existent connection will usually return 0xFF or 0x00.
  // Any other value means the chip responded.
  if (status_response != 0xFF && status_response != 0x00) {
    Serial.println("---------------------------------");
    Serial.println(">>> SUCCESS: SPI device found!");
    Serial.print(">>> Device status response: 0b");
    Serial.println(status_response, BIN);
    Serial.println(">>> This confirms your wiring is correct.");
    Serial.println("---------------------------------");
  } else {
    Serial.println("---------------------------------");
    Serial.println(">>> FAILURE: No SPI device found.");
    Serial.println(">>> This confirms a hardware-level issue.");
    Serial.println(">>> Recommended Actions:");
    Serial.println("    1. Use a multimeter to check continuity on all 4 SPI jumper wires.");
    Serial.println("    2. Try a completely different set of jumper wires.");
    Serial.println("    3. The MCP2515 module itself may be faulty.");
    Serial.println("---------------------------------");
  }
}

void loop() {
  // This test only needs to run once.
  delay(5000);
}
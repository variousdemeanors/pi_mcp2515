/*
  ESP32 Dual Analog Pressure Sensor Display

  This sketch reads two analog pressure sensors connected to GPIO 34 and 35
  on an ESP32 WROVER, and displays the calculated PSI values on a 3.2" ST7789 TFT display.

  This code is specifically configured for the "3.2inch ESP32-32E Display" from LCDwiki.
*/

// Step 1: Include the necessary libraries
#include <SPI.h>
#include <TFT_eSPI.h> // Make sure you have the TFT_eSPI library installed

// Step 2: Create an instance of the TFT_eSPI library
TFT_eSPI tft = TFT_eSPI();

// Step 3: Define the pins for your analog sensors
#define SENSOR1_PIN 34
#define SENSOR2_PIN 35

// =========================================================================
// TODO: SENSOR CALIBRATION - REPLACE THESE VALUES WITH YOUR OWN
// =========================================================================
float convertToPSI(int raw_adc_value) {
  // This function converts the raw analog reading (0-4095) to a PSI value.
  // You MUST calibrate this with your specific sensors and voltage dividers.

  // To calibrate:
  // 1. With 0 PSI pressure, read the raw ADC value. This is your ADC_MIN.
  // 2. With a known pressure (e.g., 100 PSI), read the raw ADC value. This is your ADC_AT_KNOWN_PSI.
  // 3. Update the constants below with your measured values.

  // --- PLACEHOLDER VALUES ---
  const int ADC_MIN = 0;         // Raw ADC reading at 0 PSI
  const int ADC_MAX = 4095;      // Raw ADC reading at 300 PSI
  const float PSI_MIN = 0.0;     // PSI at ADC_MIN
  const float PSI_MAX = 300.0;   // PSI at ADC_MAX
  // --- END OF PLACEHOLDER VALUES ---

  // This maps the raw ADC range to the PSI range.
  // It calculates the pressure based on a linear relationship.
  float psi = (float)(raw_adc_value - ADC_MIN) * (PSI_MAX - PSI_MIN) / (float)(ADC_MAX - ADC_MIN) + PSI_MIN;

  // Ensure the calculated pressure doesn't go below zero.
  if (psi < 0) {
    psi = 0;
  }

  return psi;
}
// =========================================================================

void setup() {
  Serial.begin(115200);
  Serial.println("Starting Dual Pressure Sensor Display...");

  // Initialize the TFT display
  tft.init();
  tft.setRotation(1); // Adjust rotation if needed (0-3)
  tft.fillScreen(TFT_BLACK);

  // Set up the text style
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(3); // Set a large font size

  // Check that the sensor pins are valid ADC pins
  if (digitalPinToAnalogChannel(SENSOR1_PIN) < 0 || digitalPinToAnalogChannel(SENSOR2_PIN) < 0) {
    tft.setCursor(10, 10);
    tft.println("ERROR: Invalid ADC pins!");
    while(1); // Halt on error
  }

  // Set the ADC resolution and attenuation for best accuracy on ESP32
  analogReadResolution(12); // 12-bit resolution (0-4095)
  analogSetPinAttenuation(SENSOR1_PIN, ADC_ATTEN_DB_11); // For 0-3.3V range
  analogSetPinAttenuation(SENSOR2_PIN, ADC_ATTEN_DB_11); // For 0-3.3V range
}

void loop() {
  // 1. Read the raw analog values from the sensors
  int sensor1_raw = analogRead(SENSOR1_PIN);
  int sensor2_raw = analogRead(SENSOR2_PIN);

  // 2. Convert the raw values to PSI using your calibration function
  float sensor1_psi = convertToPSI(sensor1_raw);
  float sensor2_psi = convertToPSI(sensor2_raw);

  // 3. Display the values on the TFT screen

  // Display Sensor 1
  tft.setCursor(20, 50); // Set position for the first line (X, Y)
  tft.print("Tank PSI: ");
  tft.print(sensor1_psi, 1); // Print with 1 decimal place
  tft.print("  "); // Add padding to clear old characters

  // Display Sensor 2
  tft.setCursor(20, 100); // Set position for the second line
  tft.print("Line PSI: ");
  tft.print(sensor2_psi, 1); // Print with 1 decimal place
  tft.print("  "); // Add padding to clear old characters

  // 4. Print to Serial monitor for debugging/calibration
  Serial.printf("Sensor 1 -> Raw: %d, PSI: %.1f  |  Sensor 2 -> Raw: %d, PSI: %.1f\n",
                sensor1_raw, sensor1_psi, sensor2_raw, sensor2_psi);

  // 5. Wait for a short period before the next reading
  delay(250); // Refresh rate of ~4 times per second
}
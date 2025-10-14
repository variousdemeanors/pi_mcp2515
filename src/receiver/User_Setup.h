//                            USER DEFINED SETTINGS
//   Set driver type, fonts to be loaded, pins used and SPI control method etc.
//   Optimized for ST7789 display with ESP32
//
//   This file configures TFT_eSPI for ST7789 display with the exact pins
//   specified by the manufacturer setup.

// User defined information reported by "Read_User_Setup" test & diagnostics example
#define USER_SETUP_INFO "User_Setup_ST7789_ESP32"

// ##################################################################################
//
// Section 1. Call up the right driver file and any options for it
//
// ##################################################################################

// Only define ST7789 driver for this display
#define ST7789_DRIVER      // Full configuration option, define additional parameters below for this display

// For ST7789, ST7735, ILI9163 and GC9A01 ONLY, define the pixel width and height in portrait orientation
// These will be set by TFT_eSPI automatically based on the display, but we can override if needed
// #define TFT_WIDTH  240
// #define TFT_HEIGHT 320

// If colours are inverted (white shows as black) then uncomment one of the next
// 2 lines try both options, one of the options should correct the inversion.
// #define TFT_INVERSION_ON
// #define TFT_INVERSION_OFF

// ##################################################################################
//
// Section 2. Define the pins that are used to interface with the display here
//
// ##################################################################################

// Backlight control
#define TFT_BL   27            // LED back-light control pin
#define TFT_BACKLIGHT_ON HIGH  // Level to turn ON back-light (HIGH or LOW)

// For ESP32 with ST7789 - use the manufacturer's exact pin configuration
#define TFT_MISO 12
#define TFT_MOSI 13
#define TFT_SCLK 14
#define TFT_CS   15  // Chip select control pin
#define TFT_DC    2  // Data Command control pin
#define TFT_RST  -1  // Set TFT_RST to -1 if display RESET is connected to ESP32 board RST

// Touch screen pins (if using touch)
#define TOUCH_CS 33     // Chip select pin (T_CS) of touch screen

// ##################################################################################
//
// Section 3. Define the fonts that are to be used here - MINIMAL SET
//
// ##################################################################################

// Enable only essential fonts to save FLASH space for minimal setup
#define LOAD_GLCD   // Font 1. Original Adafruit 8 pixel font needs ~1820 bytes in FLASH
#define LOAD_FONT2  // Font 2. Small 16 pixel high font, needs ~3534 bytes in FLASH, 96 characters
#define LOAD_FONT4  // Font 4. Medium 26 pixel high font, needs ~5848 bytes in FLASH, 96 characters
// Disable larger fonts for minimal setup to save FLASH
// #define LOAD_FONT6  // Font 6. Large 48 pixel font, needs ~2666 bytes in FLASH, only characters 1234567890:-.apm
// #define LOAD_FONT7  // Font 7. 7 segment 48 pixel font, needs ~2438 bytes in FLASH, only characters 1234567890:-.
// #define LOAD_FONT8  // Font 8. Large 75 pixel font needs ~3256 bytes in FLASH, only characters 1234567890:-.
#define LOAD_GFXFF  // FreeFonts. Include access to the 48 Adafruit_GFX free fonts FF1 to FF48 and custom fonts

// Comment out the #define below to stop the SPIFFS filing system and smooth font code being loaded
// For minimal setup, we'll keep this disabled initially
// #define SMOOTH_FONT

// ##################################################################################
//
// Section 4. Other options
//
// ##################################################################################

// Define the SPI clock frequency for ST7789
// ST7789 can typically handle higher frequencies than ST7735
// Start conservative, can increase later if stable
#define SPI_FREQUENCY  40000000   // 40MHz should work well with ST7789

// Optional reduced SPI frequency for reading TFT
#define SPI_READ_FREQUENCY  20000000

// The XPT2046 requires a lower SPI clock rate of 2.5MHz so we define that here:
#define SPI_TOUCH_FREQUENCY  2500000

// For ESP32 - use default VSPI port
// Uncomment the following line if you need to use HSPI port instead
// #define USE_HSPI_PORT

// Transaction support is automatically enabled by the library for ESP32
// #define SUPPORT_TRANSACTIONS
# VLW Font Files for SPIFFS

This directory contains VLW (Vector Line Widget) font files for smooth text rendering on the LVGL interface.

## Required Font Files

Place these VLW font files in this directory:

- `RobotoCondensed-Regular-16.vlw` - Small labels and status text
- `RobotoCondensed-Bold-24.vlw` - Pressure values
- `RobotoCondensed-Bold-32.vlw` - Large pressure numbers (optional)
- `RobotoCondensed-Regular-14.vlw` - Button text and statistics

## Generating VLW Files

Use the TFT_eSPI font creation tool or Processing IDE:

1. **TFT_eSPI Method:**
   - Open `Tools/Create_Smooth_Font/Create_font/Create_font.pde` in Processing IDE
   - Select "Roboto Condensed" font family
   - Choose sizes: 14, 16, 24, 32
   - Select "Bold" for pressure values, "Regular" for labels
   - Export as VLW files

2. **Online Font Tools:**
   - Use web-based VLW generators
   - Ensure 16-bit color depth compatibility
   - Test on small text first

## SPIFFS Upload

Use PlatformIO to upload fonts:

```bash
pio run -t uploadfs -e esp32dev-receiver
```

Or Arduino IDE with ESP32 Sketch Data Upload plugin.

## Font Usage

The receiver will automatically:
- Check for VLW fonts in SPIFFS on startup
- Load smooth fonts if available
- Fall back to built-in Montserrat fonts if VLW files missing
- Display startup message indicating font status
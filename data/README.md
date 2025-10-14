# SPIFFS Data Directory

This directory contains files that will be uploaded to the ESP32's SPIFFS filesystem.

## Structure
- `fonts/` - VLW font files for smooth text rendering
- `images/` - Background images and icons (RGB565 format recommended)
- `config/` - Configuration files and themes

## Font Files
VLW (Vector Loadable Widget) fonts are created using the TFT_eSPI font converter.
These provide smooth, anti-aliased text rendering at any size.

## Image Files
Images should be in RGB565 format (16-bit color) for optimal performance.
Recommended sizes:
- Background: 320x240 pixels
- Icons: 32x32 or 64x64 pixels

## Upload to ESP32
Use the SPIFFS upload task in VS Code:
- "LVGL: UploadFS receiver (SPIFFS)"
- Or: "Remote: UploadFS receiver (SPIFFS)" for remote upload

## File Size Considerations
ESP32 SPIFFS partition is typically 1.5MB. Keep total assets under 1MB for safety.
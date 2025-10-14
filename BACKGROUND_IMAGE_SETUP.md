# Background Image Setup for ESP32 Display

## Overview
The ESP32 pressure display now supports custom background images loaded from an SD card. This saves flash memory and allows easy customization without recompiling firmware.

## Quick Setup

### 1. Prepare Your Image
- Any common format (PNG, JPG, BMP, etc.)
- Will be automatically resized to 240x320 pixels
- Best results with automotive/dashboard-themed images

### 2. Convert Image to RGB565 Binary
```bash
# From the scripts directory
cd /workspaces/pi_mcp2515/scripts
python convert_image_to_sd.py your_image.png background.bin
```

This creates a `background.bin` file optimized for the ESP32 display.

### 3. Copy to SD Card
- Copy `background.bin` to the root of your SD card
- Insert SD card into ESP32 display board
- The firmware will automatically load it on startup

## Technical Details

### Image Format
- **Resolution**: 240×320 pixels (portrait orientation)
- **Color Format**: RGB565 (16-bit color)
- **File Size**: ~150KB for full resolution
- **Location**: Root of SD card as `background.bin`

### SD Card Setup
- **Format**: FAT32 recommended
- **CS Pin**: Pin 5 (adjust in code if different)
- **File System**: Standard SD library

### Fallback Behavior
If no SD card or background image is found:
- Display shows solid black background
- All UI elements remain functional
- Error logged to serial console

## Example Usage

```bash
# Convert a dashboard wallpaper
python convert_image_to_sd.py automotive_dashboard.jpg background.bin 240 320

# The script will output:
# ✅ Converted automotive_dashboard.jpg to background.bin
# 📊 Output size: 153600 bytes (240x320 RGB565)
# 💾 Copy background.bin to your SD card as 'background.bin'
```

## Benefits
- **Flash Memory Savings**: ~150KB saved per image vs embedded arrays
- **Easy Customization**: Swap images without recompiling firmware
- **Multiple Themes**: Store different backgrounds and swap files
- **Better Performance**: No large arrays in flash memory

## Troubleshooting

### No Background Displayed
1. Check SD card is properly inserted and formatted (FAT32)
2. Verify `background.bin` is in root directory (not in folders)
3. Check serial console for error messages
4. Ensure CS pin configuration matches your board

### Poor Image Quality
1. Use high-quality source images
2. Consider automotive/dashboard themes for best visual integration
3. Ensure proper aspect ratio before conversion

### Memory Issues
1. Large images are automatically resized
2. RGB565 format optimized for ESP32 displays
3. SD loading prevents flash memory overflow

## File Locations
- **Converter Script**: `/workspaces/pi_mcp2515/scripts/convert_image_to_sd.py`
- **Background Loader**: `/workspaces/pi_mcp2515/src/receiver/background_image.h`
- **Main Firmware**: `/workspaces/pi_mcp2515/src/receiver/pressure_display_lvgl.ino`
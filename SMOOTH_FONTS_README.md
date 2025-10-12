# Smooth Fonts (VLW) and Gauges

This receiver can load VLW smooth fonts from SPIFFS for crisp text and uses color bar gauges that fill from green → yellow → red. If smooth fonts are not available, it automatically falls back to built‑in fonts.

## Enable smooth fonts in TFT_eSPI

Edit your TFT_eSPI configuration (User_Setup.h or your custom setup) and ensure:

- Uncomment: `#define SMOOTH_FONT`
- The display and touch pins/settings match your board.

If SMOOTH_FONT is not enabled, the sketch will compile and work with built‑in fonts.

## Prepare VLW files

Place these files in SPIFFS under `fonts/` (case‑sensitive paths):

- fonts/Roboto-Bold-36.vlw
- fonts/Roboto-Regular-20.vlw
- fonts/RobotoCondensed-Regular-18.vlw

You can generate VLW fonts using Bodmer's TFT_eSPI tools (Create_font) or the Processing sketch in `Tools/Create_Smooth_Font`.

## Upload fonts to SPIFFS

Option A: Arduino IDE (ESP32 Sketch Data Upload)

1) Create a `data/` folder next to `pressure_display_receiver_fixed.ino`.
2) Inside `data/`, create `fonts/` and copy the `.vlw` files there.
3) Use the "ESP32 Sketch Data Upload" action to upload SPIFFS.

Option B: PlatformIO

Create a simple `platformio.ini` at project root:

```
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
board_build.filesystem = spiffs
```

Put fonts under `data/fonts/` and run `pio run -t uploadfs`.

## Gauge range

Gauge color scale covers 0–200 PSI by default. Adjust GAUGE_MAX_PSI in `pressure_display_receiver_fixed.ino` if needed.

## Notes

- Fonts are optional: if SPIFFS or the files are missing, the sketch uses default bitmap fonts.
- You can swap fonts with any other VLW files; keep sizes balanced (e.g., Bold ~32–40 for main numbers, Regular ~18–22 for small text).
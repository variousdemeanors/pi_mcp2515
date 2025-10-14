# Automotive Dashboard Background
# This is a placeholder for a dashboard background image
#
# To create a real background:
# 1. Create a 320x240 image with automotive styling
# 2. Convert to RGB565 format using online converter or ImageMagick
# 3. Save as dashboard_bg.rgb565
# 4. Upload via SPIFFS
#
# Example conversion with ImageMagick:
# convert dashboard.png -resize 320x240! -depth 16 -define colorspace:auto-grayscale=off RGB565:dashboard_bg.rgb565

# For now, we'll use LVGL's built-in styling and gradients
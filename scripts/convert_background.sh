#!/bin/bash
# Quick background conversion script for ESP32 display

echo "🎨 ESP32 Background Image Converter"
echo "=================================="

# Check if image file was provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <image_file>"
    echo ""
    echo "Example:"
    echo "  $0 automotive_background.png"
    echo "  $0 my_dashboard.jpg"
    echo ""
    echo "The script will:"
    echo "  ✓ Convert image to RGB565 format"
    echo "  ✓ Resize to 240x320 if needed"
    echo "  ✓ Create background.bin for SD card"
    exit 1
fi

IMAGE_FILE="$1"
OUTPUT_FILE="background.bin"

# Check if input file exists
if [ ! -f "$IMAGE_FILE" ]; then
    echo "❌ Error: Image file '$IMAGE_FILE' not found"
    exit 1
fi

echo "📷 Input image: $IMAGE_FILE"
echo "💾 Output file: $OUTPUT_FILE"
echo ""

# Run the Python converter
cd "$(dirname "$0")"
python convert_image_to_sd.py "$IMAGE_FILE" "$OUTPUT_FILE" 240 320

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Conversion complete!"
    echo ""
    echo "📋 Next steps:"
    echo "  1. Copy '$OUTPUT_FILE' to the root of your SD card"
    echo "  2. Insert SD card into ESP32 display board"
    echo "  3. Upload firmware and power on"
    echo "  4. The background will load automatically"
    echo ""
    echo "🔍 File details:"
    ls -lh "$OUTPUT_FILE" 2>/dev/null || echo "Output file created"
else
    echo "❌ Conversion failed"
    exit 1
fi
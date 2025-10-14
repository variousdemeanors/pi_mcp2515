#!/usr/bin/env python3
"""
Quick converter for your automotive background image.
Save your attached image as 'automotive_bg.png' in this directory, then run this script.
"""

import os
import sys
from PIL import Image
import struct

def convert_image_to_rgb565(input_path, output_path):
    """Convert image to RGB565 format for ESP32"""
    try:
        print(f"🎨 Converting: {input_path}")

        # Open and resize image
        img = Image.open(input_path)
        print(f"Original size: {img.size}")

        # Ensure RGB mode
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize to display dimensions (320x240 landscape)
        img = img.resize((320, 240), Image.Resampling.LANCZOS)
        print(f"Resized to: {img.size}")

        # Convert to RGB565
        pixels = img.load()
        width, height = img.size
        rgb565_data = bytearray()

        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]

                # Convert 8-bit RGB to 5-6-5 format
                r565 = (r >> 3) & 0x1F
                g565 = (g >> 2) & 0x3F
                b565 = (b >> 3) & 0x1F

                # Pack into 16-bit value (little-endian)
                rgb565 = (r565 << 11) | (g565 << 5) | b565
                rgb565_data.extend(struct.pack('<H', rgb565))

        # Save RGB565 file
        with open(output_path, 'wb') as f:
            f.write(rgb565_data)

        print(f"✅ Converted successfully!")
        print(f"📊 Output: {len(rgb565_data)} bytes ({width}x{height} RGB565)")
        print(f"💾 Saved as: {output_path}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    # Look for common image file names
    possible_files = [
        'automotive_bg.png',
        'automotive_background.png',  # Added this filename
        'automotive_bg.jpg',
        'background.png',
        'background.jpg',
        'Screenshot 2025-10-13 184928.png'
    ]

    input_file = None
    for filename in possible_files:
        if os.path.exists(filename):
            input_file = filename
            break

    if not input_file:
        print("🖼️  Please save your automotive background image as one of:")
        for filename in possible_files:
            print(f"   - {filename}")
        print("\nThen run this script again!")
        return

    # Convert for SPIFFS
    spiffs_output = "data/images/automotive_bg.rgb565"

    # Create output directory if needed
    os.makedirs("data/images", exist_ok=True)

    if convert_image_to_rgb565(input_file, spiffs_output):
        print("\n🚀 Next steps:")
        print("1. Upload to ESP32 SPIFFS using: 'LVGL: UploadFS receiver (SPIFFS)'")
        print("2. The firmware will automatically load the background")
        print("3. Your automotive particle background will appear!")

if __name__ == "__main__":
    main()
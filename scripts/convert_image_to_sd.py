#!/usr/bin/env python3
"""
Convert image files to RGB565 binary format for ESP32 SD card loading.
Supports common image formats (PNG, JPG, BMP) and converts to the exact
RGB565 format expected by LVGL.
"""

import sys
import os
from PIL import Image
import struct

def rgb888_to_rgb565(r, g, b):
    """Convert RGB888 to RGB565 format"""
    # Convert 8-bit RGB to 5-6-5 bit format
    r565 = (r >> 3) & 0x1F  # 5 bits for red
    g565 = (g >> 2) & 0x3F  # 6 bits for green
    b565 = (b >> 3) & 0x1F  # 5 bits for blue

    # Pack into 16-bit value (little endian)
    rgb565 = (r565 << 11) | (g565 << 5) | b565
    return rgb565

def convert_image_to_rgb565_binary(input_path, output_path, target_width=240, target_height=320):
    """Convert image to RGB565 binary format"""

    try:
        # Open and resize image
        img = Image.open(input_path)
        print(f"Original image size: {img.size}")

        # Convert to RGB mode if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize to target dimensions
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        print(f"Resized to: {img.size}")

        # Convert to RGB565 binary data
        rgb565_data = bytearray()

        for y in range(target_height):
            for x in range(target_width):
                r, g, b = img.getpixel((x, y))
                rgb565 = rgb888_to_rgb565(r, g, b)

                # Pack as little-endian 16-bit value
                rgb565_data.extend(struct.pack('<H', rgb565))

        # Write binary file
        with open(output_path, 'wb') as f:
            f.write(rgb565_data)

        print(f"✅ Converted {input_path} to {output_path}")
        print(f"📊 Output size: {len(rgb565_data)} bytes ({target_width}x{target_height} RGB565)")
        print(f"💾 Copy {output_path} to your SD card as 'background.bin'")

        return True

    except Exception as e:
        print(f"❌ Error converting image: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_image_to_sd.py <input_image> [output_file] [width] [height]")
        print("Example: python convert_image_to_sd.py my_background.png background.bin 240 320")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "background.bin"
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 240
    height = int(sys.argv[4]) if len(sys.argv) > 4 else 320

    if not os.path.exists(input_path):
        print(f"❌ Input file not found: {input_path}")
        sys.exit(1)

    success = convert_image_to_rgb565_binary(input_path, output_path, width, height)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
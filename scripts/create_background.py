#!/usr/bin/env python3
"""
Create a simple automotive-style background for the pressure display
Generates a 320x240 RGB565 image with gradient and grid lines
"""

try:
    from PIL import Image, ImageDraw
    import struct
except ImportError:
    print("Install Pillow: pip install Pillow")
    exit(1)

def create_automotive_background():
    # Create 320x240 image
    width, height = 320, 240
    img = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Create subtle gradient background
    for y in range(height):
        intensity = int(20 + (y / height) * 15)  # Dark gradient
        color = (intensity, intensity, intensity + 5)  # Slight blue tint
        draw.line([(0, y), (width, y)], fill=color)

    # Add subtle grid lines
    grid_spacing = 40
    grid_color = (40, 40, 50)

    # Vertical lines
    for x in range(0, width, grid_spacing):
        draw.line([(x, 0), (x, height)], fill=grid_color, width=1)

    # Horizontal lines
    for y in range(0, height, grid_spacing):
        draw.line([(0, y), (width, y)], fill=grid_color, width=1)

    # Add corner decorations
    corner_color = (60, 60, 80)
    # Top corners
    draw.rectangle([0, 0, 20, 3], fill=corner_color)
    draw.rectangle([width-20, 0, width, 3], fill=corner_color)
    # Bottom corners
    draw.rectangle([0, height-3, 20, height], fill=corner_color)
    draw.rectangle([width-20, height-3, width, height], fill=corner_color)

    return img

def convert_to_rgb565(img):
    """Convert PIL image to RGB565 bytes"""
    pixels = img.load()
    width, height = img.size
    rgb565_data = bytearray()

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            # Convert to 5-6-5 format
            r565 = (r >> 3) & 0x1F
            g565 = (g >> 2) & 0x3F
            b565 = (b >> 3) & 0x1F

            # Pack into 16-bit value (big-endian for ESP32)
            rgb565 = (r565 << 11) | (g565 << 5) | b565
            rgb565_data.extend(struct.pack('>H', rgb565))

    return rgb565_data

if __name__ == "__main__":
    print("Creating automotive dashboard background...")

    # Create the background
    bg_img = create_automotive_background()

    # Save as PNG for preview
    bg_img.save('/workspaces/pi_mcp2515/data/images/dashboard_preview.png')
    print("✅ Preview saved as dashboard_preview.png")

    # Convert to RGB565 and save
    rgb565_data = convert_to_rgb565(bg_img)
    with open('/workspaces/pi_mcp2515/data/images/dashboard_bg.rgb565', 'wb') as f:
        f.write(rgb565_data)

    print(f"✅ RGB565 background created: {len(rgb565_data)} bytes")
    print("📁 Upload to ESP32 using: 'LVGL: UploadFS receiver (SPIFFS)'")
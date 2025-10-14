#!/usr/bin/env python3
"""
PlatformIO Pre-Script: VLW Font Preparation

This script checks for VLW font files in the data/fonts/ directory
and provides helpful information for font setup.
"""

import os
import glob

def check_fonts():
    """Check for VLW font files and provide setup information"""
    
    # Get project directory
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fonts_dir = os.path.join(project_dir, "data", "fonts")
    
    print("🔤 VLW Font Check")
    print("=" * 40)
    
    if not os.path.exists(fonts_dir):
        print(f"⚠️  Fonts directory not found: {fonts_dir}")
        return
    
    # Look for VLW files
    vlw_files = glob.glob(os.path.join(fonts_dir, "*.vlw"))
    
    if vlw_files:
        print(f"✅ Found {len(vlw_files)} VLW font(s):")
        for font_file in vlw_files:
            file_size = os.path.getsize(font_file)
            file_name = os.path.basename(font_file)
            print(f"   📝 {file_name} ({file_size:,} bytes)")
        
        print("\n📡 To upload fonts to ESP32 SPIFFS:")
        print("   pio run -t uploadfs -e esp32dev-receiver")
        
    else:
        print("⚠️  No VLW fonts found in data/fonts/")
        print("\n📖 To create VLW fonts:")
        print("   1. Use Processing IDE or TFT_eSPI font tools")
        print("   2. Generate VLW files for desired fonts/sizes")
        print("   3. Place .vlw files in data/fonts/")
        print("   4. Run: pio run -t uploadfs -e esp32dev-receiver")
        print("\n📁 Expected font files:")
        print("   - NotoSans-Regular-12.vlw")
        print("   - NotoSans-Regular-16.vlw") 
        print("   - NotoSans-Regular-24.vlw")
    
    print("\n" + "=" * 40)

if __name__ == "__main__":
    check_fonts()
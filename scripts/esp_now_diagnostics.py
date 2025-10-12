#!/usr/bin/env python3
"""
ESP-NOW Communication Diagnostics Script

This script helps diagnose ESP-NOW communication issues between
pressure sensor transmitter and display receiver.
"""

import serial
import time
import re
import sys
from datetime import datetime

def scan_serial_ports():
    """Scan for available serial ports"""
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    available_ports = []
    
    print("🔍 Available Serial Ports:")
    for port in ports:
        print(f"  - {port.device}: {port.description}")
        available_ports.append(port.device)
    
    return available_ports

def monitor_transmitter(port, baudrate=115200, duration=30):
    """Monitor transmitter serial output for debugging"""
    print(f"\n📡 Monitoring Transmitter on {port} (115200 baud)")
    print(f"Duration: {duration} seconds")
    print("=" * 50)
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        start_time = time.time()
        success_count = 0
        fail_count = 0
        
        while (time.time() - start_time) < duration:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                
                if "Delivery Success" in line:
                    success_count += 1
                    print(f"[{timestamp}] ✅ {line}")
                elif "Delivery Fail" in line:
                    fail_count += 1
                    print(f"[{timestamp}] ❌ {line}")
                elif "Sensor" in line and "PSI" in line:
                    print(f"[{timestamp}] 📊 {line}")
                elif "Error" in line or "Failed" in line:
                    print(f"[{timestamp}] 🚨 {line}")
                else:
                    print(f"[{timestamp}] 💬 {line}")
            
            time.sleep(0.1)
        
        ser.close()
        
        print("\n" + "=" * 50)
        print(f"📈 Transmission Statistics:")
        print(f"  Success: {success_count}")
        print(f"  Failed:  {fail_count}")
        if success_count + fail_count > 0:
            success_rate = (success_count / (success_count + fail_count)) * 100
            print(f"  Success Rate: {success_rate:.1f}%")
        
        return success_count, fail_count
        
    except serial.SerialException as e:
        print(f"❌ Error opening serial port: {e}")
        return 0, 0
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")
        return success_count, fail_count

def monitor_receiver(port, baudrate=115200, duration=30):
    """Monitor receiver serial output for debugging"""
    print(f"\n📺 Monitoring Receiver on {port} (115200 baud)")
    print(f"Duration: {duration} seconds")
    print("=" * 50)
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        start_time = time.time()
        receive_count = 0
        
        while (time.time() - start_time) < duration:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                
                if "Received:" in line:
                    receive_count += 1
                    print(f"[{timestamp}] 📨 {line}")
                elif "ESP-NOW" in line:
                    print(f"[{timestamp}] 🔧 {line}")
                elif "Error" in line or "Failed" in line:
                    print(f"[{timestamp}] 🚨 {line}")
                else:
                    print(f"[{timestamp}] 💬 {line}")
            
            time.sleep(0.1)
        
        ser.close()
        
        print("\n" + "=" * 50)
        print(f"📈 Reception Statistics:")
        print(f"  Messages Received: {receive_count}")
        
        return receive_count
        
    except serial.SerialException as e:
        print(f"❌ Error opening serial port: {e}")
        return 0
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")
        return receive_count

def check_mac_addresses():
    """Instructions for checking MAC addresses"""
    print("\n🔍 MAC Address Check Instructions:")
    print("=" * 50)
    print("1. Upload 'get_mac_address.ino' to your receiver ESP32")
    print("2. Open Serial Monitor at 115200 baud")
    print("3. Copy the displayed MAC address")
    print("4. Update broadcastAddress[] in pressure_sensor_transmitter.ino")
    print("5. Re-upload the transmitter code")
    print("\nExample MAC address format: {0x1C, 0x69, 0x20, 0x95, 0x9F, 0x50}")

def main():
    print("🔧 ESP-NOW Communication Diagnostics")
    print("====================================")
    
    # Scan for available ports
    ports = scan_serial_ports()
    
    if not ports:
        print("❌ No serial ports found. Make sure ESP32 devices are connected.")
        return
    
    print("\n🛠️  Diagnostic Options:")
    print("1. Monitor Transmitter Output")
    print("2. Monitor Receiver Output") 
    print("3. MAC Address Check Instructions")
    print("4. Exit")
    
    try:
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            if len(ports) == 1:
                port = ports[0]
            else:
                print("\nAvailable ports:")
                for i, port in enumerate(ports):
                    print(f"  {i+1}. {port}")
                port_choice = input("Select port number: ").strip()
                try:
                    port = ports[int(port_choice) - 1]
                except (ValueError, IndexError):
                    print("❌ Invalid port selection")
                    return
            
            duration = input("Monitor duration in seconds (default 30): ").strip()
            try:
                duration = int(duration) if duration else 30
            except ValueError:
                duration = 30
            
            monitor_transmitter(port, duration=duration)
            
        elif choice == "2":
            if len(ports) == 1:
                port = ports[0]
            else:
                print("\nAvailable ports:")
                for i, port in enumerate(ports):
                    print(f"  {i+1}. {port}")
                port_choice = input("Select port number: ").strip()
                try:
                    port = ports[int(port_choice) - 1]
                except (ValueError, IndexError):
                    print("❌ Invalid port selection")
                    return
            
            duration = input("Monitor duration in seconds (default 30): ").strip()
            try:
                duration = int(duration) if duration else 30
            except ValueError:
                duration = 30
            
            monitor_receiver(port, duration=duration)
            
        elif choice == "3":
            check_mac_addresses()
            
        elif choice == "4":
            print("👋 Goodbye!")
            return
            
        else:
            print("❌ Invalid option selected")
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()
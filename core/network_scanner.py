#!/usr/bin/env python3
"""
Network scanner for discovering wireless CAN transceivers on the local network.
Scans for devices that respond to HTTP requests on common ports.
"""

import socket
import threading
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

class NetworkScanner:
    def __init__(self, timeout=2):
        self.timeout = timeout
        self.found_devices = []
        
    def get_local_network(self):
        """Get the local network range (e.g., 192.168.4.0/24)"""
        try:
            # Get local IP address
            print("   🌐 Detecting local network configuration...")
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Extract network prefix (assumes /24)
            ip_parts = local_ip.split('.')
            network_base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
            
            print(f"   📍 Local IP: {local_ip}")
            print(f"   🌐 Network base: {network_base}.x")
            
            return network_base, local_ip
        except Exception as e:
            print(f"   ⚠️  Failed to determine local network: {e}")
            print(f"   🔄 Falling back to Pi AP mode (192.168.4.x)")
            # Default to Pi AP mode network (Pi is .1, devices are .2+)
            return "192.168.4", "192.168.4.1"  # Default fallback
    
    def check_device(self, ip, port=5000, verbose=False):
        """Check if a device at the given IP responds to HTTP requests"""
        try:
            if verbose:
                print(f"   🔍 Checking {ip}:{port}...")
            
            # Try common CAN transceiver endpoints
            endpoints = ['/status', '/obd_data', '/data', '/info', '/']
            
            for endpoint in endpoints:
                try:
                    url = f"http://{ip}:{port}{endpoint}"
                    if verbose:
                        print(f"      🌐 GET {url}")
                    
                    response = requests.get(url, timeout=self.timeout)
                    
                    if response.status_code == 200:
                        if verbose:
                            print(f"      ✅ Response 200 from {endpoint}")
                        
                        # Try to determine device type from response
                        device_info = {
                            'ip': ip,
                            'port': port,
                            'endpoint': endpoint,
                            'status_code': response.status_code,
                            'device_type': 'Unknown'
                        }
                        
                        # Analyze response to determine device type
                        content = response.text.lower()
                        if 'obd' in content or 'can' in content:
                            device_info['device_type'] = 'CAN/OBD Transceiver'
                        elif 'esp32' in content:
                            device_info['device_type'] = 'ESP32 Device'
                        elif 'sensor' in content:
                            device_info['device_type'] = 'Sensor Device'
                        
                        # Try to get more info from response headers
                        server = response.headers.get('Server', '')
                        if server:
                            device_info['server'] = server
                        
                        return device_info
                        
                except requests.exceptions.RequestException:
                    continue
                    
        except Exception:
            pass
        
        return None
    
    def ping_host(self, ip):
        """Check if host is reachable via ping (faster initial check)"""
        try:
            # Use socket connection test instead of ping for better cross-platform support
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, 80))  # Try port 80 first
            sock.close()
            
            if result == 0:
                return True
                
            # Also try port 5000 (common for our devices)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, 5000))
            sock.close()
            
            return result == 0
            
        except Exception:
            return False
    
    def scan_network(self, network_base=None, max_workers=20):
        """Scan the local network for CAN transceivers"""
        if network_base is None:
            network_base, local_ip = self.get_local_network()
        
        print(f"\n🔍 Scanning network {network_base}.0/24 for CAN transceivers...")
        print(f"   📍 Local IP: {local_ip}")
        print(f"   🔧 Max workers: {max_workers}")
        print(f"   ⏱️  Timeout per check: {self.timeout}s")
        
        # First, quickly check the known ESP32 IPs
        esp32_known_ips = ["192.168.4.19", "192.168.4.150", "192.168.4.100"]  # DHCP, static configured, original
        known_device = None
        
        for esp32_ip in esp32_known_ips:
            print(f"\n🎯 Quick check: Testing known ESP32 IP ({esp32_ip})...")
            device = self.check_device(esp32_ip, verbose=True)
            if device:
                print(f"   ✅ Found ESP32 at known IP: {esp32_ip}")
                known_device = device
                break
            else:
                print(f"   ❌ ESP32 not found at {esp32_ip}")
        
        if known_device:
            return [known_device]
        else:
            print(f"   ❌ ESP32 not found at any known IP, continuing full network scan...")
        
        # Generate IP range (skip .0, .1 (Pi), and .255)
        # In AP mode: Pi is always .1, so skip it and scan .2-.254
        if local_ip.endswith('.1'):
            print("   📶 Detected Pi AP mode - scanning for client devices (.2-.254)")
            ip_range = [f"{network_base}.{i}" for i in range(2, 255)]
        else:
            print("   🌐 Scanning full network range (.1-.254)")
            ip_range = [f"{network_base}.{i}" for i in range(1, 255)]
            # Remove our own IP from scan
            if local_ip in ip_range:
                ip_range.remove(local_ip)
                print(f"   ⚠️  Excluded own IP ({local_ip}) from scan")
        
        # Remove the ESP32 known IPs since we already checked them
        for esp32_ip in esp32_known_ips:
            if esp32_ip in ip_range:
                ip_range.remove(esp32_ip)
                print(f"   ⚠️  Excluded already-checked ESP32 IP ({esp32_ip}) from scan")
        
        print(f"   📊 Total IPs to scan: {len(ip_range)}")
        
        # First pass: quick ping check
        print(f"\n🔍 Phase 1: Quick reachability check...")
        reachable_hosts = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            ping_futures = {executor.submit(self.ping_host, ip): ip for ip in ip_range}
            
            completed = 0
            total = len(ping_futures)
            
            for future in as_completed(ping_futures):
                ip = ping_futures[future]
                completed += 1
                
                try:
                    if future.result():
                        reachable_hosts.append(ip)
                        print(f"   ✅ {ip} is reachable")
                except Exception:
                    pass
                
                # Progress update every 20 completions
                if completed % 20 == 0:
                    print(f"   📊 Phase 1 progress: {completed}/{total} ({completed/total*100:.1f}%)")
        
        phase1_time = time.time() - start_time
        print(f"   ✅ Phase 1 completed in {phase1_time:.1f}s")
        print(f"   📍 Found {len(reachable_hosts)} reachable hosts: {', '.join(reachable_hosts) if len(reachable_hosts) <= 10 else f'{len(reachable_hosts)} hosts'}")
        
        # Second pass: check HTTP endpoints on reachable hosts
        print(f"\n🔍 Phase 2: HTTP service detection...")
        devices = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            http_futures = {executor.submit(self.check_device, ip): ip for ip in reachable_hosts}
            
            for future in as_completed(http_futures):
                ip = http_futures[future]
                try:
                    device_info = future.result()
                    if device_info:
                        devices.append(device_info)
                        print(f"   ✅ Found CAN device at {device_info['ip']}: {device_info['device_type']}")
                    else:
                        print(f"   ❌ {ip} - No HTTP service or not a CAN device")
                except Exception as e:
                    print(f"   ❌ {ip} - Error: {e}")
        
        phase2_time = time.time() - start_time
        print(f"   ✅ Phase 2 completed in {phase2_time:.1f}s")
        
        total_time = phase1_time + phase2_time
        print(f"\n🏁 Scan completed in {total_time:.1f}s total")
        print(f"   📍 Found {len(devices)} CAN device(s)")
        
        self.found_devices = devices
        return devices
    
    def scan_specific_ips(self, ip_list):
        """Scan specific IP addresses for CAN transceivers"""
        print(f"\n🔍 Testing specific IPs: {', '.join(ip_list)}")
        devices = []
        
        for ip in ip_list:
            print(f"   🔍 Checking {ip}...")
            try:
                device_info = self.check_device(ip)
                if device_info:
                    devices.append(device_info)
                    print(f"   ✅ Found device at {ip}: {device_info['device_type']}")
                else:
                    print(f"   ❌ {ip} - No HTTP service or not a CAN device")
            except Exception as e:
                print(f"   ❌ {ip} - Error: {e}")
        
        print(f"\n📊 Specific IP scan completed: {len(devices)} device(s) found")
        return devices

def scan_for_can_transceivers():
    """Convenience function to scan for CAN transceivers"""
    scanner = NetworkScanner(timeout=3)
    devices = scanner.scan_network()
    
    if devices:
        print(f"\nFound {len(devices)} potential CAN devices:")
        for i, device in enumerate(devices, 1):
            print(f"{i}. {device['ip']}:{device['port']} - {device['device_type']}")
    else:
        print("No CAN transceivers found on the network.")
    
    return devices

if __name__ == "__main__":
    scan_for_can_transceivers()
import netifaces
import ipaddress
import requests
import threading
from queue import Queue

def get_network_range():
    """
    Finds the active network interface and returns a list of all IP addresses
    in its subnet to be scanned.
    """
    ip_list = []
    try:
        # Find all network interfaces
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            # Skip loopback and docker interfaces
            if interface in ['lo', 'lo0'] or interface.startswith('docker'):
                continue
            
            addrs = netifaces.ifaddresses(interface)
            # Look for IPv4 addresses
            if netifaces.AF_INET in addrs:
                ipv4_info = addrs[netifaces.AF_INET][0]
                ip_addr = ipv4_info.get('addr')
                netmask = ipv4_info.get('netmask')

                if ip_addr and netmask:
                    # Create a network object
                    network = ipaddress.IPv4Network(f"{ip_addr}/{netmask}", strict=False)
                    print(f"Detected active network '{network}' on interface '{interface}'.")
                    
                    # Generate all hosts in the subnet
                    for ip in network.hosts():
                        ip_list.append(str(ip))
                    
                    # We found our primary network, no need to check other interfaces
                    return ip_list

    except Exception as e:
        print(f"Error detecting network range: {e}")
    
    if not ip_list:
        print("Warning: Could not detect an active network interface. Falling back to default AP network scan (192.168.4.0/24).")
        network = ipaddress.IPv4Network("192.168.4.0/24")
        for ip in network.hosts():
            ip_list.append(str(ip))
            
    return ip_list

def _worker(q, found_sensors):
    """Worker thread that takes IPs from a queue and checks them."""
    while not q.empty():
        ip = q.get()
        url = f"http://{ip}/data"
        try:
            # Use a short timeout to avoid waiting long for non-responsive IPs
            response = requests.get(url, timeout=0.5)
            if response.status_code == 200:
                # Try to parse JSON to ensure it's a valid sensor
                response.json()
                found_sensors.append(ip)
                print(f"  - Found a potential sensor at {ip}")
        except (requests.exceptions.RequestException, requests.exceptions.JSONDecodeError):
            # Ignore connection errors, timeouts, or invalid JSON
            pass
        finally:
            q.task_done()

def scan_for_sensors():
    """
    Scans the network for ESP32 sensors and returns a list of IPs
    where sensors were found.
    """
    print("Detecting network range to scan...")
    ips_to_scan = get_network_range()
    
    if not ips_to_scan:
        print("Could not determine any IPs to scan.")
        return []

    print(f"Scanning {len(ips_to_scan)} addresses. This may take a moment...")
    
    found_sensors = []
    q = Queue()

    for ip in ips_to_scan:
        q.put(ip)

    # Use a number of threads to speed up the process
    num_threads = min(50, len(ips_to_scan)) # Cap at 50 threads
    
    for _ in range(num_threads):
        worker = threading.Thread(target=_worker, args=(q, found_sensors))
        worker.daemon = True
        worker.start()

    q.join()  # Wait for all workers to finish
    
    print(f"\nScan complete. Found {len(found_sensors)} potential sensors.")
    return sorted(found_sensors)

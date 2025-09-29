import sys
import argparse
import json
import time
import os
from werkzeug.security import generate_password_hash
from core import config
from core.datalogger import DataLogger
from core.webapp import start_webapp
from core import pid_handler
from core import benchmark
from core import service_manager
from core import sensor_discovery
import requests

# Check if running in virtual environment
def check_virtual_environment():
    """Check if running in a virtual environment and warn if not."""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print(f"✅ Running in virtual environment: {sys.prefix}")
    else:
        print("⚠️  WARNING: Not running in a virtual environment!")
        print("   Consider using: source venv/bin/activate")
        print("   Or run: ./start_obd_system.sh")
        print()

def show_main_menu():
    """Prints the main menu options."""
    print("\n--- Main Menu ---")
    print("1. Network Setup")
    print("2. OBD-II Connection Setup")
    print("3. Datalogging Options")
    print("4. PID Management")
    print("5. ESP32 Sensor Discovery")
    print("6. Web Dashboard Security")
    print("7. Debugging")
    print("8. System Service")
    print("9. Run Benchmark Test")
    print("10. Start Datalogger")
    print("11. Start Web Dashboard")
    print("12. Exit")
    print("-----------------")

def discover_sensors_menu(app_config):
    """Handles the discovery and configuration of ESP32 sensors."""
    print("\n--- ESP32 Sensor Discovery ---")
    
    if 'devices' not in app_config['esp32']:
        app_config['esp32']['devices'] = []

    if app_config['esp32']['devices']:
        print(f"There are currently {len(app_config['esp32']['devices'])} sensors configured.")
        choice = input("Do you want to clear the existing list before scanning? (y/n): ").lower()
        if choice == 'y':
            app_config['esp32']['devices'] = []
            print("Existing sensor list cleared.")

    found_ips = sensor_discovery.scan_for_sensors()

    if not found_ips:
        return

    for ip in found_ips:
        try:
            url = f"http://{ip}/data"
            response = requests.get(url, timeout=1)
            data_sample = response.json()
            
            print("\n----------------------------------------")
            print(f"Found sensor at: {ip}")
            print("Data Sample:")
            print(json.dumps(data_sample, indent=2))
            
            name = input("Enter a name for this sensor (or leave blank to skip): ")
            if name:
                new_device = {"name": name, "url": url}
                app_config['esp32']['devices'].append(new_device)
                print(f"Sensor '{name}' added.")
        except Exception as e:
            print(f"Error processing sensor at {ip}: {e}")

    config.save_config(app_config)
    print("\nSensor configuration saved.")


def debugging_menu(app_config):
    """Handles debugging options."""
    print("\n--- Debugging ---")
    current_status = "ENABLED" if app_config['debugging']['enabled'] else "DISABLED"
    print(f"Current Status: {current_status}")
    print(f"Verbose Log File: {app_config['debugging']['verbose_log_file']}")
    print(f"Raw CAN Log File: {app_config['debugging']['raw_can_log_file']}")
    print("\n1. Toggle Debugging (ON/OFF)")
    print("2. Back to Main Menu")
    choice = input("Enter your choice: ")

    if choice == '1':
        app_config['debugging']['enabled'] = not app_config['debugging']['enabled']
        new_status = "ENABLED" if app_config['debugging']['enabled'] else "DISABLED"
        print(f"Debugging has been {new_status}.")
        config.save_config(app_config)
    elif choice == '2':
        return

def security_menu(app_config):
    """Handles setting the username and password for the web dashboard."""
    print("\n--- Web Dashboard Security ---")
    print("Set the credentials for accessing the web dashboard.")
    new_user = input(f"Enter username (current: {app_config['web_dashboard']['username']}): ")
    new_pass = input("Enter new password (leave blank to keep current): ")

    if new_user:
        app_config['web_dashboard']['username'] = new_user

    if new_pass:
        app_config['web_dashboard']['password_hash'] = generate_password_hash(new_pass)
        print("Web dashboard credentials updated successfully.")

    config.save_config(app_config)

def network_setup_menu(app_config):
    """Handles the network setup menu."""
    print("\n--- Network Setup ---")
    print("Configure how the Raspberry Pi connects to the network.")
    print("1. AP Mode (Create a Wi-Fi Hotspot)")
    print("2. Client Mode (Connect to an existing Wi-Fi network)")
    print("3. Show Network Status")
    print("4. Back to Main Menu")
    choice = input("Enter your choice: ")

    if choice == '1':
        print("\n🌐 Access Point Mode Configuration")
        print("This will create a WiFi hotspot for direct connection to devices.")
        
        use_default = input("Use default SSID/password (datalogger/datalogger)? [y/n]: ").lower()
        if use_default == 'n':
            ssid = input("Enter new AP SSID: ") or "datalogger"
            password = input("Enter new AP Password (min 8 chars): ") or "datalogger"
        else:
            ssid = "datalogger"
            password = "datalogger"
        
        # Use new network manager for proper AP configuration
        try:
            from core.network_manager import NetworkManager
            nm = NetworkManager()
            
            print(f"\n🔧 Configuring AP Mode: {ssid}")
            success = nm.configure_ap_mode(ssid, password)
            
            if success:
                app_config['network']['mode'] = 'AP'
                app_config['network']['ap_ssid'] = ssid
                app_config['network']['ap_password'] = password
                config.save_config(app_config)
                
                print("✅ AP Mode configuration complete!")
                print(f"📡 Network: {ssid} | Password: {password}")
                print("🌐 Access Point IP: 192.168.4.1")
                print("⚠️  REBOOT REQUIRED for changes to take effect")
                
                reboot = input("\nReboot now? (y/n): ").lower()
                if reboot == 'y':
                    print("🔄 Rebooting...")
                    os.system("sudo reboot")
            else:
                print("❌ AP Mode configuration failed!")
                
        except ImportError:
            print("❌ Network manager not available. Using basic configuration...")
            app_config['network']['mode'] = 'AP'
            app_config['network']['ap_ssid'] = ssid
            app_config['network']['ap_password'] = password
            config.save_config(app_config)
            print("⚠️  Manual hostapd configuration required!")
            
    elif choice == '2':
        print("\n🌐 Client Mode Configuration")
        print("This will connect the RPi4 to an existing WiFi network.")
        
        ssid = input("Enter Wi-Fi SSID: ")
        password = input("Enter Wi-Fi Password: ")
        
        if ssid and password:
            try:
                from core.network_manager import NetworkManager
                nm = NetworkManager()
                
                print(f"\n🔧 Configuring Client Mode: {ssid}")
                success = nm.configure_client_mode(ssid, password)
                
                if success:
                    app_config['network']['mode'] = 'Client'
                    app_config['network']['client_ssid'] = ssid
                    app_config['network']['client_password'] = password
                    config.save_config(app_config)
                    
                    print("✅ Client Mode configuration complete!")
                    print(f"📡 Connecting to: {ssid}")
                    print("⚠️  REBOOT REQUIRED for changes to take effect")
                    
                    reboot = input("\nReboot now? (y/n): ").lower()
                    if reboot == 'y':
                        print("🔄 Rebooting...")
                        os.system("sudo reboot")
                else:
                    print("❌ Client Mode configuration failed!")
                    
            except ImportError:
                print("❌ Network manager not available. Using basic configuration...")
                app_config['network']['mode'] = 'Client'
                app_config['network']['client_ssid'] = ssid
                app_config['network']['client_password'] = password
                config.save_config(app_config)
                print("⚠️  Manual wpa_supplicant configuration required!")
        else:
            print("❌ SSID and password are required!")
            
    elif choice == '3':
        print("\n📊 Network Status")
        try:
            from core.network_manager import NetworkManager
            nm = NetworkManager()
            status = nm.get_network_status()
            
            print(f"Mode: {status['mode']}")
            print(f"Interface: {status['interface']}")
            print(f"SSID: {status['ssid'] or 'Unknown'}")
            print(f"IP Address: {status['ip_address'] or 'Unknown'}")
            print(f"Connected: {'Yes' if status['connected'] else 'No'}")
            
        except ImportError:
            print("❌ Network manager not available")
            print("Current config mode:", app_config.get('network', {}).get('mode', 'Unknown'))
        
        input("\nPress Enter to continue...")
        
    elif choice == '4':
        return

def obd_connection_menu(app_config):
    """Handles OBD-II connection configuration."""
    print("\n--- OBD-II Connection Setup ---")
    
    # Display current connection status
    obd_config = app_config.get('network', {}).get('obd_connection', {})
    if obd_config:
        conn_type = obd_config.get('type', 'unknown')
        if conn_type == 'wireless_can':
            esp32_config = obd_config.get('wireless_can', {})
            esp32_ip = esp32_config.get('esp32_ip', 'unknown')
            print(f"Current: Wireless CAN via Acebott ESP32 at {esp32_ip}")
        elif conn_type == 'usb':
            port = obd_config.get('port', 'auto-detect')
            baudrate = obd_config.get('baudrate', 'unknown')
            print(f"Current: USB OBD-II adapter on {port} at {baudrate} baud")
        elif conn_type == 'bluetooth':
            port = obd_config.get('port', 'auto-detect')
            baudrate = obd_config.get('baudrate', 'unknown')
            print(f"Current: Bluetooth OBD-II adapter ({port}) at {baudrate} baud")
        else:
            print(f"Current: {conn_type} (unknown configuration)")
    else:
        print("Current: No OBD-II connection configured")
    
    print("\n1. Configure USB OBD-II Adapter")
    print("2. Configure Bluetooth OBD-II Adapter") 
    print("3. Configure Wireless CAN via Acebott ESP32")
    print("4. Test Current Connection")
    print("5. Remove OBD-II Configuration")
    print("6. Back to Main Menu")
    
    choice = input("Enter your choice: ")
    
    if choice == '1':
        _configure_traditional_obd(app_config, 'usb')
    elif choice == '2':
        _configure_traditional_obd(app_config, 'bluetooth')
    elif choice == '3':
        _configure_wireless_can(app_config)
    elif choice == '4':
        _test_obd_connection(app_config)
    elif choice == '5':
        if 'network' in app_config and 'obd_connection' in app_config['network']:
            del app_config['network']['obd_connection']
            config.save_config(app_config)
            print("OBD-II configuration removed.")
        else:
            print("No OBD-II configuration to remove.")
    elif choice == '6':
        return

def _configure_traditional_obd(app_config, conn_type):
    """Configure USB or Bluetooth OBD connection."""
    print(f"\n--- {conn_type.upper()} OBD-II Setup ---")
    
    if conn_type == 'usb':
        port_str = input("Enter USB port (e.g., /dev/ttyUSB0, COM3) or leave blank to auto-detect: ")
    else:  # bluetooth
        port_str = input("Enter Bluetooth MAC address or leave blank to auto-detect: ")
    
    port = port_str if port_str else None
    fast_mode = input("Enable fast mode for faster PID reading? (y/n): ").lower() == 'y'
    
    print(f"Testing {conn_type} connection...")
    
    # Note: We'd normally test the connection here, but setup.py has that logic
    # For now, just save the configuration
    if 'network' not in app_config:
        app_config['network'] = {}
    
    app_config['network']['obd_connection'] = {
        'type': conn_type,
        'port': port,
        'baudrate': 115200,  # Default - will be auto-detected later
        'fast': fast_mode
    }
    
    config.save_config(app_config)
    print(f"{conn_type.upper()} OBD-II configuration saved.")
    print("Note: Connection will be tested when datalogger starts.")

def _configure_wireless_can(app_config):
    """Configure wireless CAN via Acebott ESP32."""
    print("\n--- Wireless CAN via Acebott ESP32 Setup ---")
    print("This option uses your Acebott ESP32 Max with MCP2515 as a wireless OBD2 adapter.")
    print("Requirements:")
    print("  ✓ Acebott ESP32 flashed with OBD2 scanner firmware")
    print("  ✓ ESP32 connected to vehicle OBD2 port (CANH/CANL)")
    print("  ✓ ESP32 connected to same WiFi network as RPi4")
    print("")
    
    esp32_ip = input("Enter Acebott ESP32 IP address [192.168.4.1]: ") or "192.168.4.1"
    esp32_port = input("Enter ESP32 HTTP port [5000]: ") or "5000"
    timeout = input("Enter connection timeout in seconds [5]: ") or "5"
    
    try:
        esp32_port = int(esp32_port)
        timeout = int(timeout)
    except ValueError:
        print("❌ Invalid port or timeout value. Using defaults.")
        esp32_port = 5000
        timeout = 5
    
    # Test connection to ESP32
    print(f"\n🔍 Testing connection to Acebott ESP32 at {esp32_ip}:{esp32_port}...")
    try:
        import requests
        response = requests.get(f"http://{esp32_ip}:{esp32_port}/status", timeout=timeout)
        if response.status_code == 200:
            print("✅ Successfully connected to Acebott ESP32!")
            print("📊 ESP32 is ready for wireless OBD2 data logging")
        else:
            print(f"⚠️  ESP32 responded with status {response.status_code}")
            print("   Continuing anyway - may work when vehicle is running")
    except Exception as e:
        print(f"❌ Could not connect to ESP32: {e}")
        print("   Please check:")
        print("   - ESP32 IP address and WiFi connection")
        print("   - ESP32 firmware is running")  
        print("   - Network connectivity")
        
        continue_anyway = input("\nContinue with setup anyway? (y/n): ").lower()
        if continue_anyway != 'y':
            print("Setup cancelled.")
            return
    
    # Save wireless CAN configuration
    if 'network' not in app_config:
        app_config['network'] = {}
    
    app_config['network']['obd_connection'] = {
        'type': 'wireless_can',
        'port': None,  # Not used for wireless
        'baudrate': 115200,  # Not used for wireless
        'fast': True,  # Not used for wireless
        'wireless_can': {
            'esp32_ip': esp32_ip,
            'esp32_port': esp32_port,
            'endpoint': '/obd_data',
            'timeout': timeout
        }
    }
    
    config.save_config(app_config)
    print("✅ Wireless CAN configuration saved!")
    print("🚗 Ready for wireless OBD2 data logging with Acebott ESP32")

def _test_obd_connection(app_config):
    """Test the current OBD connection."""
    obd_config = app_config.get('network', {}).get('obd_connection', {})
    if not obd_config:
        print("❌ No OBD-II connection configured. Please configure one first.")
        return
    
    conn_type = obd_config.get('type', 'unknown')
    print(f"\n🔍 Testing {conn_type} OBD-II connection...")
    
    if conn_type == 'wireless_can':
        # Test wireless CAN connection
        wireless_config = obd_config.get('wireless_can', {})
        esp32_ip = wireless_config.get('esp32_ip')
        esp32_port = wireless_config.get('esp32_port')
        timeout = wireless_config.get('timeout', 5)
        
        if not esp32_ip or not esp32_port:
            print("❌ Invalid wireless CAN configuration")
            return
        
        try:
            import requests
            response = requests.get(f"http://{esp32_ip}:{esp32_port}/status", timeout=timeout)
            if response.status_code == 200:
                print("✅ Acebott ESP32 is responding!")
                
                # Try to get OBD data
                try:
                    obd_response = requests.get(f"http://{esp32_ip}:{esp32_port}/obd_data", timeout=timeout)
                    if obd_response.status_code == 200:
                        data = obd_response.json()
                        print(f"📊 OBD data received: {len(data)} PIDs")
                        print("✅ Wireless CAN connection is working!")
                    else:
                        print(f"⚠️  ESP32 OBD endpoint returned status {obd_response.status_code}")
                        print("   This may be normal if vehicle is not running")
                except Exception as e:
                    print(f"⚠️  Could not get OBD data: {e}")
                    print("   ESP32 is responding but may not be connected to vehicle")
            else:
                print(f"❌ ESP32 responded with status {response.status_code}")
        except Exception as e:
            print(f"❌ Could not connect to ESP32: {e}")
            
    else:
        # Test traditional OBD connection (USB/Bluetooth)
        print("Testing traditional OBD connection...")
        print("Note: This requires the python-obd library and actual hardware connection.")
        print("Connection will be fully tested when datalogger starts.")
        
        port = obd_config.get('port')
        baudrate = obd_config.get('baudrate')
        if port:
            print(f"Configuration: {conn_type} on {port} at {baudrate} baud")
        else:
            print(f"Configuration: {conn_type} with auto-detection")
    
    input("\nPress Enter to continue...")

def datalogging_options_menu(app_config):
    """Handles the datalogging options menu."""
    print("\n--- Datalogging Options ---")
    print("1. Set Log File Output Path")
    print("2. Configure Log Filename Format")
    print("3. Set Log Rotation Policy")
    print("4. Set Logging Interval (ms)")
    print("5. Set Display Units")
    print("6. Back to Main Menu")
    choice = input("Enter your choice: ")

    if choice == '1':
        path = input(f"Enter new output path (current: {app_config['datalogging']['output_path']}): ")
        app_config['datalogging']['output_path'] = path
        print("Output path updated.")
    elif choice == '2':
        use_default = input("Use default naming (e.g., '2023-10-27_14-30-00_datalog.csv')? [y/n]: ").lower()
        if use_default == 'n':
            fname = input("Enter custom filename (use strftime format, e.g., 'log_%Y%m%d.csv'): ")
            app_config['datalogging']['custom_filename'] = fname
        else:
            app_config['datalogging']['custom_filename'] = None
        print("Filename format updated.")
    elif choice == '3':
        policy = input(f"Enter rotation policy [session/static] (current: {app_config['datalogging']['log_rotation']}): ").lower()
        if policy in ['static', 'session']:
            app_config['datalogging']['log_rotation'] = policy
            print("Log rotation policy updated.")
        else:
            print("Invalid policy. Please choose 'session' or 'static'.")
    elif choice == '4':
        try:
            interval = int(input(f"Enter new logging interval in milliseconds (current: {app_config['datalogging']['logging_interval_ms']}): "))
            if interval >= 0:
                app_config['datalogging']['logging_interval_ms'] = interval
                print("Logging interval updated.")
            else:
                print("Interval must be a positive number.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    elif choice == '5':
        units = input(f"Enter display units [metric/imperial] (current: {app_config['datalogging']['display_units']}): ").lower()
        if units in ['metric', 'imperial']:
            app_config['datalogging']['display_units'] = units
            print("Display units updated.")
        else:
            print("Invalid choice. Please choose 'metric' or 'imperial'.")
    elif choice == '6':
        return

    config.save_config(app_config)

def pid_management_menu(app_config):
    """Handles the PID management menu."""
    while True:
        print("\n--- PID Management ---")
        print("1. Discover and Save Supported PIDs from Vehicle")
        print("2. Select PIDs to Log")
        print("3. View Currently Selected PIDs")
        print("4. Back to Main Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            print("Attempting to connect to vehicle to discover PIDs. This may take a moment...")
            supported_pids = pid_handler.discover_pids(app_config)
            if supported_pids:
                pid_names = [p.name for p in supported_pids]
                app_config['pid_management']['all_supported_pids'] = pid_names
                config.save_config(app_config)
                print(f"Successfully discovered and saved {len(pid_names)} supported PIDs.")
            else:
                print("Could not discover any PIDs. Please check connection and ignition.")
        elif choice == '2':
            all_pids = app_config['pid_management']['all_supported_pids']
            if not all_pids:
                print("No PIDs discovered yet. Please run option 1 first.")
                continue
            print("Available PIDs to log:")
            for i, pid_name in enumerate(all_pids):
                print(f"  {i+1}. {pid_name}")
            selection = input("Enter the numbers of the PIDs you want to log (comma-separated): ")
            try:
                indices = [int(s.strip()) - 1 for s in selection.split(',')]
                selected = [all_pids[i] for i in indices if 0 <= i < len(all_pids)]
                app_config['pid_management']['selected_pids'] = selected
                config.save_config(app_config)
                print(f"Selected {len(selected)} PIDs to be logged.")
            except ValueError:
                print("Invalid selection. Please enter numbers only.")
        elif choice == '3':
            print("Currently selected PIDs for logging:")
            for pid in app_config['pid_management']['selected_pids']:
                print(f"  - {pid}")
        elif choice == '4':
            break

def service_menu(app_config):
    """Handles system service installation and configuration."""
    print("\n--- System Service Management ---")
    print("1. Install systemd Service (for autostart on boot)")
    print("2. Configure Autostart Behavior")
    print("3. Back to Main Menu")
    choice = input("Enter your choice: ")

    if choice == '1':
        service_manager.install_service()
    elif choice == '2':
        autostart = input("Autostart on boot [none/datalogger/dashboard]: ").lower()
        if autostart in ['none', 'datalogger', 'dashboard']:
            app_config['service']['autostart'] = autostart
            config.save_config(app_config)
            print(f"Autostart behavior set to '{autostart}'.")
        else:
            print("Invalid choice.")
    elif choice == '3':
        return

def run_benchmark_menu(app_config):
    """Runs the benchmark test and displays the results."""
    results = benchmark.run_benchmark(app_config)
    if not results: return
    print("\n--- Benchmark Results ---")
    # A more detailed printout could be added here
    print(results)
    save = input("\nSave results? [y/n]: ").lower()
    if save == 'y':
        with open(app_config['benchmark']['results_file'], 'w') as f:
            json.dump(results, f, indent=2)

def start_datalogger(app_config):
    """Starts the datalogger and displays real-time stats."""
    logger = DataLogger(config=app_config)
    logger.daemon = True
    logger.start()
    logger.start_log()
    print("Datalogger starting... Press Ctrl+C to stop.")

    last_count = 0
    last_time = time.time()

    # Keys from the data_store that we don't want to display in the live table
    internal_keys = ['log_active', 'connection_status', 'last_stop_time', 'log_file_name', 'pid_read_count']

    try:
        while logger.is_alive():
            os.system('clear' if os.name == 'posix' else 'cls')

            current_time = time.time()
            delta_time = current_time - last_time
            try:
                current_count = int(logger.data_store.get("pid_read_count", 0))
            except (ValueError, TypeError):
                current_count = 0
            try:
                last_count_int = int(last_count)
            except (ValueError, TypeError):
                last_count_int = 0
            delta_count = current_count - last_count_int

            rate = (delta_count / delta_time) if delta_time > 0 else 0

            last_count = current_count
            last_time = current_time

            log_file = logger.data_store.get("log_file_name", "(Starting...)")
            print("--- Live Datalogging ---")
            print(f"Saving to: {log_file}")
            print(f"Read Rate: {rate:.2f} PID/s")
            print("-" * 30)

            # Create a sorted list of sensor keys to display
            display_keys = sorted([key for key in logger.data_store.keys() if key not in internal_keys])

            # Print in two columns
            midpoint = (len(display_keys) + 1) // 2
            col1_keys = display_keys[:midpoint]
            col2_keys = display_keys[midpoint:]

            for i in range(midpoint):
                # --- Column 1 ---
                key1 = col1_keys[i]
                val1 = logger.data_store.get(key1)
                display_key1 = key1.replace('_', ' ').title()

                # CAN-only: always display as string
                val1_str = str(val1)
                term1 = f"{display_key1.ljust(25)}: {val1_str.ljust(20)}"

                # --- Column 2 ---
                term2 = ""
                if i < len(col2_keys):
                    key2 = col2_keys[i]
                    val2 = logger.data_store.get(key2)
                    display_key2 = key2.replace('_', ' ').title()

                    # CAN-only: always display as string
                    val2_str = str(val2)
                    term2 = f"{display_key2.ljust(25)}: {val2_str}"

                print(term1 + term2)

            print("-" * 30)
            print("Press Ctrl+C to stop logging.")

            time.sleep(1)

    except KeyboardInterrupt:
        logger.stop()
        logger.join()
        print("\n\nDatalogger stopped by user.")

def start_dashboard(app_config):
    """Starts the web dashboard."""
    print("[DEBUG] Creating DataLogger instance for dashboard...")
    logger = DataLogger(config=app_config)
    logger.daemon = True
    print("[DEBUG] Starting DataLogger thread for dashboard...")
    logger.start()
    print("[DEBUG] DataLogger thread started. Calling start_webapp...")
    start_webapp(config=app_config, datalogger=logger)
    print("[DEBUG] start_webapp function has returned. This should only happen on shutdown.")

def main():
    """Main function to run the application."""
    
    # Check virtual environment status
    check_virtual_environment()
    
    parser = argparse.ArgumentParser(description="OBD-II Datalogger and Dashboard")
    parser.add_argument('--start-service', action='store_true', help='Start the application as a service.')
    args = parser.parse_args()

    app_config = config.load_config()
    if not app_config: sys.exit(1)

    # Allow running without an OBD connection for development/testing.
    # If OBD is not configured, we will still allow starting the web dashboard
    # and other tooling. The DataLogger will operate in "external sensors only" mode.
    if not app_config.get('network', {}).get('obd_connection'):
        print("[WARN] No OBD connection configured. You can still run the web dashboard and ESP32 features.")
        print("       To configure OBD later, run:  python3 setup.py")

    if args.start_service:
        autostart_mode = app_config.get('service', {}).get('autostart', 'none')
        if autostart_mode == 'datalogger':
            start_datalogger(app_config)
        elif autostart_mode == 'dashboard':
            start_dashboard(app_config)
    else:
        while True:
            show_main_menu()
            choice = input("Enter your choice (1-12): ")
            if choice == '1': network_setup_menu(app_config)
            elif choice == '2': obd_connection_menu(app_config)
            elif choice == '3': datalogging_options_menu(app_config)
            elif choice == '4': pid_management_menu(app_config)
            elif choice == '5': discover_sensors_menu(app_config)
            elif choice == '6': security_menu(app_config)
            elif choice == '7': debugging_menu(app_config)
            elif choice == '8': service_menu(app_config)
            elif choice == '9': run_benchmark_menu(app_config)
            elif choice == '10': start_datalogger(app_config)
            elif choice == '11': start_dashboard(app_config)
            elif choice == '12': sys.exit(0)

if __name__ == "__main__":
    main()

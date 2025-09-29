"""
Wireless OBD Adapter for Acebott ESP32 Max with MCP2515 CAN Transceiver

This module provides a python-obd compatible interface for communicating with
the Acebott ESP32 board that acts as a wireless CAN/OBD2 adapter. The ESP32
connects to the vehicle's OBD2 port via MCP2515 and transmits data over WiFi.

Compatible with existing RPi4 datalogger without modifying core functionality.
"""

import time
import requests
import json
import threading
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WirelessOBDAdapter:
    """
    A python-obd compatible adapter that communicates with the Acebott ESP32 
    via HTTP requests over WiFi. The ESP32 acts as a CAN/OBD2 gateway.
    """
    
    def __init__(self, esp32_ip="192.168.4.1", esp32_port=5000, timeout=5):
        self.esp32_ip = esp32_ip
        self.esp32_port = esp32_port
        self.timeout = timeout
        self.base_url = f"http://{esp32_ip}:{esp32_port}"
        self.is_connected = False
        self.last_data = {}
        self.data_lock = threading.Lock()
        
        # OBD2 PID mapping (matches Acebott firmware)
        # pid_mapping will be constructed lazily to avoid importing python-obd
        # at module import time on systems that don't have it installed.
        self.pid_mapping = None
        # Background data fetching thread control
        self.data_thread = None
        self.stop_thread = False
        
    # Start background data fetching thread helper is managed via instance attributes
    # (initialized in __init__).
        
    def connect(self):
        """Attempt to connect to the Acebott ESP32 OBD2 scanner."""
        try:
            # Test connection
            response = requests.get(f"{self.base_url}/status", timeout=self.timeout)
            if response.status_code == 200:
                logger.info(f"✅ Connected to Acebott ESP32 at {self.esp32_ip}:{self.esp32_port}")
                
                # Start data fetching thread
                self.start_data_thread()
                return True
            else:
                logger.error(f"❌ ESP32 responded with status {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to connect to ESP32: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the ESP32."""
        self.stop_thread = True
        if self.data_thread and self.data_thread.is_alive():
            self.data_thread.join(timeout=2)
        self.is_connected = False
        logger.info("Disconnected from Acebott ESP32")
    
    def start_data_thread(self):
        """Start background thread to continuously fetch data from ESP32."""
        if self.data_thread is None or not self.data_thread.is_alive():
            self.stop_thread = False
            self.data_thread = threading.Thread(target=self._data_loop, daemon=True)
            self.data_thread.start()

    def _ensure_pid_mapping(self):
        """Build pid_mapping lazily. If python-obd is available, use command
        objects as keys; otherwise fall back to string keys matching the
        JSON payload returned by the ESP32.
        """
        if self.pid_mapping is not None:
            return
        try:
            import obd as _obd
            self.pid_mapping = {
                _obd.commands.RPM: "rpm",
                _obd.commands.ENGINE_LOAD: "engineLoad",
                _obd.commands.INTAKE_TEMP: "intakeTemp",
                _obd.commands.INTAKE_PRESSURE: "manifoldPressure",
                _obd.commands.SPEED: "vehicleSpeed",
                _obd.commands.THROTTLE_POS: "throttlePos",
                _obd.commands.COOLANT_TEMP: "coolantTemp",
                _obd.commands.MAF: "mafRate"
            }
        except Exception:
            # Fallback: use simple string keys (the adapter still returns JSON fields)
            self.pid_mapping = {
                'RPM': 'rpm', 'ENGINE_LOAD': 'engineLoad', 'INTAKE_TEMP': 'intakeTemp',
                'INTAKE_PRESSURE': 'manifoldPressure', 'SPEED': 'vehicleSpeed',
                'THROTTLE_POS': 'throttlePos', 'COOLANT_TEMP': 'coolantTemp', 'MAF': 'mafRate'
            }

    def _data_loop(self):
        """Background loop to poll ESP32 for data and update last_data."""
        self._ensure_pid_mapping()
        while not self.stop_thread:
            try:
                response = requests.get(f"{self.base_url}/data", timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    with self.data_lock:
                        self.last_data = data
                        self.last_data['timestamp'] = time.time()
                else:
                    logger.warning(f"ESP32 data fetch returned {response.status_code}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Data fetch error: {e}")
                # Brief pause before retry
                time.sleep(0.2)

            # OPTIMIZED: Fetch data every 50ms (20Hz) for real-time performance
            time.sleep(0.05)  # 50ms = 20Hz polling
    
    def query(self, cmd, force=False):
        """
        Query a specific OBD2 command from the ESP32.
        
        Args:
            cmd: OBD command object (e.g., obd.commands.RPM)
            force: Ignored for wireless adapter
            
        Returns:
            OBD Response object or None if no data available
        """
        if not self.is_connected:
            return None
            
        # Get the latest data
        with self.data_lock:
            if not self.last_data:
                return None
            
            data_copy = self.last_data.copy()
        
        # Check if data is recent (within 5 seconds)
        if time.time() - data_copy.get('timestamp', 0) > 5:
            logger.warning("ESP32 data is stale")
            return None
        
        # Map OBD command to ESP32 data field
        if cmd not in self.pid_mapping:
            logger.debug(f"PID not supported by wireless adapter: {cmd}")
            return None

        field_name = self.pid_mapping[cmd]
        if field_name not in data_copy:
            return None

        raw_value = data_copy[field_name]

        # Create OBD response object
        return self._create_obd_response(cmd, raw_value)
    
    def _create_obd_response(self, cmd, raw_value):
        """Create a python-obd compatible response object."""
        try:
            # Convert raw value to appropriate units/format. Use lazy import
            # so this module doesn't require python-obd at import time.
            try:
                import obd as _obd
                has_obd = True
            except Exception:
                _obd = None
                has_obd = False

            # Determine a canonical command name for mapping
            cmd_name = None
            if hasattr(cmd, 'name'):
                cmd_name = getattr(cmd, 'name')
            else:
                # If cmd is a string key, normalize it
                cmd_name = str(cmd).upper()

            # Map based on canonical PID names
            if 'RPM' in cmd_name:
                value = float(raw_value)
                if has_obd:
                    value = value * _obd.Unit.rpm
            elif 'ENGINE_LOAD' in cmd_name or 'LOAD' in cmd_name:
                value = float(raw_value)
                if has_obd:
                    value = value * _obd.Unit.percent
            elif 'INTAKE_TEMP' in cmd_name or 'IAT' in cmd_name or 'COOLANT_TEMP' in cmd_name:
                value = float(raw_value)
                if has_obd:
                    value = value * _obd.Unit.celsius
            elif 'INTAKE_PRESSURE' in cmd_name or 'MANIFOLD' in cmd_name or 'FUEL_RAIL' in cmd_name:
                value = float(raw_value)
                if has_obd:
                    value = value * _obd.Unit.kilopascal
            elif 'SPEED' in cmd_name:
                value = float(raw_value)
                if has_obd:
                    value = value * _obd.Unit.kph
            elif 'THROTTLE' in cmd_name:
                value = float(raw_value)
                if has_obd:
                    value = value * _obd.Unit.percent
            elif 'MAF' in cmd_name:
                value = float(raw_value)
                if has_obd:
                    value = value * _obd.Unit.grams_per_second
            else:
                value = float(raw_value)
            
            # Create mock response object
            class MockResponse:
                def __init__(self, command, value):
                    self.command = command
                    self.value = value
                    self.time = time.time()
                
                def __str__(self):
                    return f"{self.command.name}: {self.value}"
            
            return MockResponse(cmd, value)
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error creating OBD response for {cmd.name}: {e}")
            return None
    
    def supported_commands(self):
        """Return list of supported OBD commands."""
        if self.pid_mapping is None:
            self._ensure_pid_mapping()
        return list(self.pid_mapping.keys())
    
    def __enter__(self):
        """Context manager entry."""
        if self.connect():
            return self
        else:
            raise ConnectionError("Failed to connect to Acebott ESP32")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class WirelessOBDConnection:
    """
    A python-obd compatible connection class that uses the WirelessOBDAdapter.
    This integrates seamlessly with existing datalogger code.
    """
    
    def __init__(self, esp32_config):
        """
        Initialize wireless OBD connection.
        
        Args:
            esp32_config: Dictionary with esp32_ip, esp32_port, timeout
        """
        self.adapter = WirelessOBDAdapter(
            esp32_ip=esp32_config.get('esp32_ip', '192.168.4.1'),
            esp32_port=esp32_config.get('esp32_port', 5000),
            timeout=esp32_config.get('timeout', 5)
        )
        self.is_connected = False
        
    def start(self):
        """Start the wireless OBD connection."""
        success = self.adapter.connect()
        self.is_connected = success
        return success
    
    def stop(self):
        """Stop the wireless OBD connection."""
        self.adapter.disconnect()
        self.is_connected = False
    
    def query(self, cmd, force=False):
        """Query an OBD command."""
        if not self.is_connected:
            return None
        return self.adapter.query(cmd, force)
    
    def supported_commands(self):
        """Get supported commands."""
        return self.adapter.supported_commands()
    
    @property
    def status(self):
        """Connection status."""
        return "Connected" if self.is_connected else "Disconnected"


def create_wireless_obd_connection(config):
    """
    Factory function to create a wireless OBD connection.
    
    Args:
        config: Configuration dictionary from config.json
        
    Returns:
        WirelessOBDConnection instance or None if config invalid
    """
    try:
        wireless_config = config['network']['obd_connection']['wireless_can']
        return WirelessOBDConnection(wireless_config)
    except KeyError as e:
        logger.error(f"Missing wireless CAN configuration: {e}")
        return None


if __name__ == "__main__":
    # Test the wireless adapter directly
    logging.basicConfig(level=logging.DEBUG)
    
    print("Testing Acebott ESP32 Wireless OBD Adapter...")
    
    adapter = WirelessOBDAdapter()
    if adapter.connect():
        print("\u2705 Connected successfully!")
        
        # Test a few commands if python-obd is available
        time.sleep(2)  # Let some data accumulate
        try:
            import obd
            cmds = [obd.commands.RPM, obd.commands.COOLANT_TEMP, obd.commands.SPEED]
        except Exception:
            cmds = None

        if cmds:
            for cmd in cmds:
                response = adapter.query(cmd)
                if response:
                    print(f"\ud83d\udcca {response}")
                else:
                    print(f"\u274c No data for {getattr(cmd, 'name', str(cmd))}")
        else:
            print("python-obd not available; skipping command-level tests")
        
        adapter.disconnect()
    else:
        print("❌ Failed to connect")
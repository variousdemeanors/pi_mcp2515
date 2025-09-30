"""
Wireless OBD Adapter for ESP32 ESP-NOW Coordinator with MCP2515 CAN Transceiver

This module provides a python-obd compatible interface for communicating with
an ESP32 coordinator that receives data from a CAN-connected ESP32 via ESP-NOW.
The coordinator forwards data to the Pi via serial over GPIO.

Compatible with existing RPi datalogger without modifying core functionality.
"""

import time
import serial
import json
import threading
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WirelessOBDAdapter:
    """
    A python-obd compatible adapter that communicates with the ESP32 coordinator
    via serial over GPIO. The coordinator receives CAN/OBD2 data via ESP-NOW.
    """
    
    def __init__(self, serial_port="/dev/ttyAMA0", baudrate=115200, timeout=5):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        self.is_connected = False
        self.last_data = {}
        self.data_lock = threading.Lock()
        
        # OBD2 PID mapping (matches ESP32 firmware)
        # pid_mapping will be constructed lazily to avoid importing python-obd
        # at module import time on systems that don't have it installed.
        self.pid_mapping = None
        # Background data fetching thread control
        self.data_thread = None
        self.stop_thread = False
        
    # Start background data fetching thread helper is managed via instance attributes
    # (initialized in __init__).
        
    def connect(self):
        """Attempt to connect to the ESP32 coordinator via serial."""
        try:
            self.serial_conn = serial.Serial(self.serial_port, self.baudrate, timeout=self.timeout)
            # Test connection by sending a ping
            self.serial_conn.write(b"PING\n")
            response = self.serial_conn.readline().decode().strip()
            if response == "PONG":
                logger.info(f"✅ Connected to ESP32 coordinator on {self.serial_port}")
                self.is_connected = True
                # Start data fetching thread
                self.start_data_thread()
                return True
            else:
                logger.error(f"❌ ESP32 coordinator responded with: {response}")
                self.serial_conn.close()
                return False
                
        except serial.SerialException as e:
            logger.error(f"❌ Failed to connect to ESP32 coordinator: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the ESP32 coordinator."""
        self.stop_thread = True
        if self.data_thread and self.data_thread.is_alive():
            self.data_thread.join(timeout=2)
        if self.serial_conn:
            self.serial_conn.close()
        self.is_connected = False
        logger.info("Disconnected from ESP32 coordinator")
    
    def start_data_thread(self):
        """Start background thread to continuously fetch data from ESP32."""
        if self.data_thread is None or not self.data_thread.is_alive():
            self.stop_thread = False
            self.data_thread = threading.Thread(target=self._data_loop, daemon=True)
            self.data_thread.start()

    def _ensure_pid_mapping(self):
        """Build pid_mapping lazily. Use string keys for PID names."""
        if self.pid_mapping is not None:
            return
        self.pid_mapping = {
            "RPM": "rpm",
            "ENGINE_LOAD": "engineLoad",
            "INTAKE_TEMP": "intakeTemp",
            "INTAKE_PRESSURE": "manifoldPressure",
            "SPEED": "vehicleSpeed",
            "THROTTLE_POS": "throttlePos",
            "COOLANT_TEMP": "coolantTemp"
            # "MAF": "mafRate"  # Not used - car has MAP sensor
        }

    def _data_loop(self):
        """Background loop to poll ESP32 coordinator for data and update last_data."""
        self._ensure_pid_mapping()
        while not self.stop_thread:
            try:
                if self.serial_conn and self.serial_conn.is_open:
                    self.serial_conn.write(b"GET_DATA\n")
                    response_line = self.serial_conn.readline().decode().strip()
                    if response_line:
                        data = json.loads(response_line)
                        with self.data_lock:
                            self.last_data = data
                            self.last_data['timestamp'] = time.time()
                    else:
                        logger.warning("No response from ESP32 coordinator")
                else:
                    logger.warning("Serial connection not open")

            except (serial.SerialException, json.JSONDecodeError) as e:
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
        cmd_key = cmd.name if hasattr(cmd, 'name') else str(cmd)
        if cmd_key not in self.pid_mapping:
            logger.debug(f"PID not supported by wireless adapter: {cmd_key}")
            return None

        field_name = self.pid_mapping[cmd_key]
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
            esp32_config: Dictionary with serial_port, baudrate, timeout
        """
        self.adapter = WirelessOBDAdapter(
            serial_port=esp32_config.get('serial_port', '/dev/ttyAMA0'),
            baudrate=esp32_config.get('baudrate', 115200),
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
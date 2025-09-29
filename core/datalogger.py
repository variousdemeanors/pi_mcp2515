# Avoid importing python-obd at module import time to prevent any auto-scan
# behavior on embedded systems that use a local MCP2515 (socketcan).
# Code paths that need python-obd do lazy imports or check `obd` at runtime.
obd = None
import time
import csv
import threading
from datetime import datetime
import requests
import os
import logging
import re
from logging.handlers import RotatingFileHandler
from .wireless_obd_adapter import create_wireless_obd_connection
from .imperial_units import ImperialConverter, calculate_afr_from_lambda, calculate_afr_from_wideband_o2
from .fuel_calculations import calculate_fuel_metrics

# --- Custom Log Handler for Raw CAN Data ---
class CsvCanLogHandler(logging.FileHandler):
    """
    A custom logging handler that parses raw CAN messages from python-obd's
    debug output and writes them to a structured CSV file.
    """
    def __init__(self, filename, mode='a', encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)
        self.csv_writer = csv.writer(self.stream, delimiter=',')
        # Regex to parse messages like: [obd.obd] [DEBUG] RX: 7E8 03 41 0C 00 00
        self.log_pattern = re.compile(r"\[(RX|TX)\]: (.*)")
        self._write_header()

    def _write_header(self):
        """Writes the header row to the CSV file if it's a new file."""
        if self.stream.tell() == 0:
            self.csv_writer.writerow(['Timestamp', 'Type', 'RawMessage'])
            self.flush()

    def emit(self, record):
        """Overrides the default emit method to parse and write CSV rows."""
        msg = self.format(record)
        match = self.log_pattern.search(msg)
        if match:
            log_type = match.group(1)  # RX or TX
            raw_message = match.group(2).strip()
            # Use the timestamp from the logging record for consistency
            timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            self.csv_writer.writerow([timestamp, log_type, raw_message])
            self.flush()

class MinimalMessage:
    """
    A minimal, mock of the `obd.Message` class that has only the `.data`
    attribute. This is sufficient for the standard `python-obd` decoders,
    which only operate on the data bytes of a message.
    """
    def __init__(self, data_bytes):
        self.data = data_bytes

class DataLogger(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = True
        self.connection = None
        self.log_file = None
        self.csv_writer = None
        self.header_written = False
        self.verbose_logger = None
        self._setup_debugging()

        self.pids_to_query = self._build_pid_list()

        # Data store is now simpler, it will be populated dynamically
        self.data_store = {pid_name: "N/A" for pid_name in self.pids_to_query.keys()}
        self.data_store["Boost_Pressure_PSI"] = "N/A"
        self.data_store["Commanded_AFR"] = "N/A"
        self.data_store["Measured_AFR"] = "N/A"
        self.data_store["log_active"] = False
        self.data_store["connection_status"] = "Connecting..."
        # Flag to allow running without OBD (external sensors only)
        self.allow_no_obd = True
        # Track ESP32 external sensor availability
        self.data_store["esp32_online"] = False
        self.data_store["last_stop_time"] = datetime.now()
        
        # Mock data mode for testing/demo purposes
        self.mock_data_mode = self.config.get('debug', {}).get('mock_data_mode', False)
        self.mock_data_counter = 0
        self.data_store["log_file_name"] = ""
        self.data_store["pid_read_count"] = 0

    # Small local helper to detect python-obd Quantity-like objects without
    # importing python-obd at module import time.
    def _is_quantity(self, x):
        return hasattr(x, 'magnitude') and hasattr(x, 'units')

    def _setup_debugging(self):
        if self.config.get('debugging', {}).get('enabled', False):
            log_dir = self.config['datalogging']['output_path']
            os.makedirs(log_dir, exist_ok=True)

            # --- Verbose Logger Setup ---
            verbose_log_file = os.path.join(log_dir, self.config['debugging']['verbose_log_file'])
            self.verbose_logger = logging.getLogger('VerboseLogger')
            self.verbose_logger.setLevel(logging.DEBUG)
            # Use a rotating file handler to prevent logs from growing indefinitely
            handler = RotatingFileHandler(verbose_log_file, maxBytes=5*1024*1024, backupCount=2)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            # Avoid adding handlers if they already exist from a previous run
            if not self.verbose_logger.handlers:
                self.verbose_logger.addHandler(handler)
            self.verbose_logger.info("--- Verbose Logging Session Started ---")

            # --- Raw CAN Logger Setup ---
            raw_can_log_file = os.path.join(log_dir, self.config['debugging']['raw_can_log_file'])
            can_handler = CsvCanLogHandler(raw_can_log_file)
            can_handler.setLevel(logging.DEBUG)

            # The python-obd logger is just 'obd'
            if obd:
                obd_logger = obd.logger
            else:
                obd_logger = logging.getLogger('obd')
            # Avoid adding duplicate handlers
            if not any(isinstance(h, CsvCanLogHandler) for h in obd_logger.handlers):
                obd_logger.addHandler(can_handler)
            obd_logger.setLevel(logging.DEBUG)
            self.verbose_logger.info(f"Raw CAN data logging enabled. Output: {raw_can_log_file}")

    def _build_pid_list(self):
        # CAN-only mode: treat all selected PIDs as strings (hex codes or names)
        pids = {}
        selected = self.config['pid_management']['selected_pids']
        for pid_name in selected:
            pids[pid_name] = pid_name
        if not pids and self.verbose_logger:
            self.verbose_logger.warning("No PIDs to query. Check config.")
        return pids

    def connect_obd(self):
        try:
            if self.verbose_logger: self.verbose_logger.info("Attempting to establish OBD connection.")
            self.data_store["connection_status"] = "Connecting..."
            conn_config = self.config.get('network', {}).get('obd_connection')
            if not conn_config:
                self.data_store["connection_status"] = "Error: OBD connection not configured."
                print("OBD connection type not configured. Please run 'python3 setup.py' first.")
                if self.verbose_logger: self.verbose_logger.error("OBD connection not configured in config.json.")
                return False

            connection_type = conn_config.get('type')

            if connection_type == 'local_mcp2515':
                self.data_store["connection_status"] = "Using local MCP2515 (hub-managed CAN)"
                if self.verbose_logger: self.verbose_logger.info("Configured for local MCP2515; skipping direct OBD serial connection by default.")
                open_socketcan = self.config.get('datalogger', {}).get('open_socketcan_if_local', False)
                if open_socketcan:
                    try:
                        import can as _can
                        bus = _can.interface.Bus(channel='can0', bustype='socketcan')
                        self.connection = bus
                        self.data_store["connection_status"] = "SocketCAN opened on can0"
                        if self.verbose_logger: self.verbose_logger.info("Opened socketcan can0 for direct OBD queries.")
                        return True
                    except Exception as e:
                        self.data_store["connection_status"] = f"SocketCAN open failed: {e}"
                        if self.verbose_logger: self.verbose_logger.exception("Failed to open socketcan can0")
                        return False
                else:
                    # Always set self.connection to a dummy object for hub-managed CAN
                    self.connection = object()  # Dummy connection to indicate CAN mode
                    return True

            if connection_type == 'wireless_can':
                print("🌐 Attempting to connect via Acebott ESP32 Wireless CAN adapter...")
                if self.verbose_logger: self.verbose_logger.info("Using wireless CAN connection via Acebott ESP32")
                wireless_conn = create_wireless_obd_connection(self.config)
                if wireless_conn and wireless_conn.start():
                    self.connection = wireless_conn
                    self.data_store["connection_status"] = "Successfully connected via Acebott ESP32."
                    print("✅ Successfully connected to vehicle via Acebott ESP32!")
                    if self.verbose_logger: self.verbose_logger.info("Wireless CAN connection established successfully.")
                    return True
                else:
                    self.connection = object()  # Dummy connection to indicate CAN mode
                    self.data_store["connection_status"] = "Wireless CAN connection failed."
                    print("❌ Could not connect to Acebott ESP32. Check WiFi and ESP32 status.")
                    if self.verbose_logger: self.verbose_logger.error("Wireless CAN connection failed.")
                    return False

            # Handle traditional USB/Bluetooth connections
            if not obd:
                self.data_store["connection_status"] = "Error: python-obd not installed; serial adapters disabled."
                if self.verbose_logger: self.verbose_logger.error("python-obd not available; cannot open serial OBD adapter.")
                self.connection = None
                return False

            port = conn_config.get('port')
            baud = conn_config.get('baudrate')
            fast = conn_config.get('fast', False)

            if not baud:
                self.data_store["connection_status"] = "Error: Baud rate not configured in config.json."
                print("CRITICAL: Baud rate not configured. Please run 'python3 setup.py' again.")
                if self.verbose_logger: self.verbose_logger.critical("Baud rate is not configured.")
                return False

            msg1 = f"Attempting to connect via {connection_type} on port '{port or 'auto-scan'}'..."
            msg2 = f"Connection settings: port='{port or 'auto-scan'}', baudrate={baud}, fast={fast}"
            if self.verbose_logger:
                self.verbose_logger.info(msg1)
                self.verbose_logger.info(msg2)
            else:
                if os.isatty(0):
                    print(msg1)
                    print(msg2)

            try:
                import obd as _obd
                if not port:
                    self.connection = _obd.OBD(baudrate=baud, fast=fast)
                else:
                    self.connection = _obd.OBD(port, baudrate=baud, fast=fast)
                if not self.connection.is_connected():
                    self.data_store["connection_status"] = "Connection failed."
                    print("Error: Could not connect to the OBD-II adapter.")
                    if self.verbose_logger: self.verbose_logger.error("self.connection.is_connected() returned False.")
                    return False
                self.data_store["connection_status"] = "Successfully connected."
                print("Successfully connected to the vehicle.")
                if self.verbose_logger: self.verbose_logger.info("Successfully connected to vehicle.")
                return True
            except Exception as e:
                self.data_store["connection_status"] = f"Connection error: {e}"
                print(f"An unexpected error occurred during OBD connection: {e}")
                if self.verbose_logger: self.verbose_logger.exception("An exception occurred during OBD connection.")
                self.connection = None
                return False
        except Exception as e:
            self.data_store["connection_status"] = f"Connection error: {e}"
            print(f"An unexpected error occurred during OBD connection: {e}")
            if self.verbose_logger: self.verbose_logger.exception("An exception occurred during OBD connection.")
            self.connection = None
            return False

    def fetch_external_sensor_data(self):
        if not self.config.get('esp32', {}).get('enabled', False):
            return

        seen_ok = False
        for device in self.config['esp32'].get('devices', []):
            try:
                response = requests.get(device['url'], timeout=0.5)
                if response.status_code == 200:
                    data = response.json()
                    for key, value in data.items():
                        self.data_store[key] = str(value)
                    seen_ok = True
                else:
                    if self.verbose_logger:
                        self.verbose_logger.warning(f"Received status code {response.status_code} from {device.get('name','ESP32')} at {device['url']}")
            except requests.exceptions.RequestException as e:
                if self.verbose_logger:
                    self.verbose_logger.warning(f"Could not fetch data from {device.get('name','ESP32')} at {device['url']}. Error: {e}")

        self.data_store["esp32_online"] = str(seen_ok)

    def start_log(self):
        if self.data_store["log_active"]:
            return
        # Warn if user selected more than 6 PIDs for very short intervals —
        # we will attempt to query multiple 6-PID groups per cycle, but
        # hardware and python-obd limits may cause the cycle to exceed the target interval.
        interval_ms = int(self.config['datalogging'].get('logging_interval_ms', 100))
        num_selected = len(self.pids_to_query)
        if interval_ms <= 100 and num_selected > 6:
            msg = (f"Warning: high-frequency logging requested: interval={interval_ms}ms with "
                   f"{num_selected} selected PIDs. The datalogger will send multiple multi-PID "
                   "requests (groups of up to 6) per cycle. If the ECU or CAN interface cannot keep "
                   "up, increase logging_interval_ms or reduce selected PIDs.")
            print(msg)
            if self.verbose_logger: self.verbose_logger.warning(msg)
        log_path = self.config['datalogging']['output_path']
        os.makedirs(log_path, exist_ok=True)
        filename_format = self.config['datalogging'].get('custom_filename') or self.config['datalogging']['default_filename']
        filename = datetime.now().strftime(filename_format)
        full_path = os.path.join(log_path, filename)
        try:
            self.log_file = open(full_path, mode='w', newline='')
            self.csv_writer = csv.writer(self.log_file)
            self.header_written = False
            self.data_store["log_active"] = "True"
            self.data_store["log_file_name"] = full_path
            if self.verbose_logger: self.verbose_logger.info(f"Datalogger started. Saving to: {full_path}")
        except Exception as e:
            self.data_store["log_active"] = "False"
            print(f"Error starting log: {e}")
            if self.verbose_logger: self.verbose_logger.exception("Failed to start log file.")

    def stop_log(self):
        if not self.data_store["log_active"]:
            return
        if self.log_file:
            self.log_file.close()
        self.data_store["log_active"] = "False"
        self.data_store["last_stop_time"] = str(datetime.now())
        if self.verbose_logger:
            self.verbose_logger.info("Datalogger stopped.")

    def _generate_mock_data(self):
        """Generate realistic mock OBD data for testing/demo purposes."""
        import math
        import random
        
        # Simulate a driving scenario with realistic values
        self.mock_data_counter += 1
        t = self.mock_data_counter * 0.6  # 0.6 seconds per iteration
        
        # Base RPM with some variation (idle to moderate RPM)
        base_rpm = 800 + 1200 * (0.5 + 0.3 * math.sin(t / 10) + 0.2 * random.random())
        
        mock_data = {
            'RPM': base_rpm,
            'ENGINE_LOAD': min(95, 15 + (base_rpm - 800) / 20 + 10 * random.random()),
            'THROTTLE_POS': min(95, max(0, (base_rpm - 800) / 30 + 5 * random.random())),
            'TIMING_ADVANCE': 10 + 15 * random.random(),
            'INTAKE_PRESSURE': max(10, 30 + 20 * random.random()),
            'FUEL_RAIL_PRESSURE': 40 + 5 * random.random(),
            'COOLANT_TEMP': 85 + 10 * random.random(),
            'AMBIANT_AIR_TEMP': 20 + 10 * random.random(),
            'INTAKE_TEMP': 25 + 15 * random.random(),
            'SHORT_FUEL_TRIM_1': -5 + 10 * random.random(),
            'LONG_FUEL_TRIM_1': -3 + 6 * random.random(),
        }
        
        # Add some units as python-obd would, but don't import python-obd at
        # module import time. Use a lazy, guarded import so systems without
        # python-obd (MCP2515-only deployments) still run cleanly.
        try:
            import obd as _obd
            Unit = getattr(_obd, 'Unit', None)
        except Exception:
            Unit = None

        if Unit:
            try:
                mock_data_with_units = {}
                for key, value in mock_data.items():
                    if key == 'RPM':
                        mock_data_with_units[key] = value * Unit.rpm
                    elif key in ['ENGINE_LOAD', 'THROTTLE_POS']:
                        mock_data_with_units[key] = value * Unit.percent
                    elif key == 'TIMING_ADVANCE':
                        mock_data_with_units[key] = value * Unit.degree
                    elif key in ['INTAKE_PRESSURE', 'FUEL_RAIL_PRESSURE']:
                        mock_data_with_units[key] = value * Unit.kilopascal
                    elif key in ['COOLANT_TEMP', 'AMBIANT_AIR_TEMP', 'INTAKE_TEMP']:
                        mock_data_with_units[key] = value * Unit.celsius
                    elif key in ['SHORT_FUEL_TRIM_1', 'LONG_FUEL_TRIM_1']:
                        mock_data_with_units[key] = value * Unit.percent
                    else:
                        mock_data_with_units[key] = value
                return mock_data_with_units
            except Exception:
                # If anything goes wrong with unit wrapping, fall back to raw
                return mock_data
        else:
            return mock_data
    
    @staticmethod
    def chunker(seq, size):
        for pos in range(0, len(seq), size):
            yield seq[pos:pos + size]

    def _parse_multi_pid_response(self, messages, group):
        results = {}
        full_response_hex = "".join([m.hex().decode() for m in messages])

        if self.verbose_logger: self.verbose_logger.debug(f"Parsing multi-PID response: {full_response_hex}")

        if not full_response_hex.startswith("41"):
            return results

        pointer = 2
        group_by_pid = {cmd.pid: cmd for cmd in group}
        
        if self.verbose_logger: self.verbose_logger.debug(f"Parser expecting PIDs with integer keys: {list(group_by_pid.keys())}")

        while pointer < len(full_response_hex):
            if pointer + 2 > len(full_response_hex):
                break

            pid_hex_from_response = full_response_hex[pointer : pointer + 2].upper()
            pid_int_from_response = int(pid_hex_from_response, 16)
            command = group_by_pid.get(pid_int_from_response)
            
            pointer += 2

            if command:
                # command.bytes is the length of the full data payload (Mode + PID + Value)
                # We need to subtract 2 (for Mode and PID) to get the length of the value itself.
                # All Mode 01 PIDs are 1 byte, so this is safe.
                num_value_bytes = command.bytes - 2
                
                if pointer + (num_value_bytes * 2) > len(full_response_hex):
                    if self.verbose_logger: self.verbose_logger.warning(f"Incomplete data for PID {pid_hex_from_response}. Stopping parse.")
                    break
                    
                value_hex = full_response_hex[pointer : pointer + (num_value_bytes * 2)]
                pointer += (num_value_bytes * 2)

                # The standard decoders expect a message object with a .data attribute
                # containing the full response for that PID (Mode + PID + Value)
                mode_bytes = bytearray.fromhex("41")
                pid_bytes = bytearray.fromhex(pid_hex_from_response)
                value_bytes = bytearray.fromhex(value_hex)
                
                # The decoders in python-obd operate on the raw data bytes
                # of a message. The `decode` attribute on a command is a
                # direct reference to the decoder function.
                minimal_message = MinimalMessage(mode_bytes + pid_bytes + value_bytes)
                
                # Call the decoder function with the minimal message
                decoded_value = command.decode([minimal_message])
                results[command.name] = decoded_value
                
                if self.verbose_logger: self.verbose_logger.info(f"Successfully decoded {command.name} as {decoded_value}")
            else:
                if self.verbose_logger: self.verbose_logger.warning(f"Unknown PID '{pid_hex_from_response}' in response. Attempting to skip one byte and continue.")
                # This is a simple recovery strategy. If we see a PID we don't know,
                # we assume it's a 1-byte value and skip it to not derail the whole parse.
                pointer += 2

        return results

    def run(self):
        # Write debug info to a log file for persistent diagnostics
        with open("/tmp/datalogger_debug.log", "a") as f:
            f.write(f"[DEBUG] DataLogger thread started. Connection object: {self.connection}\n")
            conn_status = None
            if self.connection:
                is_conn = getattr(self.connection, 'is_connected', None)
                if callable(is_conn):
                    try:
                        conn_status = is_conn()
                    except Exception:
                        conn_status = "Exception calling is_connected()"
                else:
                    conn_status = "No is_connected() method"
            else:
                conn_status = "No connection object"
            f.write(f"[DEBUG] self.connection.is_connected(): {conn_status}\n")
            f.write(f"[DEBUG] pids_to_query: {self.pids_to_query}\n")
        if self.verbose_logger: self.verbose_logger.info("DataLogger thread started.")
        # Attempt OBD connection; if it fails and allow_no_obd is True,
        # continue running to service external ESP32 sensors and web UI.
        if not self.connect_obd():
            if self.allow_no_obd:
                self.data_store["connection_status"] = "OBD unavailable (external sensors only)"
                if self.verbose_logger: self.verbose_logger.warning("OBD unavailable; continuing in external-sensors-only mode.")
                supported_commands = set()
                commands_to_query = []
            else:
                self.running = False
                if self.verbose_logger: self.verbose_logger.error("Failed to connect to OBD, stopping thread.")
                return

        # CAN-only mode: always use all PIDs from config as strings
        commands_to_query = list(self.pids_to_query.values())

        while self.running:
            # --- OBD-II Data Fetching ---
            interval_ms = int(self.config['datalogging'].get('logging_interval_ms', 100))
            cycle_start = time.time()
            groups = list(self.chunker(commands_to_query, 6))
            self.data_store['pid_groups_per_cycle'] = str(len(groups))
            group_delay_ms = int(self.config['datalogging'].get('inter_group_delay_ms', 0))

            for grp_idx, group in enumerate(groups):
                group_names = [str(cmd) for cmd in group]
                if self.verbose_logger: self.verbose_logger.info(f"Querying PID group ({grp_idx+1}/{len(groups)}): {', '.join(group_names)}")
                pids_hex = "".join([cmd.command.decode()[2:] for cmd in group])
                command_str = f"01{pids_hex}"
                def decoder(messages):
                    return self._parse_multi_pid_response(messages, group)

                # Construct a multi-PID command object. Use python-obd's
                # OBDCommand when available; otherwise create a minimal
                # fallback object so wireless/mocked connections don't crash.
                multi_cmd = None
                try:
                    if obd and hasattr(obd, 'OBDCommand'):
                        multi_cmd = obd.OBDCommand(f"MULTI_GROUP_{pids_hex}",
                                                   "Multi-PID Request",
                                                   command_str.encode(),
                                                   0,
                                                   decoder=decoder)
                    else:
                        class _SimpleCmd:
                            def __init__(self, name, command):
                                self.name = name
                                self.command = command
                        multi_cmd = _SimpleCmd(f"MULTI_GROUP_{pids_hex}", command_str.encode())
                except Exception:
                    multi_cmd = None

                # CAN-only mode: no query, just simulate N/A for all PIDs
                response = None

                self.data_store["pid_read_count"] = str(int(self.data_store.get("pid_read_count", "0")) + len(group))

                # CAN-only mode: set all PIDs in group to N/A
                if self.verbose_logger: self.verbose_logger.warning(f"No CAN response for group: {', '.join(group_names)}")
                for cmd in group:
                    self.data_store[str(cmd)] = "N/A"

                # Optional inter-group delay to avoid bus saturation
                if group_delay_ms > 0 and grp_idx < len(groups) - 1:
                    time.sleep(group_delay_ms / 1000.0)

            cycle_end = time.time()
            cycle_ms = (cycle_end - cycle_start) * 1000.0
            self.data_store['last_cycle_duration_ms'] = str(round(cycle_ms, 2))

            # Warn if cycle took longer than configured interval
            if cycle_ms > interval_ms:
                warn_msg = f"PID cycle took {cycle_ms:.1f}ms which exceeds target interval {interval_ms}ms"
                if self.verbose_logger: self.verbose_logger.warning(warn_msg)
                else: print(warn_msg)
            
            # --- Mock Data Generation (for testing/demo) ---
            if self.mock_data_mode and (not self.connection or not (hasattr(self.connection, "is_connected") and callable(getattr(self.connection, "is_connected", None)) and self.connection.is_connected())):
                mock_data = self._generate_mock_data()
                for pid_name, mock_value in mock_data.items():
                    self.data_store[pid_name] = str(mock_value)
                if self.verbose_logger: 
                    self.verbose_logger.info(f"Generated mock data: RPM={mock_data.get('RPM', 'N/A')}")

            # --- External Sensor Data Fetching ---
            self.fetch_external_sensor_data()

            # --- Data Processing and Logging ---
            intake_pressure = self.data_store.get('INTAKE_PRESSURE')
            baro_pressure = self.data_store.get('BAROMETRIC_PRESSURE')
            # CAN-only: cannot calculate boost, set N/A
            self.data_store["Boost_Pressure_PSI"] = "N/A"

            # --- AFR Calculations ---
            # Calculate commanded AFR from lambda (COMMANDED_EQUIV_RATIO)
            commanded_lambda = self.data_store.get('COMMANDED_EQUIV_RATIO')
            if commanded_lambda:
                commanded_afr = calculate_afr_from_lambda(commanded_lambda)
                self.data_store["Commanded_AFR"] = str(commanded_afr)
            else:
                self.data_store["Commanded_AFR"] = "N/A"

            # Calculate measured AFR from wideband O2 sensor current
            o2_current = self.data_store.get('O2_S1_WR_CURRENT')
            if o2_current:
                measured_afr = calculate_afr_from_wideband_o2(o2_current)
                self.data_store["Measured_AFR"] = str(measured_afr)
            else:
                self.data_store["Measured_AFR"] = "N/A"

            # --- Fuel Delivery Calculations ---
            # Calculate comprehensive fuel metrics (works with MAP sensor)
            # CAN-only: cannot calculate fuel metrics, set N/A
            self.data_store["Fuel_Metrics"] = "N/A"

            if self.data_store["log_active"]:
                try:
                    # Create a copy of the data to avoid modifying the live data_store
                    logged_data = self.data_store.copy()
                    
                    # Apply imperial unit conversions if enabled
                    if self.config['datalogging']['display_units'] == 'imperial':
                        logged_data = ImperialConverter.convert_data_dict(logged_data, force_conversion=True)

                    if not self.header_written:
                        # Build explicit header list (shortened/cleaned)
                        header = [
                            "Timestamp",
                            "RPM",
                            "EngineLoad",
                            "ThrottlePos",
                            "EngineTiming_deg",
                            "Intercooler_Pressure",
                            "Manifold_Pressure_psi",
                            "FuelRailPressure_psi",
                            "CoolantTemp_F",
                            "AmbientAirTemp_F",
                            "IntakeTemp_F",
                            "ShortFuelTrim1",
                            "LongFuelTrim1",
                            "Commanded_AFR",
                            "Measured_AFR",
                        ]

                        # Include any external ESP32 sensor keys (e.g., WmiPressure)
                        # Append them in deterministic order
                        # Identify external sensor keys (not OBD PIDs and not internal fields and not already in header)
                        base_header_keys = [
                            "Timestamp", "RPM", "EngineLoad", "ThrottlePos", "EngineTiming_deg",
                            "Intercooler_Pressure", "Manifold_Pressure_psi", "FuelRailPressure_psi",
                            "CoolantTemp_F", "AmbientAirTemp_F", "IntakeTemp_F", "ShortFuelTrim1",
                            "LongFuelTrim1", "Commanded_AFR", "Measured_AFR"
                        ]
                        
                        esp_keys = [k for k in logged_data.keys() if k not in self.pids_to_query and k not in [
                            'Boost_Pressure_PSI', 'log_active', 'connection_status', 'last_stop_time', 
                            'log_file_name', 'pid_read_count', 'Commanded_AFR', 'Measured_AFR'
                        ] and k not in base_header_keys]

                        # Normalize common WMI pressure keys (handle hyphens, casing)
                        def normalize_esp_key(k):
                            # Normalize common variants from ESP JSON keys to user-friendly CSV headers
                            k_norm = k.replace('-', '_')
                            k_norm_lower = k_norm.lower()
                            # Common WMI patterns: wmi_psi_pre, wmi_psi_post
                            if 'wmi' in k_norm_lower and 'pre' in k_norm_lower:
                                return 'WMI Pre_solenoid'
                            if 'wmi' in k_norm_lower and 'post' in k_norm_lower:
                                return 'WMI post_solenoid'
                            # If sensor explicitly includes 'pre'/'post' and 'solenoid'
                            if 'pre' in k_norm_lower and 'solenoid' in k_norm_lower:
                                return 'WMI Pre_solenoid'
                            if 'post' in k_norm_lower and 'solenoid' in k_norm_lower:
                                return 'WMI post_solenoid'
                            # Fall back to a cleaned version of the key (remove non-alphanum except underscore)
                            cleaned = re.sub(r"[^0-9A-Za-z_]", '', k_norm)
                            return cleaned

                        esp_normalized = []
                        for k in esp_keys:
                            esp_normalized.append((k, normalize_esp_key(k)))
                        for orig, clean in esp_normalized:
                            header.append(clean)

                        if self.csv_writer:
                            self.csv_writer.writerow(header)
                            self.header_written = True

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

                    # Snapshot data_store for a consistent row
                    snapshot = logged_data.copy()

                    # Convert units where necessary and compute derived fields
                    def qty_to_magnitude(q, target_unit=None):
                        try:
                            if target_unit:
                                return q.to(target_unit).magnitude
                            return q.magnitude
                        except Exception:
                            return None

                    # Pressures: convert intake and baro to psi if available
                    intake = snapshot.get('INTAKE_PRESSURE')
                    baro = snapshot.get('BAROMETRIC_PRESSURE')
                    fuel_rail = snapshot.get('FUEL_RAIL_PRESSURE_DIRECT')

                    intake_psi = None
                    baro_psi = None
                    fuel_rail_psi = None

                    # CAN-only: cannot convert units, set all to N/A
                    intake_psi = None
                    baro_psi = None
                    fuel_rail_psi = None

                    # Manifold pressure relative to atmosphere: intake - baro (positive => boost)
                    manifold_psi = None
                    if intake_psi is not None and baro_psi is not None:
                        manifold_psi = intake_psi - baro_psi

                    # Boost_Pressure_PSI in existing code is intake - baro in psi; keep existing value name
                    # Temperatures: convert celsius to fahrenheit
                    def convert_temp_to_f(val):
                        # Use duck-typing to detect quantity-like objects instead
                        # of relying on python-obd's types being present at
                        # import time.
                        if self._is_quantity(val):
                            try:
                                c = val.to('celsius').magnitude
                            except Exception:
                                return None
                        else:
                            try:
                                c = float(val)
                            except Exception:
                                return None
                        return (c * 9.0/5.0) + 32.0

                    coolant_f = convert_temp_to_f(snapshot.get('COOLANT_TEMP'))
                    ambient_f = convert_temp_to_f(snapshot.get('AMBIANT_AIR_TEMP'))
                    intake_temp_f = convert_temp_to_f(snapshot.get('INTAKE_TEMP'))

                    # AFR calculations: use stoich 14.7 and assume lambdas provided directly
                    stoich = 14.7
                    cmd_lambda = snapshot.get('COMMANDED_EQUIV_RATIO')
                    meas_lambda = snapshot.get('O2_S1_WR_CURRENT')

                    def lambda_to_float(l):
                        if self._is_quantity(l):
                            try:
                                return float(l.magnitude)
                            except Exception:
                                return None
                        try:
                            return float(l)
                        except Exception:
                            return None

                    cmd_l_val = lambda_to_float(cmd_lambda)
                    meas_l_val = lambda_to_float(meas_lambda)

                    cmd_afr = (cmd_l_val * stoich) if cmd_l_val is not None else None
                    meas_afr = (meas_l_val * stoich) if meas_l_val is not None else None

                    # Build row following the header order
                    row_data = [timestamp]
                    # RPM
                    rpm = snapshot.get('RPM')
                    row_data.append(str(rpm) if rpm is not None else "N/A")
                    # Engine Load
                    el = snapshot.get('ENGINE_LOAD')
                    row_data.append(str(el) if el is not None else "N/A")
                    # Throttle
                    tp = snapshot.get('THROTTLE_POS')
                    row_data.append(str(tp) if tp is not None else "N/A")
                    # Timing advance
                    ta = snapshot.get('TIMING_ADVANCE')
                    row_data.append(str(ta) if ta is not None else "N/A")
                    # Existing Boost_Pressure_PSI stored in data_store
                    bp = snapshot.get('Boost_Pressure_PSI')
                    row_data.append(str(bp) if bp is not None else "N/A")
                    # Manifold pressure (calculated)
                    row_data.append(f"{manifold_psi:.2f}" if manifold_psi is not None else "N/A")
                    # Fuel rail pressure
                    row_data.append(f"{fuel_rail_psi:.2f}" if fuel_rail_psi is not None else "N/A")
                    # Temps
                    row_data.append(f"{coolant_f:.2f}" if coolant_f is not None else "N/A")
                    row_data.append(f"{ambient_f:.2f}" if ambient_f is not None else "N/A")
                    row_data.append(f"{intake_temp_f:.2f}" if intake_temp_f is not None else "N/A")
                    # Fuel trims
                    sft = snapshot.get('SHORT_FUEL_TRIM_1')
                    lft = snapshot.get('LONG_FUEL_TRIM_1')
                    row_data.append(str(sft) if sft is not None else "N/A")
                    row_data.append(str(lft) if lft is not None else "N/A")
                    # Commanded and Measured AFR (no lambda columns)
                    row_data.append(f"{cmd_afr:.2f}" if cmd_afr is not None else "N/A")
                    row_data.append(f"{meas_afr:.2f}" if meas_afr is not None else "N/A")

                    # Append external ESP32 keys in same order as header (use normalized names)
                    if 'esp_normalized' not in locals():
                        esp_normalized = []
                    for orig, clean in esp_normalized:
                        v = snapshot.get(orig)
                        # If value is a dict (two sensors), try to map known subkeys
                        if isinstance(v, dict):
                            # Look for common keys
                            pre = None
                            post = None
                            for subk, subv in v.items():
                                sk = subk.lower()
                                if 'pre' in sk and 'solenoid' in sk:
                                    pre = subv
                                elif 'post' in sk and 'solenoid' in sk:
                                    post = subv
                            if clean == 'PreSolenoidPsi':
                                row_data.append(str(pre) if pre is not None else 'N/A')
                            elif clean == 'PostSolenoidPsi':
                                row_data.append(str(post) if post is not None else 'N/A')
                            else:
                                # Fallback: stringify the dict
                                row_data.append(str(v))
                        else:
                            row_data.append(str(v))

                    if self.csv_writer:
                        self.csv_writer.writerow(row_data)
                        # Ensure data is flushed to disk to minimize lost rows on crash
                        if self.log_file:
                            try:
                                self.log_file.flush()
                                os.fsync(self.log_file.fileno())
                            except Exception:
                                # Best-effort; do not crash datalogger on fsync failure
                                pass
                except Exception as e:
                    if self.verbose_logger: self.verbose_logger.exception("Error writing to main datalog.")
                    print(f"Error writing to log: {e}")

            time.sleep(self.config['datalogging']['logging_interval_ms'] / 1000.0)

    def stop(self):
        if self.verbose_logger: self.verbose_logger.info("Stop method called. Shutting down...")
        self.running = False
        # CAN-only: no connection close needed
        self.stop_log()
        if self.verbose_logger:
            # Important to avoid issues with duplicate handlers on app restart
            logging.shutdown()

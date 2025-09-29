import time
import threading
import functools
import os
import pandas as pd
import plotly
import plotly.graph_objects as go
import json
from io import StringIO

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
from werkzeug.security import check_password_hash
import logging
import requests

# --- Configure logging to suppress verbose output from Flask/SocketIO ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- Web Server Setup ---
app = Flask(__name__, template_folder='../templates', static_folder='../static')
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*", logger=False, engineio_logger=False)

# These will be passed in from main.py
datalogger_instance = None
app_config = None

# --- Decorator for Login ---
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

def data_emitter_thread():
    """Periodically fetches data from the datalogger's store and emits it."""
    while True:
        if datalogger_instance:
            data_store = datalogger_instance.data_store
            status = data_store.get("connection_status", "Initializing...")

            # Always emit the connection status
            socketio.emit('status_update', {'status': status})

            # Only emit the full data payload if we are actually connected
            if status == "Successfully Connected":
                # Create a JSON-safe payload, converting python-obd Quantity-like objects
                def unwrap_value(x):
                    if hasattr(x, 'magnitude'):
                        try:
                            return x.magnitude
                        except Exception:
                            return x
                    return x
                payload = {k: unwrap_value(v) for k, v in data_store.items()}
                # Force imperial units on this preconfigured branch
                payload['display_units'] = 'imperial'
                # Convert numeric values to imperial representation
                try:
                    payload = ImperialConverter.convert_data_dict(payload)
                except Exception:
                    pass
                socketio.emit('current_data', payload)

        # The datalogger loop is the source of truth for update frequency.
        # This thread just relays the latest data. A 10Hz refresh rate is plenty.
        time.sleep(0.1)

# --- Flask Routes and SocketIO Events ---
@app.route('/')
@login_required
def index():
    """Serves the main dashboard page."""
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Template error: {str(e)}"

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles the login process."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        stored_user = app_config['web_dashboard']['username']
        stored_hash = app_config['web_dashboard']['password_hash']

        if not stored_hash:
            flash('Password not set. Please set it via the CLI.', 'error')
            return redirect(url_for('login'))

        if username == stored_user and check_password_hash(stored_hash, password):
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))

    try:
        return render_template('login.html')
    except Exception as e:
        return f"""
        <html><head><title>Login</title></head><body>
        <h2>Login</h2>
        <form method="post">
            <p>Username: <input type="text" name="username" value="admin"></p>
            <p>Password: <input type="password" name="password"></p>
            <p><input type="submit" value="Login"></p>
        </form>
        <p>Template error: {str(e)}</p>
        </body></html>
        """

@app.route('/logout')
def logout():
    """Logs the user out."""
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/live_data')
def live_data():
    """Enhanced JSON endpoint for external devices with imperial units and AFR data."""
    if datalogger_instance:
        data_store = datalogger_instance.data_store
        
        # Create a JSON-safe payload, converting Pint quantities and applying imperial units
        payload = {}
        for k, v in data_store.items():
            if hasattr(v, 'magnitude'):
                try:
                    payload[k] = v.magnitude
                except Exception:
                    payload[k] = v
            else:
                payload[k] = v
        
        # Apply imperial conversions if configured
        config = getattr(datalogger_instance, 'config', {})
        if config.get('datalogging', {}).get('display_units') == 'imperial':
            payload = ImperialConverter.convert_data_dict(payload)
        
        # Add unit suffixes for clarity
        imperial_payload = {}
        for k, v in payload.items():
            if isinstance(v, (int, float)) and k.lower() != 'rpm':  # Don't add units to RPM
                if 'temp' in k.lower() or 'coolant' in k.lower() or 'ambient' in k.lower() or 'intake' in k.lower():
                    imperial_payload[f"{k}_F"] = v
                elif 'pressure' in k.lower() or 'boost' in k.lower() or 'psi' in k.lower():
                    imperial_payload[f"{k}_PSI"] = v
                elif 'afr' in k.lower():
                    imperial_payload[f"{k}"] = v  # AFR is unitless ratio
                else:
                    imperial_payload[k] = v
            else:
                imperial_payload[k] = v
        
        return json.dumps(imperial_payload)
    else:
        return json.dumps({"error": "Datalogger not running"})


@app.route('/health')
def health_check():
    """Simple health check endpoint for debugging."""
    return jsonify({
        "status": "ok",
        "datalogger_running": datalogger_instance is not None,
        "templates_path": app.template_folder,
        "static_path": app.static_folder
    })

@app.route('/test')
def test_simple():
    """Simple test page without templates."""
    return """
    <html>
    <head><title>Test Page</title></head>
    <body>
        <h1>Flask is Working!</h1>
        <p>If you see this, Flask basic routing works.</p>
        <p><a href="/health">Health Check</a></p>
        <p><a href="/alldata">All Data JSON</a></p>
        <p><a href="/login">Login Page</a></p>
    </body>
    </html>
    """

@app.route('/alldata')
def alldata():
    """A compact consolidated JSON payload for lightweight clients (ESP displays).
    Returns: { boost_psi, wmi_psi_pre, wmi_psi_post, iat_f }
    """
    if not datalogger_instance:
        return jsonify({"error": "Datalogger not running"}), 503

    ds = datalogger_instance.data_store

    def extract_value(key):
        v = ds.get(key)
        # Handle python-obd Quantity-like objects by duck-typing
        try:
            if hasattr(v, 'magnitude'):
                return float(v.magnitude)
        except Exception:
            pass
        # Numeric
        try:
            return float(v)
        except Exception:
            return None

    # Boost / intercooler pressure value (prefer Boost_Pressure_PSI if present)
    boost = extract_value('Boost_Pressure_PSI')
    # Some configurations may expose Intercooler under a different key
    if boost is None:
        boost = extract_value('Intercooler_Pressure')

    # --- WMI sensors: robust extraction for pre/post PSI ---
    def to_float_maybe(v):
        try:
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                # Allow negatives, decimals, and scientific notation
                return float(v.strip())
        except Exception:
            return None
        return None

    def key_normalize(k: str) -> str:
        return k.replace('-', '_').replace(' ', '_').lower()

    def find_in_dict(d: dict, want: str):
        """Find a numeric value in dict matching 'pre' or 'post' variants.
        want: 'pre' | 'post'
        """
        want = want.lower()
        for k, v in d.items():
            kn = key_normalize(str(k))
            # Skip non-scalar values
            if isinstance(v, dict):
                # Try one level nested
                res = find_in_dict(v, want)
                if res is not None:
                    return res
                continue
            # Look for common patterns: 'pre'/'post' + ('psi' or 'solenoid')
            if want in kn and (('psi' in kn) or ('solenoid' in kn)):
                f = to_float_maybe(v)
                if f is not None:
                    return f
            # Direct exacts we see in the wild
            if want == 'pre' and kn in (
                'presolenoidpsi', 'pre_solenoid_psi', 'pre_solenoid', 'prepsi', 'pre', 'wmi_pre'
            ):
                f = to_float_maybe(v)
                if f is not None:
                    return f
            if want == 'post' and kn in (
                'postsolenoidpsi', 'post_solenoid_psi', 'post_solenoid', 'postpsi', 'post', 'wmi_post'
            ):
                f = to_float_maybe(v)
                if f is not None:
                    return f
        return None

    # Start with canonical keys if present
    wmi_pre_val = to_float_maybe(ds.get('wmi_psi_pre'))
    wmi_post_val = to_float_maybe(ds.get('wmi_psi_post'))

    # Try alternate flat key names
    if wmi_pre_val is None:
        wmi_pre_val = find_in_dict(ds, 'pre')
    if wmi_post_val is None:
        wmi_post_val = find_in_dict(ds, 'post')

    # If still missing, check for a WMI grouping dict under common names
    if (wmi_pre_val is None or wmi_post_val is None):
        for group_key in ('WmiPressure', 'wmi', 'WMI', 'wmi_pressure'):
            wp = ds.get(group_key)
            if isinstance(wp, dict):
                if wmi_pre_val is None:
                    wmi_pre_val = find_in_dict(wp, 'pre')
                if wmi_post_val is None:
                    wmi_post_val = find_in_dict(wp, 'post')
                break

    # Intake Air Temp -> iat_f using imperial converter
    iat = ds.get('INTAKE_TEMP')
    iat_f = ImperialConverter.convert_temperature(iat)
    if isinstance(iat_f, str):
        iat_f = None

    # Determine sensor health heuristics
    def is_valid_pressure(v):
        try:
            if v is None: return False
            f = float(v)
            return 0.0 <= f < 500.0
        except Exception:
            return False

    wmi_pre_ok = is_valid_pressure(wmi_pre_val)
    wmi_post_ok = is_valid_pressure(wmi_post_val)

    # Extract AFR values
    commanded_afr = ds.get('Commanded_AFR', 'N/A')
    measured_afr = ds.get('Measured_AFR', 'N/A')
    
    # Extract fuel delivery metrics
    fuel_flow_gph = ds.get('Fuel_fuel_flow_gph', 'N/A')
    injector_duty = ds.get('Fuel_injector_duty_cycle', 'N/A')
    fuel_economy = ds.get('Fuel_fuel_economy_mpg', 'N/A')
    airflow_method = ds.get('Fuel_airflow_method', 'MAP')

    payload = {
        'boost_psi': boost if boost is not None else 'N/A',
        'wmi_psi_pre': wmi_pre_val if wmi_pre_val is not None else 'N/A',
        'wmi_psi_post': wmi_post_val if wmi_post_val is not None else 'N/A',
        'iat_f': round(iat_f, 2) if iat_f is not None else 'N/A',
        'commanded_afr': commanded_afr,
        'measured_afr': measured_afr,
        'fuel_flow_gph': fuel_flow_gph,
        'injector_duty_cycle': injector_duty,
        'fuel_economy_mpg': fuel_economy,
        'airflow_method': airflow_method,
        'esp32_online': bool(datalogger_instance.data_store.get('esp32_online', False)),
        'wmi_pre_ok': wmi_pre_ok,
        'wmi_post_ok': wmi_post_ok
    }

    return jsonify(payload)

@app.route('/debug/ds')
@login_required
def debug_data_store():
    """Expose current data_store keys and simple values for debugging (login required)."""
    if not datalogger_instance:
        return jsonify({'error': 'datalogger not running'}), 503
    ds = datalogger_instance.data_store
    out = {}
    for k, v in ds.items():
        try:
            if hasattr(v, 'magnitude'):
                out[k] = {'type': 'quantity', 'value': getattr(v, 'magnitude', None), 'units': str(getattr(v, 'units', ''))}
            elif isinstance(v, (int, float, str)):
                out[k] = v
            elif isinstance(v, dict):
                # Shallow convert nested dict
                sub = {}
                for sk, sv in v.items():
                    if isinstance(sv, (int, float, str)):
                        sub[sk] = sv
                out[k] = sub
            else:
                out[k] = str(v)
        except Exception:
            out[k] = '<unrepr>'
    return jsonify(out)

from . import config as config_manager
from . import sensor_discovery
from .imperial_units import ImperialConverter
import subprocess
import psutil
import socket
import threading
import time

@app.route('/esp32_management')
@login_required
def esp32_management():
    """ESP32 sensor management page."""
    return render_template('esp32_management.html')


@app.route('/espnow_status')
@login_required
def espnow_status():
    """ESP-NOW network status page."""
    return render_template('espnow_status.html')


# Background thread to emit ESP-NOW hub status periodically
def espnow_status_emitter():
    while True:
        try:
            # Default values
            status = {'coordinator_mac': None, 'peers': []}
            # Try to query hub process via shared status file or API. Fallback to config.
            try:
                cfg = app_config or config_manager.load_config()
                # coordinator mac may be stored in config under espnow.coordinator_mac
                status['coordinator_mac'] = cfg.get('espnow', {}).get('coordinator_mac') if cfg else None
            except Exception:
                pass

            # If a pi_espnow_hub module exposes live peers, try to import it (best effort)
            try:
                import pi_espnow_hub as local_hub
                peers = getattr(local_hub, 'PEER_STATUS', None)
                if peers:
                    status['peers'] = peers
            except Exception:
                # Not available or not running; keep empty list
                status['peers'] = []

            # Normalize peers for UI
            normalized = []
            for p in status['peers']:
                normalized.append({
                    'mac': p.get('mac') if isinstance(p, dict) else str(p),
                    'last_seen': p.get('last_seen', 'N/A') if isinstance(p, dict) else 'N/A',
                    'rssi': p.get('rssi', 'N/A') if isinstance(p, dict) else 'N/A',
                    'status': p.get('status', 'unknown') if isinstance(p, dict) else 'unknown'
                })

            socketio.emit('espnow_status', {'coordinator_mac': status.get('coordinator_mac'), 'peers': normalized})
        except Exception:
            pass
        time.sleep(2.0)

# Start the emitter thread when the app is ready
@socketio.on('connect')
def _on_connect():
    global app_config
    if app_config is None:
        app_config = config_manager.load_config()



@app.route('/network/ap', methods=['POST'])
@login_required
def api_network_ap():
    """Enable AP mode with given SSID/password via NetworkManager."""
    ssid = request.form.get('ssid', 'datalogger')
    password = request.form.get('password', 'datalogger')
    # Prefer calling privileged helper via sudo to avoid running webapp as root
    helper = '/opt/obd2/venv/bin/python /opt/obd2/obd2-repo/scripts/network_helper.py'
    import shlex, subprocess
    cmd = f"sudo {helper} ap {shlex.quote(ssid)} {shlex.quote(password)}"
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        try:
            data = json.loads(res.stdout.strip()) if res.stdout.strip() else {'ok': False, 'error': res.stderr}
        except Exception:
            data = {'ok': False, 'error': res.stdout or res.stderr}
        status_code = 200 if data.get('ok') else 500
        return jsonify(data), status_code
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/network/client', methods=['POST'])
@login_required
def api_network_client():
    """Configure client mode (connect to existing WiFi) via NetworkManager."""
    ssid = request.form.get('ssid')
    password = request.form.get('password')
    if not ssid or not password:
        return jsonify({'ok': False, 'error': 'ssid and password required'}), 400
    helper = '/opt/obd2/venv/bin/python /opt/obd2/obd2-repo/scripts/network_helper.py'
    import shlex, subprocess
    cmd = f"sudo {helper} client {shlex.quote(ssid)} {shlex.quote(password)}"
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        try:
            data = json.loads(res.stdout.strip()) if res.stdout.strip() else {'ok': False, 'error': res.stderr}
        except Exception:
            data = {'ok': False, 'error': res.stdout or res.stderr}
        status_code = 200 if data.get('ok') else 500
        return jsonify(data), status_code
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# --- ESP32 Management API Routes ---
@app.route('/api/esp32/scan', methods=['POST'])
@login_required
def api_esp32_scan():
    """Scan network for ESP32 devices."""
    try:
        found_ips = sensor_discovery.scan_for_sensors()
        devices = []
        
        for ip in found_ips:
            try:
                url = f"http://{ip}/data"
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    sample_data = response.json()
                    
                    # Try to determine device type from data
                    device_type = "unknown"
                    suggested_name = f"ESP32_{ip.split('.')[-1]}"
                    suggested_pid = ip.replace('.', '_')
                    
                    # Analyze sample data to suggest better names
                    if isinstance(sample_data, dict):
                        keys = list(sample_data.keys())
                        if any('pressure' in k.lower() or 'psi' in k.lower() for k in keys):
                            device_type = "pressure"
                            if 'wmi' in str(sample_data).lower():
                                suggested_name = f"WMI_Pressure_{ip.split('.')[-1]}"
                            elif 'boost' in str(sample_data).lower():
                                suggested_name = f"Boost_Sensor_{ip.split('.')[-1]}"
                        elif any('temp' in k.lower() for k in keys):
                            device_type = "temperature"
                            suggested_name = f"Temp_Sensor_{ip.split('.')[-1]}"
                    
                    devices.append({
                        'ip': ip,
                        'url': url,
                        'type': device_type,
                        'sample': sample_data,
                        'suggested_name': suggested_name,
                        'suggested_pid': suggested_pid
                    })
            except Exception as e:
                # Device responded to scan but data fetch failed
                devices.append({
                    'ip': ip,
                    'url': f"http://{ip}/data",
                    'type': 'unknown',
                    'sample': {'error': str(e)},
                    'suggested_name': f"ESP32_{ip.split('.')[-1]}",
                    'suggested_pid': ip.replace('.', '_')
                })
        
        return jsonify({'success': True, 'devices': devices})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/esp32/configured', methods=['GET'])
@login_required
def api_esp32_configured():
    """Get list of configured ESP32 sensors."""
    try:
        sensors = app_config.get('esp32', {}).get('devices', [])
        return jsonify({'success': True, 'sensors': sensors})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/esp32/add', methods=['POST'])
@login_required
def api_esp32_add():
    """Add or update ESP32 sensor configuration."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        url = data.get('url', '').strip()
        # Normalize URL: add scheme if missing, default /data path if only host provided
        if url and not url.lower().startswith(('http://', 'https://')):
            # If the string has a slash path already, just prepend http://
            if '/' in url:
                url = f"http://{url}"
            else:
                url = f"http://{url}/data"
        
        if not name or not url:
            return jsonify({'success': False, 'error': 'Name and URL required'})
        
        # Ensure esp32 section exists
        if 'esp32' not in app_config:
            app_config['esp32'] = {'enabled': True, 'devices': []}
        if 'devices' not in app_config['esp32']:
            app_config['esp32']['devices'] = []
        
        # Create sensor config
        sensor_config = {
            'name': name,
            'url': url
        }
        
        # Add optional fields
        if data.get('pid_name'):
            sensor_config['pid_name'] = data['pid_name']
        if data.get('data_type'):
            sensor_config['data_type'] = data['data_type']
        
        # Check if updating existing (by URL)
        existing_index = None
        for i, sensor in enumerate(app_config['esp32']['devices']):
            if sensor.get('url') == url:
                existing_index = i
                break
        
        if existing_index is not None:
            app_config['esp32']['devices'][existing_index] = sensor_config
        else:
            app_config['esp32']['devices'].append(sensor_config)
        
        # Save config
        config_manager.save_config(app_config)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/esp32/remove', methods=['POST'])
@login_required
def api_esp32_remove():
    """Remove ESP32 sensor configuration."""
    try:
        data = request.get_json()
        index = data.get('index')
        
        if index is None or index < 0:
            return jsonify({'success': False, 'error': 'Invalid index'})
        
        devices = app_config.get('esp32', {}).get('devices', [])
        if index >= len(devices):
            return jsonify({'success': False, 'error': 'Index out of range'})
        
        # Remove device
        devices.pop(index)
        config_manager.save_config(app_config)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/esp32/test', methods=['POST'])
@login_required
def api_esp32_test():
    """Test ESP32 sensor connectivity."""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        # Normalize URL: ensure scheme and reasonable default path
        if url and not url.lower().startswith(('http://', 'https://')):
            if '/' in url:
                url = f"http://{url}"
            else:
                url = f"http://{url}/data"
        
        if not url:
            return jsonify({'success': False, 'error': 'URL required'})

        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'response': response.json(),
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds()
            })
        else:
            return jsonify({
                'success': False,
                'error': f'HTTP {response.status_code}',
                'response': response.text[:200]
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- Network Management API Routes ---
@app.route('/api/network/status', methods=['GET'])
@login_required
def api_network_status():
    """Get network status and connected clients."""
    try:
        network_config = app_config.get('network', {})
        
        # Get basic network info
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Try to get more detailed info if on Linux
        try:
            # Get WiFi info using iwconfig/ip commands
            mode = network_config.get('mode', 'Unknown')
            ssid = network_config.get('ap_ssid') if mode == 'AP' else network_config.get('client_ssid', 'Unknown')
            
            # Get actually responding devices instead of phantom ARP entries
            connected_clients = []
            
            try:
                # Use network scanner to find real, responding devices
                from .network_scanner import NetworkScanner
                scanner = NetworkScanner(timeout=2)
                
                # Check common device IPs (Pi AP subnet)
                test_ips = [f"192.168.4.{i}" for i in range(100, 110)]  # Focus on device range
                devices = scanner.scan_specific_ips(test_ips)
                
                for device in devices:
                    # Check if this device is providing sensor data
                    providing_data = False
                    device_type = device.get('device_type', 'Unknown')
                    
                    for configured_device in app_config.get('esp32', {}).get('devices', []):
                        if device['ip'] in configured_device.get('url', ''):
                            providing_data = True
                            break
                    
                    connected_clients.append({
                        'ip': device['ip'],
                        'mac': 'Unknown',  # HTTP scan doesn't provide MAC
                        'providing_data': providing_data,
                        'device_type': device_type,
                        'last_data': None,
                        'status': 'Active'
                    })
                    
                print(f"📊 Network Status: Found {len(connected_clients)} active devices")
                
            except Exception as e:
                print(f"⚠️  Network scan failed: {e}")
                # Only add known ESP32 static IP as fallback
                connected_clients = [{
                    'ip': '192.168.4.100', 
                    'mac': 'Unknown', 
                    'providing_data': False, 
                    'device_type': 'ESP32 CAN (Static IP)', 
                    'last_data': None,
                    'status': 'Unknown'
                }]
            
            return jsonify({
                'success': True,
                'mode': mode,
                'ssid': ssid,
                'ip': local_ip,
                'hostname': hostname,
                'clients': connected_clients
            })
        except Exception as e:
            return jsonify({
                'success': True,
                'mode': 'Unknown',
                'ssid': 'Unknown',
                'ip': local_ip,
                'hostname': hostname,
                'clients': [],
                'error': str(e)
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/network/reboot', methods=['POST'])
@login_required
def api_network_reboot():
    """Restart network services (requires sudo access)."""
    try:
        # Try to restart network services
        # Note: This requires the pi user to have sudo access for networking commands
        commands = [
            ['sudo', 'systemctl', 'restart', 'hostapd'],
            ['sudo', 'systemctl', 'restart', 'dnsmasq'],
            ['sudo', 'systemctl', 'restart', 'dhcpcd']
        ]
        
        for cmd in commands:
            try:
                subprocess.run(cmd, check=True, timeout=10)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass  # Continue with other commands even if one fails
        
        return jsonify({'success': True, 'message': 'Network restart initiated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- Configuration Pages ---
@app.route('/config/network', methods=['GET', 'POST'])
@login_required
def config_network():
    # ... (implementation from before)
    return render_template('config_network.html', network_config=app_config['network'])

@app.route('/config/datalogging', methods=['GET', 'POST'])
@login_required
def config_datalogging():
    # ... (implementation from before)
    return render_template('config_datalogging.html', datalogging_config=app_config['datalogging'])

@app.route('/config/pids', methods=['GET', 'POST'])
@login_required
def config_pids():
    # ... (implementation from before)
    return render_template('config_pids.html', pid_config=app_config['pid_management'])

@app.route('/config/fuel', methods=['GET', 'POST'])
@login_required
def config_fuel():
    """Fuel calculations configuration page."""
    from core.config import save_config
    
    if request.method == 'POST':
        try:
            # Update fuel configuration
            app_config['fuel']['injector_flow_rate'] = float(request.form.get('injector_flow_rate', 36.0))
            app_config['fuel']['num_cylinders'] = int(request.form.get('num_cylinders', 4))
            app_config['fuel']['engine_displacement'] = float(request.form.get('engine_displacement', 2.0))
            app_config['fuel']['stoichiometric_afr'] = float(request.form.get('stoichiometric_afr', 14.7))
            app_config['fuel']['fuel_density'] = float(request.form.get('fuel_density', 6.17))
            
            # Save configuration
            save_config(app_config)
            flash('Fuel configuration updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating fuel configuration: {str(e)}', 'danger')
        
        return redirect(url_for('config_fuel'))
    
    # Ensure fuel config exists
    if 'fuel' not in app_config:
        app_config['fuel'] = {
            'injector_flow_rate': 36.0,
            'num_cylinders': 4,
            'engine_displacement': 2.0,
            'stoichiometric_afr': 14.7,
            'fuel_density': 6.17
        }
    
    return render_template('config_fuel.html', fuel_config=app_config['fuel'])

@app.route('/config/obd', methods=['GET', 'POST'])
@login_required
def config_obd():
    """OBD connection configuration page."""
    from core.config import save_config
    
    if request.method == 'POST':
        try:
            # Update OBD connection configuration
            connection_type = request.form.get('type', 'usb')
            
            app_config['network']['obd_connection']['type'] = connection_type
            
            if connection_type == 'usb':
                app_config['network']['obd_connection']['port'] = request.form.get('port') or None
                app_config['network']['obd_connection']['baudrate'] = int(request.form.get('baudrate', 115200))
                app_config['network']['obd_connection']['fast'] = bool(request.form.get('fast'))
            elif connection_type == 'wireless_can':
                app_config['network']['obd_connection']['wireless_can']['esp32_ip'] = request.form.get('esp32_ip', '192.168.4.2')
                app_config['network']['obd_connection']['wireless_can']['esp32_port'] = int(request.form.get('esp32_port', 5000))
                app_config['network']['obd_connection']['wireless_can']['endpoint'] = request.form.get('endpoint', '/obd_data')
                app_config['network']['obd_connection']['wireless_can']['timeout'] = int(request.form.get('timeout', 5))
            
            # Save configuration
            save_config(app_config)
            flash('OBD connection configuration updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating OBD configuration: {str(e)}', 'danger')
        
        return redirect(url_for('config_obd'))
    
    # Ensure OBD config exists
    if 'obd_connection' not in app_config.get('network', {}):
        if 'network' not in app_config:
            app_config['network'] = {}
        app_config['network']['obd_connection'] = {
            'type': 'usb',
            'port': None,
            'baudrate': 115200,
            'fast': True,
            'wireless_can': {
                'esp32_ip': '192.168.4.100',
                'esp32_port': 5000,
                'endpoint': '/obd_data',
                'timeout': 5
            }
        }
    
    return render_template('config_obd.html', obd_config=app_config['network']['obd_connection'])

# --- OBD Connection API Routes ---
@app.route('/api/scan_can_devices', methods=['POST'])
@login_required
def api_scan_can_devices():
    """Scan network for CAN/OBD devices."""
    try:
        from core.network_scanner import NetworkScanner
        
        scanner = NetworkScanner(timeout=3)
        devices = scanner.scan_network(max_workers=8)
        
        # Filter for likely CAN/OBD devices
        can_devices = []
        for device in devices:
            if device.get('device_type') == 'CAN/OBD Transceiver' or 'obd' in device.get('endpoint', '').lower():
                can_devices.append(device)
        
        return jsonify({'success': True, 'devices': can_devices})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test_can_connection', methods=['POST'])
@login_required
def api_test_can_connection():
    """Test connection to a CAN/OBD device."""
    try:
        data = request.get_json()
        ip = data.get('ip')
        port = data.get('port', 5000)
        endpoint = data.get('endpoint', '/obd_data')
        
        if not ip:
            return jsonify({'success': False, 'error': 'IP address required'})
        
        import requests
        url = f"http://{ip}:{port}{endpoint}"
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        sample_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        
        return jsonify({
            'success': True, 
            'sample_data': sample_data,
            'status_code': response.status_code
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- CAN Diagnostics Routes ---
@app.route('/can_diagnostics')
@login_required
def can_diagnostics():
    """CAN diagnostics and configuration page."""
    return render_template('can_diagnostics.html')

@app.route('/api/can/status', methods=['GET'])
@login_required
def api_can_status():
    """Get real-time CAN connection status and statistics."""
    try:
        if not datalogger_instance:
            return jsonify({'success': False, 'error': 'Datalogger not running'})
        
        # Import diagnostics module
        from . import can_diagnostics
        
        # Get wireless adapter instance
        wireless_adapter = getattr(datalogger_instance, 'wireless_adapter', None)
        
        if wireless_adapter:
            stats = can_diagnostics.get_connection_stats(wireless_adapter)
            status = can_diagnostics.get_connection_status(wireless_adapter)
            return jsonify({
                'success': True,
                'status': status,
                'stats': stats,
                'timestamp': time.time()
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Wireless adapter not available'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/can/benchmark', methods=['POST'])
@login_required
def api_can_benchmark():
    """Start CAN performance benchmark."""
    try:
        if not datalogger_instance:
            return jsonify({'success': False, 'error': 'Datalogger not running'})
        
        from . import can_diagnostics
        
        data = request.get_json()
        duration = data.get('duration', 30)  # Default 30 seconds
        
        wireless_adapter = getattr(datalogger_instance, 'wireless_adapter', None)
        
        if wireless_adapter:
            # Start benchmark in background
            benchmark_results = can_diagnostics.run_benchmark(wireless_adapter, duration)
            return jsonify({
                'success': True,
                'results': benchmark_results
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Wireless adapter not available'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/can/config', methods=['GET', 'POST'])
@login_required
def api_can_config():
    """Get or update CAN configuration."""
    try:
        if request.method == 'GET':
            # Return current CAN configuration
            can_config = app_config.get('can', {})
            return jsonify({'success': True, 'config': can_config})
        
        elif request.method == 'POST':
            # Update CAN configuration
            data = request.get_json()
            
            if 'can' not in app_config:
                app_config['can'] = {}
            
            # Update configuration fields
            if 'baud_rate' in data:
                app_config['can']['baud_rate'] = data['baud_rate']
            if 'polling_interval' in data:
                app_config['can']['polling_interval'] = data['polling_interval']
            if 'retry_attempts' in data:
                app_config['can']['retry_attempts'] = data['retry_attempts']
            if 'timeout' in data:
                app_config['can']['timeout'] = data['timeout']
            
            # Save configuration
            config_manager.save_config(app_config)
            
            # Apply configuration to wireless adapter if running
            if datalogger_instance:
                wireless_adapter = getattr(datalogger_instance, 'wireless_adapter', None)
                if wireless_adapter and hasattr(wireless_adapter, 'update_config'):
                    wireless_adapter.update_config(app_config['can'])
            
            return jsonify({'success': True, 'message': 'Configuration updated'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/can/recommendations', methods=['GET'])
@login_required
def api_can_recommendations():
    """Get performance recommendations."""
    try:
        if not datalogger_instance:
            return jsonify({'success': False, 'error': 'Datalogger not running'})
        
        from . import can_diagnostics
        
        wireless_adapter = getattr(datalogger_instance, 'wireless_adapter', None)
        
        if wireless_adapter:
            recommendations = can_diagnostics.get_recommendations(wireless_adapter)
            return jsonify({
                'success': True,
                'recommendations': recommendations
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Wireless adapter not available'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- Analysis Page ---
@app.route('/analysis')
@login_required
def analysis():
    log_dir = app_config['datalogging']['output_path']
    log_files = []
    if os.path.exists(log_dir):
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.csv')]
    return render_template('analysis.html', log_files=log_files)

@app.route('/download_log/<path:filename>')
@login_required
def download_log(filename):
    """Provides a route to download a specific log file."""
    log_dir = os.path.abspath(os.path.expanduser(app_config['datalogging']['output_path']))
    return send_from_directory(log_dir, filename, as_attachment=True)

@socketio.on('load_log_file')
def handle_load_log_file(data):
    if not session.get('logged_in'): return
    try:
        if 'content' in data: # File was uploaded
            df = pd.read_csv(StringIO(data['content']))
        else: # File selected from server
            log_path = os.path.join(app_config['datalogging']['output_path'], data['filename'])
            df = pd.read_csv(log_path)

        # Clean up column names (remove spaces, etc.)
        df.columns = df.columns.str.strip()
        pids = [col for col in df.columns if col.lower() != 'timestamp']
        emit('log_file_loaded', {'pids': pids})
    except Exception as e:
        emit('log_file_loaded', {'error': str(e)})

@socketio.on('get_plot_data')
def handle_get_plot_data(data):
    if not session.get('logged_in'): return
    try:
        filename = data['filename']
        pids_to_plot = data['pids']

        # This assumes the file is on the server for simplicity
        log_path = os.path.join(app_config['datalogging']['output_path'], filename)
        
        # Read CSV with error handling
        try:
            # Read with engine='python' to handle malformed files better
            df = pd.read_csv(log_path, low_memory=False, engine='python')
            
            # Handle duplicate column names by renaming them
            cols = pd.Series(df.columns)
            for dup in cols[cols.duplicated()].unique():
                cols[cols[cols == dup].index.values.tolist()] = [dup + '_' + str(i) if i != 0 else dup for i in range(sum(cols == dup))]
            df.columns = cols
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            print(f"CSV loaded with {len(df)} rows and {len(df.columns)} columns")
            print(f"Available columns: {list(df.columns[:15])}...")  # Debug info
            
        except Exception as e:
            print(f"Error reading CSV: {e}")
            emit('plot_data_ready', {'error': f'Failed to read CSV file: {str(e)}'})
            return

        # Ensure timestamp is datetime object for plotting
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        else:
            # Fallback: create a sequential index as timestamp
            df['Timestamp'] = pd.date_range(start='2024-01-01', periods=len(df), freq='S')

        fig = go.Figure()
        
        # Process each PID with better data cleaning
        plot_traces_created = 0
        na_values_count = 0
        total_data_points = 0
        
        for pid in pids_to_plot:
            # Handle potential column name variations (including duplicates)
            actual_column = None
            possible_names = [pid, f"{pid}_1", f"{pid}_2"]
            
            for name in possible_names:
                if name in df.columns:
                    actual_column = name
                    break
            
            if actual_column is None:
                print(f"Warning: PID '{pid}' not found. Available columns: {list(df.columns)}")
                continue
                
            print(f"Processing PID '{pid}' using column '{actual_column}'")
                
            # Clean data - handle various formats and convert to numeric
            series = df[actual_column].copy()
            total_data_points += len(series)
            
            # Count N/A values before processing
            na_count = series.isin(['N/A', 'n/a', 'NA', 'null', 'NULL', '', 'None']).sum()
            na_values_count += na_count
            
            # Handle 'N/A' and other string values
            series = series.replace(['N/A', 'n/a', 'NA', 'null', 'NULL', '', 'None'], pd.NA)
            
            # Convert to numeric, coercing errors to NaN
            numeric_series = pd.to_numeric(series, errors='coerce')
            
            # Remove NaN values for plotting
            valid_mask = numeric_series.notna()
            valid_data = df.loc[valid_mask]
            valid_series = numeric_series.loc[valid_mask]
            
            print(f"  PID '{pid}': {len(valid_series)} valid points out of {len(series)} total")
            
            if len(valid_series) > 0:
                # Check if all values are the same (which would create a flat line)
                unique_values = valid_series.nunique()
                value_range = valid_series.max() - valid_series.min() if len(valid_series) > 1 else 0
                
                print(f"  PID '{pid}': {unique_values} unique values, range: {value_range}")
                
                if unique_values > 1 and value_range > 0.001:  # More than one unique value with meaningful range
                    fig.add_trace(go.Scatter(
                        x=valid_data['Timestamp'], 
                        y=valid_series, 
                        mode='lines+markers', 
                        name=f"{pid}",
                        connectgaps=False,
                        hovertemplate=f'{pid}: %{{y}}<br>Time: %{{x}}<extra></extra>'
                    ))
                    plot_traces_created += 1
                else:
                    print(f"  Warning: PID '{pid}' has flat data (value: {valid_series.iloc[0] if len(valid_series) > 0 else 'N/A'})")
            else:
                print(f"  Warning: No valid numeric data found for PID '{pid}'")

        # Check if all data was N/A and provide helpful message
        if plot_traces_created == 0:
            if total_data_points > 0 and na_values_count > total_data_points * 0.9:
                # More than 90% of values are N/A
                error_msg = "Most data values are 'N/A' which indicates no OBD connection was available during logging. "
                error_msg += "To generate demo data for testing, enable 'mock_data_mode' in the debug section of config.json."
            else:
                error_msg = "No valid numeric data found for the selected PIDs. "
                error_msg += "This could be due to non-numeric columns or data formatting issues."
            emit('plot_data_ready', {'error': error_msg})
            return

        fig.update_layout(
            title=f'Datalog Analysis - {filename}',
            xaxis_title='Timestamp',
            yaxis_title='Value',
            template='plotly_dark',
            hovermode='x unified'
        )

        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        # Calculate stats only for numeric columns
        numeric_pids = []
        for pid in pids_to_plot:
            if pid in df.columns:
                series = pd.to_numeric(df[pid].replace(['N/A', 'n/a', 'NA', 'null', 'NULL', ''], pd.NA), errors='coerce')
                if series.notna().sum() > 0:  # Has some valid numeric data
                    numeric_pids.append(pid)
        
        if numeric_pids:
            # Create a clean dataframe for stats
            stats_df = df[numeric_pids].copy()
            for col in numeric_pids:
                stats_df[col] = pd.to_numeric(stats_df[col].replace(['N/A', 'n/a', 'NA', 'null', 'NULL', ''], pd.NA), errors='coerce')
            
            stats = stats_df.describe().transpose().reset_index()
            stats.columns = ['PID', 'Count', 'Mean', 'Std Dev', 'Min', '25%', '50%', '75%', 'Max']
            
            stats_data = {
                'headers': stats.columns.tolist(),
                'rows': stats.round(3).values.tolist()
            }
        else:
            stats_data = {
                'headers': ['Error'],
                'rows': [['No valid numeric data found for selected PIDs']]
            }

        emit('plot_data_ready', {'plot_data': json.loads(graph_json), 'stats': stats_data})

    except Exception as e:
        print(f"Error in get_plot_data: {e}")
        emit('plot_data_ready', {'error': str(e)})


@socketio.on('start_log')
def handle_start_log():
    if not session.get('logged_in'): return
    if datalogger_instance:
        try:
            datalogger_instance.start_log()
            log_status = datalogger_instance.data_store.get('log_active', False)
            log_file = datalogger_instance.data_store.get('log_file_name', 'Unknown')
            
            print(f"Log recording started via web UI. Active: {log_status}, File: {log_file}")
            
            # Emit a status update to potentially show the new log file name or status
            emit('status_update', {
                'status': f"Logging {'started' if log_status else 'failed to start'}",
                'log_status': log_status,
                'log_file': log_file,
                'message': f"Logging {'started' if log_status else 'failed'}: {log_file}"
            }, broadcast=True)
        except Exception as e:
            print(f"Error starting log: {e}")
            emit('status_update', {
                'status': 'Logging failed to start',
                'log_status': False,
                'error': str(e)
            }, broadcast=True)
    else:
        print("Error: No datalogger instance available")
        emit('status_update', {
            'status': 'Error: Datalogger not available',
            'log_status': False,
            'error': 'Datalogger instance not initialized'
        }, broadcast=True)

@socketio.on('stop_log')
def handle_stop_log():
    if not session.get('logged_in'): return
    if datalogger_instance:
        try:
            datalogger_instance.stop_log()
            log_status = datalogger_instance.data_store.get('log_active', False)
            
            print(f"Log recording stopped via web UI. Active: {log_status}")
            
            emit('status_update', {
                'status': 'Logging stopped',
                'log_status': log_status,
                'message': "Logging stopped successfully."
            }, broadcast=True)
        except Exception as e:
            print(f"Error stopping log: {e}")
            emit('status_update', {
                'status': 'Error stopping log',
                'log_status': datalogger_instance.data_store.get('log_active', False),
                'error': str(e)
            }, broadcast=True)
    else:
        print("Error: No datalogger instance available")
        emit('status_update', {
            'status': 'Error: Datalogger not available',
            'error': 'Datalogger instance not initialized'
        }, broadcast=True)




# ... (rest of the socketio event handlers) ...

def start_webapp(config, datalogger):
    """Starts the web application."""
    print("[DEBUG] Entered start_webapp function.")
    global datalogger_instance, app_config
    datalogger_instance = datalogger
    app_config = config

    app.config['SECRET_KEY'] = app_config['web_dashboard']['secret_key']

    # Start background task for data emission
    socketio.start_background_task(target=data_emitter_thread)
    
    # Use threading mode with debug disabled for better compatibility
    print(f"[DEBUG] Starting Flask-SocketIO server on 0.0.0.0:{app_config['web_dashboard']['port']}")
    # Note: Werkzeug is a development server and will raise a RuntimeError
    # when used in 'production' contexts. For local embedded devices (Raspberry
    # Pi running the dashboard as a systemd service) we accept the risk and
    # allow Werkzeug to run by passing allow_unsafe_werkzeug=True so systemd
    # doesn't crash the service immediately. If you deploy externally, replace
    # this with a production WSGI server (gunicorn/eventlet) instead.
    socketio.run(app, 
                 host='0.0.0.0', 
                 port=app_config['web_dashboard']['port'],
                 debug=False,
                 use_reloader=False,
                 allow_unsafe_werkzeug=True)

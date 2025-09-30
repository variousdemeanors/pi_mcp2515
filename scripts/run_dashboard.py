#!/usr/bin/env python3
"""
Run the full dashboard + datalogger from the installed venv path.
This script is intended to be executed by systemd using the venv python.
"""
import os
import sys

# Activate virtual environment
venv_path = '/opt/obd2/venv'
if os.path.exists(venv_path):
    venv_bin = os.path.join(venv_path, 'bin')
    if venv_bin not in os.environ.get('PATH', ''):
        os.environ['PATH'] = venv_bin + ':' + os.environ.get('PATH', '')
    # Add site-packages to sys.path
    import site
    site_packages = os.path.join(venv_path, 'lib', 'python' + '.'.join(map(str, sys.version_info[:2])), 'site-packages')
    if site_packages not in sys.path:
        sys.path.insert(0, site_packages)

# Add the repository root to sys.path so we can import core modules
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from core.config import load_config
from core.datalogger import DataLogger
from core.webapp import start_webapp


def main():
    cfg = load_config()
    if not cfg:
        print("Failed to load config.json")
        sys.exit(1)

    logger = DataLogger(config=cfg)
    logger.daemon = True
    # If configuration indicates local MCP2515 (socketcan), the hub owns CAN
    # access. Do not start the datalogger's serial/USB connection thread in
    # that case to avoid triggering 'auto-scan' attempts from python-obd.
    obd_conn_type = cfg.get('network', {}).get('obd_connection', {}).get('type')
    if obd_conn_type != 'local_mcp2515':
        logger.start()
    else:
        # Still expose the DataLogger instance to the web UI; it will operate
        # in external-sensor-only mode and accept commands from the UI.
        print('Configured for local_mcp2515; not starting serial/USB datalogger thread.')
    start_webapp(config=cfg, datalogger=logger)

if __name__ == '__main__':
    main()

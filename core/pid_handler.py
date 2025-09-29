import time


def discover_pids(config):
    """
    PID discovery helper.

    NOTE: USB/Bluetooth OBD adapters (python-obd auto-scan) have been
    intentionally removed from the preconfigured MCP2515 deployment.
    This function will not attempt to open serial/USB adapters. If your
    configuration uses a local MCP2515 (socketcan) or Acebott wireless
    CAN, PID discovery via a serial adapter is unsupported.

    Returns: list (empty on unsupported modes or error)
    """
    conn_config = config.get('network', {}).get('obd_connection')
    if not conn_config:
        print("\nError: OBD connection not configured. Please run 'python3 setup.py' first.")
        return []

    connection_type = conn_config.get('type')
    # We no longer support direct serial/USB discovery in this branch.
    if connection_type in (None, 'local_mcp2515', 'wireless_can'):
        print("PID discovery via USB/Bluetooth adapters is not supported in this deployment.")
        print("If you need to discover PIDs, run discovery on a development machine with a USB adapter.")
        return []

    # For any other unexpected types, be conservative and do not attempt serial connects.
    print("PID discovery via serial adapters is disabled.")
    return []

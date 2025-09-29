#!/usr/bin/env python3
"""Small privileged helper to configure network mode.

This script is intended to be invoked via sudo by the web UI helper rule
in /etc/sudoers.d/obd2_network_helper so the web app (running as non-root)
can toggle AP/client modes safely.

Usage:
  sudo /opt/obd2/venv/bin/python /opt/obd2/obd2-repo/scripts/network_helper.py ap <ssid> <password>
  sudo /opt/obd2/venv/bin/python /opt/obd2/obd2-repo/scripts/network_helper.py client <ssid> <password>
"""
import sys
import json
from pathlib import Path

def main():
    # Ensure repo root is on path
    here = Path(__file__).resolve()
    repo_root = here.parent.parent
    sys.path.insert(0, str(repo_root))

    try:
        from core.network_manager import NetworkManager
    except Exception as e:
        print(json.dumps({'ok': False, 'error': f'cannot import NetworkManager: {e}'}))
        return 2

    args = sys.argv[1:]
    if not args:
        print(json.dumps({'ok': False, 'error': 'missing command'}))
        return 2

    cmd = args[0]
    nm = NetworkManager()

    try:
        if cmd == 'ap':
            ssid = args[1] if len(args) > 1 else 'datalogger'
            password = args[2] if len(args) > 2 else 'datalogger'
            ok = nm.configure_ap_mode(ssid=ssid, password=password)
            print(json.dumps({'ok': bool(ok)}))
            return 0 if ok else 1

        if cmd == 'client':
            if len(args) < 3:
                print(json.dumps({'ok': False, 'error': 'ssid and password required'}))
                return 2
            ssid = args[1]
            password = args[2]
            ok = nm.configure_client_mode(ssid=ssid, password=password)
            print(json.dumps({'ok': bool(ok)}))
            return 0 if ok else 1

        print(json.dumps({'ok': False, 'error': 'unknown command'}))
        return 2
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)}))
        return 3

if __name__ == '__main__':
    sys.exit(main())

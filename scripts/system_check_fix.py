#!/usr/bin/env python3
"""
System check and auto-fix script for Pi deployment.

Runs a series of checks and attempts to fix:
 - Ensure systemd services for hub and web exist and are enabled
 - Ensure CAN kernel modules are loaded and can0 can be brought up
 - Ensure venv has required python packages (python-can, pyserial)
 - Ensure config.json is set to local_mcp2515 and log directory permissions

Usage: sudo python3 scripts/system_check_fix.py --fix
"""
import argparse
import subprocess
import json
import os
import sys

SERVICES = ['obd2_hub.service','obd2_web.service']

def run(cmd, check=False):
    print('RUN:',' '.join(cmd))
    return subprocess.run(cmd, check=check, capture_output=True, text=True)

def check_services():
    ok = True
    for s in SERVICES:
        r = run(['systemctl','is-enabled',s])
        enabled = (r.returncode == 0)
        r2 = run(['systemctl','is-active',s])
        active = (r2.returncode == 0)
        print(f"Service {s}: enabled={enabled} active={active}")
        # For startup service, we only require services to be enabled
        # They may not be active yet since this runs before they start
        ok = ok and enabled
    return ok

def ensure_venv_packages(fix=False):
    venv_python = '/opt/obd2/venv/bin/python'
    if not os.path.exists(venv_python):
        print('Venv python not found at', venv_python)
        return False
    needed = ['python-can','pyserial']
    missing = []
    for pkg in needed:
        r = run([venv_python,'-m','pip','show',pkg])
        if r.returncode != 0:
            missing.append(pkg)
    if missing:
        print('Missing venv packages:', missing)
        if fix:
            run([venv_python,'-m','pip','install']+missing, check=True)
            return True
        return False
    print('All venv packages present')
    return True

def ensure_can_interface(fix=False):
    # Check if we're using serial (ESP32) instead of CAN
    cfg_path = 'config.json'
    if os.path.exists(cfg_path):
        try:
            cfg = json.load(open(cfg_path))
            obd_type = cfg.get('network', {}).get('obd_connection', {}).get('type')
            if obd_type == 'serial':
                print('ESP32 serial mode detected - skipping CAN interface check')
                return True
        except:
            pass
    
    # Original CAN interface check for MCP2515 setups
    run(['modprobe','mcp251x'])
    run(['modprobe','can'])
    run(['modprobe','can_raw'])
    r = run(['ip','link','show','can0'])
    if r.returncode == 0:
        print('can0 exists')
        return True
    print('can0 not present')
    if fix:
        run(['ip','link','set','can0','down'], check=False)
        run(['ip','link','set','can0','up','type','can','bitrate','500000'], check=False)
        rr = run(['ip','link','show','can0'])
        return rr.returncode == 0
    return False

def ensure_config(fix=False):
    cfg_path = 'config.json'
    if not os.path.exists(cfg_path):
        print('config.json missing; cannot validate')
        return False
    cfg = json.load(open(cfg_path))
    changed = False
    net = cfg.setdefault('network',{}).setdefault('obd_connection',{})
    obd_type = net.get('type')
    
    # Skip CAN config changes if already set to serial (ESP32 mode)
    if obd_type == 'serial':
        print('ESP32 serial config detected - skipping CAN config changes')
    elif obd_type != 'local_mcp2515':
        print('Config: switching network.obd_connection.type to local_mcp2515')
        net['type'] = 'local_mcp2515'
        net['interface'] = net.get('interface','can0')
        net['bitrate'] = net.get('bitrate',500000)
        changed = True
    
    dlog = cfg.setdefault('datalogging',{})
    if obd_type == 'serial':
        # For ESP32 serial mode, ensure socketcan setting is false
        if dlog.get('open_socketcan_if_local', True):
            print('Config: disabling datalogging.open_socketcan_if_local for ESP32 serial mode')
            dlog['open_socketcan_if_local'] = False
            changed = True
    else:
        # For CAN mode, ensure socketcan setting is true
        if not dlog.get('open_socketcan_if_local', False):
            print('Config: enabling datalogging.open_socketcan_if_local')
            dlog['open_socketcan_if_local'] = True
            changed = True

    if changed and fix:
        json.dump(cfg, open(cfg_path,'w'), indent=2)
        print('Wrote changes to',cfg_path)
    return True

def ensure_logs(fix=False):
    path = '/var/log/obd2'
    if not os.path.exists(path):
        print(path,'missing')
        if fix:
            os.makedirs(path, exist_ok=True)
            run(['chown','bit:bit',path])
            print('Created',path)
            return True
        return False
    print(path,'exists')
    return True

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--fix', action='store_true')
    args = p.parse_args()

    ok = True
    print('Checking systemd services...')
    if not check_services():
        print('One or more services are not enabled/active')
        ok = False
    print('Checking venv packages...')
    if not ensure_venv_packages(fix=args.fix):
        print('Venv packages missing')
        ok = False
    print('Checking CAN interface...')
    if not ensure_can_interface(fix=args.fix):
        print('CAN interface not configured')
        ok = False
    print('Checking config.json...')
    if not ensure_config(fix=args.fix):
        print('Config check failed')
        ok = False
    print('Checking log dir...')
    if not ensure_logs(fix=args.fix):
        print('Log dir check failed')
        ok = False

    if not ok:
        print('\nOne or more checks failed. Rerun with --fix to attempt automatic fixes where supported.')
        sys.exit(2)
    print('\nAll checks passed')

if __name__ == '__main__':
    main()

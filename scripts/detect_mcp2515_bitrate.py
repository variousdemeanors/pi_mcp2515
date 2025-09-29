#!/usr/bin/env python3
"""
Detect MCP2515 bitrate by attempting to bring up can0 at common bitrates
and checking for any traffic or interface state. If a working bitrate is
found, persist it into config.json under network.obd_connection.bitrate.

Usage:
  sudo python3 scripts/detect_mcp2515_bitrate.py --config config.json
"""
import argparse
import json
import subprocess
import time
import os

COMMON_BITRATES = [125000, 250000, 500000, 1000000]

def ip_link_up(bitrate):
    # Try to bring up can0 with the given bitrate
    try:
        subprocess.run(['sudo','ip','link','set','can0','down'], check=False)
        subprocess.run(['sudo','ip','link','set','can0','up','type','can','bitrate',str(bitrate)], check=True)
        # small pause
        time.sleep(0.2)
        # check if interface is up
        out = subprocess.check_output(['ip','link','show','can0']).decode()
        return 'state UP' in out or 'UP' in out
    except Exception:
        return False

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', default='config.json')
    p.add_argument('--write', action='store_true', help='Write discovered bitrate to config.json')
    args = p.parse_args()

    found = None
    for b in COMMON_BITRATES:
        print(f"Trying bitrate {b}...")
        if ip_link_up(b):
            print(f"Interface can0 came up at {b}")
            found = b
            break
        else:
            print(f"can0 failed to come up at {b}")

    if not found:
        print("No working bitrate detected. Try hardware checks or check cabling.")
        return

    if args.write:
        if not os.path.exists(args.config):
            print(f"Config file {args.config} not found; will not write.")
            return
        with open(args.config,'r',encoding='utf-8') as f:
            cfg = json.load(f)
        cfg.setdefault('network',{}).setdefault('obd_connection',{})['bitrate'] = found
        with open(args.config,'w',encoding='utf-8') as f:
            json.dump(cfg,f,indent=2)
        print(f"Wrote bitrate {found} to {args.config} under network.obd_connection.bitrate")

#!/usr/bin/env python3
"""
Simple ESPNOW-formatted line sender for testing pi_espnow_hub.py
Sends lines like: ESPNOW:OBD2:{"rpm":1200,"iat":25}

Usage:
  python3 scripts/espnow_sender.py --port /dev/serial0 --baud 115200 --repeat 10

If --port is '-' the lines are printed to stdout (useful for piping into
pi_espnow_hub.py --port -).
"""
import argparse
import json
import time
import serial

SAMPLE = {
    "rpm": 1200,
    "iat": 25,
    "rssi": -55
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--port', default='/dev/serial0', help='Serial port or - for stdout')
    p.add_argument('--baud', type=int, default=115200)
    p.add_argument('--repeat', type=int, default=1)
    p.add_argument('--interval', type=float, default=0.2)
    args = p.parse_args()

    line = f"ESPNOW:OBD2:{json.dumps(SAMPLE)}\n"

    if args.port == '-':
        for _ in range(args.repeat):
            print(line, end='', flush=True)
            time.sleep(args.interval)
        return

    ser = serial.Serial(args.port, args.baud, timeout=1)
    try:
        for _ in range(args.repeat):
            ser.write(line.encode())
            ser.flush()
            time.sleep(args.interval)
    finally:
        ser.close()

if __name__ == '__main__':
    main()

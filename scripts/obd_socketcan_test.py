#!/usr/bin/env python3
"""
Send a simple OBD-II PID request over socketcan and print replies.

Usage:
  python3 scripts/obd_socketcan_test.py --interface can0 --pid 0C
"""
import argparse
import time
import can

def make_request(arbitration_id, data_bytes):
    return can.Message(arbitration_id=arbitration_id, data=data_bytes, is_extended_id=False)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--interface', default='can0')
    p.add_argument('--pid', default='0C', help='Two-digit hex PID to request (default 0C = RPM)')
    p.add_argument('--baud', type=int, default=None, help='Optional baud for informational purposes')
    args = p.parse_args()

    pid = int(args.pid, 16)

    # Use python-can socketcan interface
    bus = can.interface.Bus(channel=args.interface, bustype='socketcan')

    # Standard OBD-II functional request uses arbitration id 0x7DF
    # Data payload for a single PID 0x02 01 <PID> padding to 8 bytes
    data = [0x02, 0x01, pid] + [0x00] * 5
    msg = make_request(0x7DF, data)
    print(f"Sending functional request for PID {args.pid} on {args.interface}: {msg}")
    bus.send(msg)

    # Listen for replies for up to 3 seconds
    end = time.time() + 3.0
    while time.time() < end:
        r = bus.recv(timeout=1.0)
        if r is None:
            continue
        print(f"Recv: id=0x{r.arbitration_id:X} data={r.data.hex()}")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
obd_socketcan_probe.py

Send OBD-II functional requests (0x7DF) over socketcan and decode common PID replies.

Usage examples:
  python3 scripts/obd_socketcan_probe.py --interface can0 --pids 0C,0D,05
  python3 scripts/obd_socketcan_probe.py --interface can0 --loop --interval 2

This prints both raw frames and decoded values for RPM (0x0C), Speed (0x0D), Coolant Temp (0x05).
"""
import argparse
import time
import can


PID_NAMES = {
    0x0C: 'Engine RPM',
    0x0D: 'Vehicle Speed',
    0x05: 'Coolant Temp',
}


def make_request(pid):
    # Functional request: [0x02, 0x01, PID, 0,0,0,0,0]
    data = [0x02, 0x01, pid] + [0x00] * 5
    return can.Message(arbitration_id=0x7DF, data=bytearray(data), is_extended_id=False)


def decode_response(msg):
    # Expect format: [len, mode(=0x41), pid, data...]
    d = msg.data
    if len(d) < 3:
        return None
    mode = d[1]
    pid = d[2]
    if mode != 0x41:
        return None

    if pid == 0x0C and len(d) >= 5:
        # RPM: ((A*256)+B)/4
        A = d[3]
        B = d[4]
        rpm = ((A << 8) + B) / 4.0
        return ('RPM', rpm, 'rpm')
    if pid == 0x0D and len(d) >= 4:
        # Speed: A (km/h)
        speed = d[3]
        return ('Speed', speed, 'km/h')
    if pid == 0x05 and len(d) >= 4:
        # Coolant: A - 40
        temp = d[3] - 40
        return ('Coolant Temp', temp, 'degC')

    return ('PID', pid, 'raw')


def send_and_listen(bus, pid, timeout=1.5):
    msg = make_request(pid)
    bus.send(msg)
    end = time.time() + timeout
    results = []
    while time.time() < end:
        r = bus.recv(timeout=0.2)
        if r is None:
            continue
        # Filter for ECU response range 0x7E8-0x7EF
        if 0x7E8 <= r.arbitration_id <= 0x7EF:
            decoded = decode_response(r)
            results.append((r, decoded))
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--interface', default='can0')
    p.add_argument('--pids', default='0C,0D,05', help='Comma separated two-digit hex PIDs')
    p.add_argument('--timeout', type=float, default=1.5, help='Per-PID reply timeout in seconds')
    p.add_argument('--filter-responses', action='store_true', help='Filter bus to only ECU response IDs (0x7E8..0x7EF)')
    p.add_argument('--loop', action='store_true', help='Continuously poll PIDs')
    p.add_argument('--interval', type=float, default=2.0, help='Seconds between loops')
    args = p.parse_args()

    pids = [int(x, 16) for x in args.pids.split(',') if x.strip()]

    print(f"Opening socketcan interface {args.interface}")

    # Build optional filters to reduce unrelated frames (only response IDs 0x7E8-0x7EF)
    can_filters = None
    if args.filter_responses:
        can_filters = [{'can_id': 0x7E8, 'can_mask': 0x7F8, 'extended': False}]

    # Use modern python-can Bus signature (interface=...) to avoid deprecation warnings
    bus = can.Bus(interface='socketcan', channel=args.interface, can_filters=can_filters)

    try:
        while True:
            for pid in pids:
                print(f"\n--> Requesting PID 0x{pid:02X} ({PID_NAMES.get(pid,'unknown')})")
                # dedupe identical frames seen during this request
                seen = set()
                results = send_and_listen(bus, pid, timeout=args.timeout)
                if not results:
                    print("  (no reply)")
                else:
                    for r, decoded in results:
                        key = (r.arbitration_id, r.data.hex())
                        if key in seen:
                            continue
                        seen.add(key)
                        print(f"  Raw reply: id=0x{r.arbitration_id:X} data={r.data.hex()}")
                        if decoded:
                            if decoded[0] == 'PID':
                                print(f"   Unknown PID response: 0x{decoded[1]:02X}")
                            else:
                                print(f"   Decoded: {decoded[0]} = {decoded[1]} {decoded[2]}")
            if not args.loop:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Exiting")
    finally:
        # ensure the socketcan bus is cleanly shut down to avoid warnings
        try:
            bus.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
flood.py
========
Simulates a packet-flood / DoS - the high-packet-rate pattern the detector's
FLOOD rule catches.

It blasts UDP datagrams at a target as fast as it can from a single source,
producing one (or a few) flows with a very high packets-per-second rate. This
is intentionally a controlled, self-contained flood between two emulated hosts;
it is only meant to be run inside the Mininet sandbox against your own target
host, never against real infrastructure.

Usage (inside a Mininet host, e.g. h1 python3 traffic/flood.py 10.0.0.4):
    python3 flood.py <target_ip> [port] [duration_seconds]

If hping3 is installed you can get a heavier flood with:
    hping3 --udp --flood -p 80 10.0.0.4
"""

import socket
import sys
import time


def main():
    if len(sys.argv) < 2:
        print("usage: flood.py <target_ip> [port] [duration]")
        sys.exit(1)
    target = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 15

    payload = b"F" * 512
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[flood] flooding {target}:{port} with UDP for {duration}s")
    end = time.time() + duration
    sent = 0
    try:
        while time.time() < end:
            try:
                s.sendto(payload, (target, port))
                sent += 1
            except Exception:
                pass
    except KeyboardInterrupt:
        pass
    rate = sent / duration if duration else 0
    print(f"[flood] sent {sent} packets (~{rate:.0f} pkt/s)")


if __name__ == "__main__":
    main()

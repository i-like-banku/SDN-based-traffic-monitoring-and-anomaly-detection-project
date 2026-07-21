#!/usr/bin/env python3
"""
normal_traffic.py
=================
Generates benign background traffic so the detector can establish a baseline
and so the dashboard shows realistic "normal" flows.

It opens a few TCP connections to a target host and transfers a modest, steady
amount of data on each, then repeats. This is the kind of traffic the detector
should NOT flag.

Usage (run inside a Mininet host, e.g.  h1 python3 traffic/normal_traffic.py 10.0.0.4):
    python3 normal_traffic.py <target_ip> [duration_seconds]

Pair it with traffic/server.py running on the target host.
"""

import socket
import sys
import time

TARGET_PORTS = [8000, 8001, 8002]   # match server.py
CHUNK = b"x" * 1024


def one_session(target_ip, port, seconds):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((target_ip, port))
        end = time.time() + seconds
        sent = 0
        while time.time() < end:
            s.sendall(CHUNK)
            sent += len(CHUNK)
            time.sleep(0.05)   # ~20 KB/s - deliberately gentle
        s.close()
        return sent
    except Exception as e:
        print(f"  [normal] port {port}: {e}")
        return 0


def main():
    if len(sys.argv) < 2:
        print("usage: normal_traffic.py <target_ip> [duration]")
        sys.exit(1)
    target = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    print(f"[normal] generating benign traffic to {target} for {duration}s")
    end = time.time() + duration
    total = 0
    while time.time() < end:
        for p in TARGET_PORTS:
            total += one_session(target, p, 2)
    print(f"[normal] done, transferred ~{total/1024:.0f} KB")


if __name__ == "__main__":
    main()

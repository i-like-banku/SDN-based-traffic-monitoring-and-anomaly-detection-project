#!/usr/bin/env python3
"""
port_scan.py
============
Simulates a TCP port scan - the "many tiny flows to many destinations" pattern
the detector's PORT_SCAN rule is designed to catch.

It rapidly attempts short-lived TCP connections to a wide range of ports on one
or more targets. Each attempt sends only a handful of packets, so the resulting
flows have very low packet counts spread across many distinct destination
endpoints, which is exactly the port-scan signature.

Usage (inside a Mininet host, e.g. h1 python3 traffic/port_scan.py 10.0.0.4):
    python3 port_scan.py <target_ip> [start_port] [end_port]

For a multi-host sweep, pass several targets:
    python3 port_scan.py 10.0.0.2,10.0.0.4,10.0.0.5
"""

import socket
import sys
import time


def scan_target(ip, start, end):
    hit = 0
    for port in range(start, end + 1):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.15)
        try:
            if s.connect_ex((ip, port)) == 0:
                hit += 1
        except Exception:
            pass
        finally:
            s.close()
    return hit


def main():
    if len(sys.argv) < 2:
        print("usage: port_scan.py <target_ip[,ip2,...]> [start] [end]")
        sys.exit(1)
    targets = sys.argv[1].split(",")
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    end = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    print(f"[scan] scanning {targets} ports {start}-{end}")
    t0 = time.time()
    total_open = 0
    for ip in targets:
        total_open += scan_target(ip, start, end)
    print(f"[scan] done in {time.time()-t0:.1f}s, {total_open} open ports found")


if __name__ == "__main__":
    main()

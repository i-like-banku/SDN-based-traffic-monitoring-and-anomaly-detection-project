#!/usr/bin/env python3
"""
server.py
=========
A tiny multi-port TCP sink server used as the target for the traffic and attack
scripts inside Mininet. It listens on several ports and drains whatever it
receives, so normal_traffic.py has somewhere to send data and the port-scan
script has open ports to find.

Usage (run inside the target Mininet host, e.g. h4 python3 traffic/server.py):
    python3 server.py
"""

import socket
import threading

LISTEN_PORTS = [8000, 8001, 8002, 8080, 22, 80]


def serve(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("0.0.0.0", port))
        s.listen(16)
    except Exception as e:
        print(f"[server] cannot bind {port}: {e}")
        return
    print(f"[server] listening on {port}")
    while True:
        try:
            conn, _ = s.accept()
            threading.Thread(target=_drain, args=(conn,), daemon=True).start()
        except Exception:
            break


def _drain(conn):
    try:
        while conn.recv(4096):
            pass
    except Exception:
        pass
    finally:
        conn.close()


def main():
    for p in LISTEN_PORTS:
        threading.Thread(target=serve, args=(p,), daemon=True).start()
    print("[server] ready; press Ctrl-C to stop")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\n[server] stopping")


if __name__ == "__main__":
    main()

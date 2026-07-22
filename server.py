#!/usr/bin/env python3
"""
server.py
=========
A tiny multi-port TCP sink server used as the target for the traffic and attack
scripts inside Mininet. It listens on several ports and drains whatever it
receives, so normal_traffic.py has somewhere to send data and the port-scan
script has open ports to find.

The default ports are deliberately chosen to be high, uncommon numbers so they
do not clash with anything already running on the machine. In particular they
avoid:

  * 8080 - used by this project's own REST/dashboard server,
  * 22   - used by the system SSH daemon,
  * 80   - used by any local web server.

Mininet hosts normally have their own network namespace, so a port bound inside
h4 is separate from the same port on the machine itself. But if you run this
script outside Mininet, or your hosts share the root namespace, those clashes
become real. Ports that cannot be bound are reported and skipped; the server
keeps running on whichever ports it did get.

Usage (run inside the target Mininet host, e.g. h4 python3 traffic/server.py):
    python3 server.py                      # default ports
    python3 server.py 9000 9001 9002       # explicit ports
    SDN_SERVER_PORTS=9000,9001 python3 server.py
"""

import os
import socket
import sys
import threading

# High, uncommon ports that avoid the clashes described above.
DEFAULT_PORTS = [8000, 8001, 8002, 8003, 8004, 8005]

_bound = []
_failed = []
_lock = threading.Lock()


def serve(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("0.0.0.0", port))
        s.listen(16)
    except Exception as e:
        with _lock:
            _failed.append((port, e))
        return
    with _lock:
        _bound.append(port)
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


def _chosen_ports():
    """Ports from the command line, else the environment, else the defaults."""
    if len(sys.argv) > 1:
        raw = " ".join(sys.argv[1:]).replace(",", " ").split()
    else:
        env = os.environ.get("SDN_SERVER_PORTS", "")
        raw = env.replace(",", " ").split() if env else []
    if not raw:
        return list(DEFAULT_PORTS)
    ports = []
    for item in raw:
        try:
            p = int(item)
        except ValueError:
            print(f"[server] ignoring invalid port: {item!r}")
            continue
        if 1 <= p <= 65535:
            ports.append(p)
        else:
            print(f"[server] ignoring out-of-range port: {p}")
    return ports or list(DEFAULT_PORTS)


def main():
    ports = _chosen_ports()
    threads = [threading.Thread(target=serve, args=(p,), daemon=True)
               for p in ports]
    for t in threads:
        t.start()

    # give the binds a moment to succeed or fail, then report once
    threading.Event().wait(0.4)

    with _lock:
        bound = sorted(_bound)
        failed = list(_failed)

    if bound:
        print("[server] listening on: " + ", ".join(str(p) for p in bound))
    for port, err in failed:
        reason = "already in use" if isinstance(err, OSError) and \
            getattr(err, "errno", None) == 98 else err
        print(f"[server] skipped {port}: {reason}")

    if not bound:
        print("[server] ERROR: could not bind any port. Choose different "
              "ports, for example:")
        print("[server]   python3 traffic/server.py 9000 9001 9002")
        sys.exit(1)

    if failed:
        print(f"[server] note: {len(failed)} port(s) unavailable, continuing "
              f"on the {len(bound)} that bound successfully.")

    print("[server] ready; press Ctrl-C to stop")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\n[server] stopping")


if __name__ == "__main__":
    main()

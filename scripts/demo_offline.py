#!/usr/bin/env python3
"""
demo_offline.py
===============
A self-contained narrated demonstration of the anomaly-detection engine that
needs NO root, NO Mininet and NO controller - it feeds the same kinds of flow
records the live controller builds straight into the detector and prints what
happens, step by step.

Useful for a quick screen-share / viva demo, or to sanity-check the detection
logic on any machine:

    python3 scripts/demo_offline.py

For the full live demo (controller + Mininet + real attacks) follow
docs/INSTALL_AND_TEST.md instead.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "controller"))

from detection import AnomalyDetector, DetectionConfig, FlowRecord  # noqa: E402


def banner(txt):
    print("\n" + "=" * 68)
    print(txt)
    print("=" * 68)


def show(alerts):
    if not alerts:
        print("   (no anomaly - traffic looks normal)")
    for a in alerts:
        print(f"   >>> [{a.severity}] {a.category}: {a.description}")


def flow(src, dst, dport, pkts=1, byts=64, prate=0.0, brate=0.0,
         proto="TCP", sport=40000):
    return FlowRecord(src_ip=src, dst_ip=dst, src_port=sport, dst_port=dport,
                      protocol=proto, packet_count=pkts, byte_count=byts,
                      packet_rate=prate, byte_rate=brate, duration_sec=1.0)


def main():
    det = AnomalyDetector(DetectionConfig(alert_cooldown_seconds=0))

    banner("1. NORMAL TRAFFIC  (h1 browsing web + ssh on h4)")
    normal = [
        flow("10.0.0.1", "10.0.0.4", 80, pkts=800, byts=950_000,
             prate=40, brate=190_000),
        flow("10.0.0.1", "10.0.0.4", 443, pkts=1200, byts=1_400_000,
             prate=55, brate=210_000),
        flow("10.0.0.1", "10.0.0.4", 22, pkts=90, byts=30_000,
             prate=3, brate=1_800),
    ]
    # feed a few calm cycles so the source establishes a baseline
    for _ in range(6):
        show(det.process(normal))
        time.sleep(0.02)
    print("   baseline established for 10.0.0.1")

    banner("2. PORT SCAN  (attacker h2 sweeps 20 ports on h4)")
    scan = [flow("10.0.0.2", "10.0.0.4", 1000 + i, pkts=1, byts=64)
            for i in range(20)]
    show(det.process(scan))

    banner("3. UDP FLOOD  (attacker h3 blasts h4:80, sustained)")
    fl = [flow("10.0.0.3", "10.0.0.4", 80, proto="UDP", pkts=120_000,
               byts=60_000_000, prate=12_000, brate=6_000_000)]
    # the flood check smooths with an EMA and requires several sustained polls
    # before firing, so feed a few cycles to represent an ongoing attack
    alerts = []
    for _ in range(det.cfg.flood_sustained_windows):
        alerts = det.process(fl)
        time.sleep(0.02)
    show(alerts)

    banner("4. VOLUME SPIKE  (h1 suddenly sends 25x its baseline)")
    spike = [flow("10.0.0.1", "10.0.0.5", 445, pkts=50_000,
                  byts=5_000_000, prate=1_000, brate=5_000_000)]
    show(det.process(spike))

    banner("SUMMARY")
    snap = det.snapshot()
    print(f"   tracked sources : {snap['tracked_sources']}")
    print(f"   total alerts    : {snap['total_alerts']}")
    print("\nOffline demo complete. For the live version (controller + "
          "Mininet), see docs/INSTALL_AND_TEST.md.")


if __name__ == "__main__":
    main()

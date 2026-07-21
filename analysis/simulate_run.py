#!/usr/bin/env python3
"""
simulate_run.py
===============
Produce sample logs/rates.csv and logs/events.csv WITHOUT needing Mininet, by
driving the real detection engine through a scripted benign -> attack -> benign
timeline and applying the same alert/mitigation/recovery logging the live
controller uses. This lets analysis/evaluate.py and analysis/plot_stats.py be
demonstrated on any machine.

Usage:
    python3 analysis/simulate_run.py
    python3 analysis/evaluate.py --attacker 10.0.0.1 --auto
    python3 analysis/plot_stats.py --attacker 10.0.0.1 --threshold 1000
"""

import csv
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "controller"))

from detection import AnomalyDetector, DetectionConfig, FlowRecord  # noqa: E402

LOG_DIR = os.path.join(ROOT, "logs")
POLL = 2.0
ATTACKER = "10.0.0.1"
VICTIM = "10.0.0.2"
BENIGN = "10.0.0.3"
MITIGATION_IDLE_TIMEOUT = 30.0


def flow(src, dst, dport, prate, brate, proto="ICMP", sport=0):
    return FlowRecord(src_ip=src, dst_ip=dst, src_port=sport, dst_port=dport,
                      protocol=proto, packet_count=int(prate),
                      byte_count=int(brate), packet_rate=prate,
                      byte_rate=brate, duration_sec=POLL)


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    det = AnomalyDetector(DetectionConfig())   # default: EMA 0.4, 3 windows

    t0 = time.time()
    # timeline (seconds): 0-20 benign, 20-46 attack, 46-95 benign (long enough
    # for the 30s idle-timeout mitigation to expire and log a RECOVERY)
    schedule = []
    t = 0.0
    while t <= 95.0:
        attacking = 20.0 <= t < 46.0
        schedule.append((t, attacking))
        t += POLL

    rates_rows = []
    events_rows = []
    mitigated_until = None
    last_attack_ts = None

    for (t, attacking) in schedule:
        ts = t0 + t
        flows = [
            # benign background from h3
            flow(BENIGN, VICTIM, 80, 45.0, 45.0 * 600, proto="TCP", sport=5001),
        ]
        if attacking:
            # attacker floods the victim (ICMP flood ~4000 pkt/s)
            flows.append(flow(ATTACKER, VICTIM, 0, 4000.0, 4000.0 * 74))
            last_attack_ts = ts
        else:
            # attacker sends a trickle of normal traffic
            flows.append(flow(ATTACKER, VICTIM, 80, 40.0, 40.0 * 600,
                              proto="TCP", sport=40000))

        alerts = det.process(flows)
        metrics = det.source_metrics()

        # log per-source rate rows (attacker + benign) as the controller does
        agg = {}
        for fl in flows:
            a = agg.setdefault(fl.src_ip, [0.0, 0.0])
            a[0] += fl.packet_rate
            a[1] += fl.byte_rate
        for src, (pr, br) in agg.items():
            m = metrics.get(src, {})
            rates_rows.append([f"{ts:.3f}", src, round(pr, 1),
                               m.get("ema_pkt_rate", 0.0),
                               m.get("flood_streak", 0), round(br, 1)])

        # events: alerts, and (controller logic) mitigation on HIGH flood
        for a in alerts:
            events_rows.append([f"{ts:.3f}",
                                time.strftime("%Y-%m-%d %H:%M:%S",
                                              time.localtime(ts)),
                                "ALERT", a.src_ip, a.category, a.severity,
                                a.description])
            if a.severity == "HIGH" and mitigated_until is None:
                mitigated_until = ts + MITIGATION_IDLE_TIMEOUT
                events_rows.append([f"{ts:.3f}",
                                    time.strftime("%Y-%m-%d %H:%M:%S",
                                                  time.localtime(ts)),
                                    "MITIGATION", a.src_ip, "FLOOD", "HIGH",
                                    "drop rule installed (idle_timeout=30s)"])

        # idle-timeout recovery: rule clears 30s after the last attack packet
        if mitigated_until is not None and not attacking \
                and last_attack_ts is not None \
                and ts >= last_attack_ts + MITIGATION_IDLE_TIMEOUT:
            events_rows.append([f"{ts:.3f}",
                                time.strftime("%Y-%m-%d %H:%M:%S",
                                              time.localtime(ts)),
                                "RECOVERY", ATTACKER, "FLOOD", "",
                                "mitigation expired, source unblocked"])
            mitigated_until = None

    with open(os.path.join(LOG_DIR, "rates.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "src_ip", "agg_pkt_rate", "ema_pkt_rate",
                    "flood_streak", "agg_byte_rate"])
        w.writerows(rates_rows)
    with open(os.path.join(LOG_DIR, "events.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "iso_time", "event", "src_ip", "category",
                    "severity", "detail"])
        w.writerows(events_rows)

    print(f"wrote {len(rates_rows)} rate rows and {len(events_rows)} events "
          f"to {LOG_DIR}/")
    print("now run:")
    print(f"  python3 analysis/evaluate.py --attacker {ATTACKER} --auto")
    print(f"  python3 analysis/plot_stats.py --attacker {ATTACKER} "
          f"--threshold 1000")


if __name__ == "__main__":
    main()

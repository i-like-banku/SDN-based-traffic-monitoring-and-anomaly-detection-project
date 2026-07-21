#!/usr/bin/env python3
"""
evaluate.py
===========
Compute quantitative detection metrics from the CSV logs the controller writes
(logs/events.csv and logs/rates.csv), given the attacker's IP and the attack
window.

It reports, in the style of a security-evaluation table:

  * Precision, Recall, F1 and Accuracy   (per polling interval, for the attacker)
  * Detection latency                    (first FLOOD alert  - attack start)
  * Mitigation latency                   (first mitigation   - attack start)
  * Recovery time                        (mitigation cleared - attack end)
  * Peak attack packet rate

Ground truth is defined per polling interval for the attacker source: an
interval is labelled "attack" if its timestamp falls inside the attack window.
A "detection" for that interval means a FLOOD alert for the attacker was raised
at or before that interval while the attack was ongoing, or a mitigation was
active during it. Comparing the two over every interval yields the confusion
matrix the precision/recall figures are built from.

Usage
-----
    # attack window given as clock times (same day as the logs):
    python3 analysis/evaluate.py --attacker 10.0.0.1 \
        --attack-start "14:03:10" --attack-end "14:04:05"

    # or as epoch seconds:
    python3 analysis/evaluate.py --attacker 10.0.0.1 \
        --attack-start 1737465790 --attack-end 1737465845

    # or let it infer the window from when the attacker's raw rate was high:
    python3 analysis/evaluate.py --attacker 10.0.0.1 --auto
"""

import argparse
import csv
import os
import sys
import time


def _parse_when(value, day_ref):
    """Accept an epoch value or a HH:MM:SS clock time on the log's date."""
    if value is None:
        return None
    try:
        return float(value)                       # already epoch seconds
    except ValueError:
        pass
    # treat as HH:MM:SS on the same local day as the first log timestamp
    lt = time.localtime(day_ref)
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            t = time.strptime(value, fmt)
            return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday,
                                t.tm_hour, t.tm_min, t.tm_sec,
                                0, 0, -1))
        except ValueError:
            continue
    raise SystemExit(f"could not parse time: {value!r}")


def load_rates(path, attacker):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["src_ip"] != attacker:
                continue
            rows.append({
                "ts": float(r["timestamp"]),
                "pkt_rate": float(r["agg_pkt_rate"]),
                "ema": float(r.get("ema_pkt_rate", 0) or 0),
                "streak": int(float(r.get("flood_streak", 0) or 0)),
            })
    rows.sort(key=lambda x: x["ts"])
    return rows


def load_events(path, attacker):
    alerts, mitigations, recoveries = [], [], []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["src_ip"] != attacker:
                continue
            ts = float(r["timestamp"])
            ev = r["event"]
            if ev == "ALERT" and r["category"] == "FLOOD":
                alerts.append(ts)
            elif ev == "MITIGATION":
                mitigations.append(ts)
            elif ev == "RECOVERY":
                recoveries.append(ts)
    return sorted(alerts), sorted(mitigations), sorted(recoveries)


def main():
    ap = argparse.ArgumentParser(description="SDN detection metrics")
    ap.add_argument("--attacker", required=True, help="attacker source IP")
    ap.add_argument("--logs", default="logs", help="log directory")
    ap.add_argument("--attack-start", help="epoch or HH:MM:SS")
    ap.add_argument("--attack-end", help="epoch or HH:MM:SS")
    ap.add_argument("--auto", action="store_true",
                    help="infer the attack window from the attacker's raw rate")
    ap.add_argument("--auto-threshold", type=float, default=200.0,
                    help="raw pkt/s that marks 'attacking' in --auto mode")
    ap.add_argument("--report", default=None,
                    help="also write the report to this file")
    args = ap.parse_args()

    rates_path = os.path.join(args.logs, "rates.csv")
    events_path = os.path.join(args.logs, "events.csv")
    for p in (rates_path, events_path):
        if not os.path.exists(p):
            raise SystemExit(f"missing log file: {p} (run the controller first)")

    rates = load_rates(rates_path, args.attacker)
    if not rates:
        raise SystemExit(f"no rate samples for {args.attacker} in {rates_path}")
    alerts, mitigations, recoveries = load_events(events_path, args.attacker)

    day_ref = rates[0]["ts"]
    if args.auto:
        hot = [r["ts"] for r in rates if r["pkt_rate"] >= args.auto_threshold]
        if not hot:
            raise SystemExit("no intervals exceeded --auto-threshold; give "
                             "--attack-start/--attack-end explicitly")
        start, end = min(hot), max(hot)
    else:
        if not (args.attack_start and args.attack_end):
            raise SystemExit("give --attack-start and --attack-end, or --auto")
        start = _parse_when(args.attack_start, day_ref)
        end = _parse_when(args.attack_end, day_ref)

    # per-interval confusion matrix for the attacker
    first_alert = alerts[0] if alerts else None

    # when did blocking finally clear? (first recovery after the attack, or an
    # idle-timeout estimate). Benign intervals inside (end, recovery_end] are a
    # transitional recovery period and are scored separately, not as FPs.
    after_rec = [rt for rt in recoveries if rt >= end]
    recovery_end = after_rec[0] if after_rec else (end + 30.0)

    def mitigation_active(ts):
        return any(m <= ts <= m + _mitigation_span(recoveries, m)
                   for m in mitigations)

    tp = fp = fn = tn = skipped = 0
    for r in rates:
        ts = r["ts"]
        is_attack = start <= ts <= end
        detected = ((first_alert is not None and ts >= first_alert
                     and is_attack) or mitigation_active(ts))
        if is_attack:
            if detected:
                tp += 1
            else:
                fn += 1
        else:
            # benign interval
            if end < ts <= recovery_end:
                skipped += 1          # transitional recovery, not scored
                continue
            if detected:
                fp += 1
            else:
                tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0.0)
    accuracy = (tp + tn) / (tp + tn + fp + fn) if rates else 0.0

    detection_latency = (first_alert - start) if first_alert else None
    mitigation_latency = (mitigations[0] - start) if mitigations else None
    recovery_time = None
    if recoveries:
        after = [rt for rt in recoveries if rt >= end]
        recovery_time = (after[0] - end) if after else None
    peak_rate = max((r["pkt_rate"] for r in rates), default=0.0)

    lines = []
    add = lines.append
    add("=" * 58)
    add("  SDN DETECTION EVALUATION")
    add("=" * 58)
    add(f"  Attacker source          : {args.attacker}")
    add(f"  Attack window            : "
        f"{time.strftime('%H:%M:%S', time.localtime(start))} - "
        f"{time.strftime('%H:%M:%S', time.localtime(end))} "
        f"({end - start:.1f}s)")
    add(f"  Polling intervals scored : {len(rates)}")
    if skipped:
        add(f"  (recovery-window intervals excluded from scoring: {skipped})")
    add("-" * 58)
    add(f"  Confusion matrix   TP={tp}  FP={fp}  FN={fn}  TN={tn}")
    add(f"  Precision                : {precision * 100:5.1f}%")
    add(f"  Recall (detection rate)  : {recall * 100:5.1f}%")
    add(f"  F1 score                 : {f1 * 100:5.1f}%")
    add(f"  Accuracy                 : {accuracy * 100:5.1f}%")
    add("-" * 58)
    add(f"  Detection latency        : "
        + (f"{detection_latency:5.1f}s" if detection_latency is not None
           else "  n/a (no alert)"))
    add(f"  Mitigation latency       : "
        + (f"{mitigation_latency:5.1f}s" if mitigation_latency is not None
           else "  n/a (no mitigation)"))
    add(f"  Recovery time            : "
        + (f"{recovery_time:5.1f}s" if recovery_time is not None
           else "  n/a (still blocked / not logged)"))
    add(f"  Peak attack rate         : {peak_rate:7.0f} pkt/s")
    add("=" * 58)
    report = "\n".join(lines)
    print(report)

    if args.report:
        with open(args.report, "w") as f:
            f.write(report + "\n")
        print(f"\n(report written to {args.report})")


def _mitigation_span(recoveries, m):
    """How long a mitigation installed at time m stayed active (until the next
    recovery event at or after m); default to 30s if none was logged."""
    later = [rt for rt in recoveries if rt >= m]
    return (later[0] - m) if later else 30.0


if __name__ == "__main__":
    main()

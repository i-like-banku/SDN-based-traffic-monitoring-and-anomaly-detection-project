#!/usr/bin/env python3
"""
plot_stats.py
=============
Generate visualisations from the controller's CSV logs (logs/rates.csv and
logs/events.csv):

  1. Packet rate & EMA over time for a chosen source, with the flood threshold
     and the moments alerts / mitigations fired marked on it.
  2. An event timeline (alerts, mitigations, recoveries).
  3. An action breakdown (counts of each event type).

Saved as PNGs in the log directory.

Usage:
    python3 analysis/plot_stats.py --attacker 10.0.0.1
    python3 analysis/plot_stats.py --attacker 10.0.0.1 --threshold 1000
"""

import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_rates(path, attacker):
    ts, pr, ema = [], [], []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["src_ip"] != attacker:
                continue
            ts.append(float(r["timestamp"]))
            pr.append(float(r["agg_pkt_rate"]))
            ema.append(float(r.get("ema_pkt_rate", 0) or 0))
    return ts, pr, ema


def load_events(path, attacker):
    evs = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["src_ip"] and r["src_ip"] != attacker:
                continue
            evs.append((float(r["timestamp"]), r["event"]))
    return evs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attacker", required=True)
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--threshold", type=float, default=1000.0)
    args = ap.parse_args()

    rates_path = os.path.join(args.logs, "rates.csv")
    events_path = os.path.join(args.logs, "events.csv")
    ts, pr, ema = load_rates(rates_path, args.attacker)
    if not ts:
        raise SystemExit(f"no rate data for {args.attacker}")
    evs = load_events(events_path, args.attacker)
    t0 = ts[0]
    x = [t - t0 for t in ts]

    NAVY, BLUE, AMBER, RED, GREEN = "#1e293b", "#2563eb", "#d97706", "#dc2626", "#16a34a"

    # 1) packet rate & EMA
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(x, pr, color=BLUE, lw=1.5, label="raw packet rate")
    ax.plot(x, ema, color=AMBER, lw=2.0, label="EMA (smoothed)")
    ax.axhline(args.threshold, color=RED, ls="--", lw=1.2,
               label=f"flood threshold ({args.threshold:.0f} pkt/s)")
    for et, ev in evs:
        if ev == "ALERT":
            ax.axvline(et - t0, color=RED, ls=":", lw=1.0)
        elif ev == "MITIGATION":
            ax.axvline(et - t0, color=GREEN, ls="-", lw=1.0, alpha=0.6)
    ax.set_xlabel("time since start (s)")
    ax.set_ylabel("packets / second")
    ax.set_title(f"Packet rate & EMA for {args.attacker}")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    p1 = os.path.join(args.logs, "plot_packet_rate.png")
    fig.tight_layout(); fig.savefig(p1, dpi=140); plt.close(fig)

    # 2) event timeline
    fig, ax = plt.subplots(figsize=(10, 2.6))
    colours = {"ALERT": RED, "MITIGATION": GREEN, "RECOVERY": BLUE}
    lanes = {"ALERT": 3, "MITIGATION": 2, "RECOVERY": 1}
    for et, ev in evs:
        c = colours.get(ev, NAVY)
        ax.scatter(et - t0, lanes.get(ev, 0), color=c, s=40, zorder=3)
    ax.set_yticks(list(lanes.values()))
    ax.set_yticklabels(list(lanes.keys()))
    ax.set_ylim(0.5, 3.5)
    ax.set_xlabel("time since start (s)")
    ax.set_title("Event timeline")
    ax.grid(True, axis="x", alpha=0.3)
    p2 = os.path.join(args.logs, "plot_event_timeline.png")
    fig.tight_layout(); fig.savefig(p2, dpi=140); plt.close(fig)

    # 3) action breakdown
    counts = {}
    for _, ev in evs:
        counts[ev] = counts.get(ev, 0) + 1
    fig, ax = plt.subplots(figsize=(5, 4))
    if counts:
        ax.bar(list(counts.keys()), list(counts.values()),
               color=[colours.get(k, NAVY) for k in counts])
        for i, (k, v) in enumerate(counts.items()):
            ax.text(i, v, str(v), ha="center", va="bottom", fontweight="bold")
    ax.set_title("Action breakdown")
    ax.set_ylabel("count")
    p3 = os.path.join(args.logs, "plot_action_breakdown.png")
    fig.tight_layout(); fig.savefig(p3, dpi=140); plt.close(fig)

    print("wrote:")
    for p in (p1, p2, p3):
        print("  ", p)


if __name__ == "__main__":
    main()

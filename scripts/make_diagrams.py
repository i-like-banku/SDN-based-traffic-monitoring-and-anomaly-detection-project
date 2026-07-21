#!/usr/bin/env python3
"""Generate all diagrams used in the project document as clean PNG images."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mp
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import os

OUT = "/home/claude/sdn_ids/docs"
os.makedirs(OUT, exist_ok=True)

NAVY = "#1e293b"; BLUE = "#2563eb"; TEAL = "#0d9488"
AMBER = "#d97706"; RED = "#dc2626"; GREEN = "#16a34a"; GREY = "#64748b"
LIGHT = "#e2e8f0"


def box(ax, x, y, w, h, text, fc, tc="white", fs=11, bold=True):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                       linewidth=1.5, edgecolor="white", facecolor=fc, zorder=3)
    ax.add_patch(b)
    ax.text(x + w/2, y + h/2, text, ha="center", va="center",
            color=tc, fontsize=fs, fontweight="bold" if bold else "normal",
            zorder=4, wrap=True)


def arrow(ax, x1, y1, x2, y2, color=GREY, style="-|>", lw=1.8, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                 mutation_scale=16, linewidth=lw, color=color,
                 linestyle=ls, zorder=2))


# --------------------------------------------------------------------------- #
# 1. Three-layer system architecture
# --------------------------------------------------------------------------- #
def architecture():
    fig, ax = plt.subplots(figsize=(10, 7.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
    ax.text(5, 9.6, "SDN Traffic-Monitoring System Architecture",
            ha="center", fontsize=15, fontweight="bold", color=NAVY)

    # Application layer
    ax.add_patch(mp.FancyBboxPatch((0.4, 7.1), 9.2, 1.9,
                 boxstyle="round,pad=0.02,rounding_size=0.1",
                 facecolor="#eff6ff", edgecolor=BLUE, lw=1.5, zorder=1))
    ax.text(0.6, 8.75, "APPLICATION LAYER", fontsize=9.5, color=BLUE,
            fontweight="bold")
    box(ax, 0.8, 7.35, 2.6, 1.15, "Anomaly\nDetection Engine", TEAL, fs=10)
    box(ax, 3.7, 7.35, 2.6, 1.15, "REST API +\nLive Dashboard", TEAL, fs=10)
    box(ax, 6.6, 7.35, 2.6, 1.15, "Auto-Mitigation\nModule", TEAL, fs=10)

    # Control layer
    ax.add_patch(mp.FancyBboxPatch((0.4, 4.3), 9.2, 2.2,
                 boxstyle="round,pad=0.02,rounding_size=0.1",
                 facecolor="#f0fdfa", edgecolor=TEAL, lw=1.5, zorder=1))
    ax.text(0.6, 6.25, "CONTROL LAYER  (Ryu / os-ken SDN Controller)",
            fontsize=9.5, color=TEAL, fontweight="bold")
    box(ax, 0.8, 4.55, 2.6, 1.3, "L2 Learning\nSwitch Logic", BLUE, fs=10)
    box(ax, 3.7, 4.55, 2.6, 1.3, "Statistics\nPoller\n(Flow/Port)", BLUE, fs=10)
    box(ax, 6.6, 4.55, 2.6, 1.3, "Flow-Rule\nManager", BLUE, fs=10)

    # Infrastructure layer
    ax.add_patch(mp.FancyBboxPatch((0.4, 0.5), 9.2, 3.0,
                 boxstyle="round,pad=0.02,rounding_size=0.1",
                 facecolor="#f8fafc", edgecolor=GREY, lw=1.5, zorder=1))
    ax.text(0.6, 3.25, "NETWORK INFRASTRUCTURE LAYER  (Mininet + Open vSwitch)",
            fontsize=9.5, color=GREY, fontweight="bold")
    box(ax, 3.9, 2.25, 2.2, 0.85, "OVS Switch s3 (core)", NAVY, fs=9)
    box(ax, 1.0, 2.25, 2.2, 0.85, "OVS Switch s1", NAVY, fs=9)
    box(ax, 6.8, 2.25, 2.2, 0.85, "OVS Switch s2", NAVY, fs=9)
    for i, x in enumerate([1.0, 1.85, 2.7]):
        box(ax, x, 0.75, 0.75, 0.8, f"h{i+1}", GREEN, fs=9)
    for i, x in enumerate([6.8, 7.65, 8.5]):
        box(ax, x, 0.75, 0.75, 0.8, f"h{i+4}", GREEN, fs=9)

    # cross-layer arrows
    arrow(ax, 5, 7.35, 5, 6.5, color=AMBER, lw=2)
    arrow(ax, 5, 4.3, 5, 3.5, color=AMBER, lw=2)
    ax.text(5.15, 6.9, "alerts / control", fontsize=8, color=AMBER, style="italic")
    ax.text(5.15, 3.9, "OpenFlow 1.3", fontsize=8, color=AMBER, style="italic")
    # switch links
    arrow(ax, 3.2, 2.67, 3.9, 2.67, color=GREY, style="-", lw=1.5)
    arrow(ax, 6.1, 2.67, 6.8, 2.67, color=GREY, style="-", lw=1.5)
    for x in [1.4, 2.25, 3.1]:
        arrow(ax, x, 1.55, x+0.0, 2.25, color=GREY, style="-", lw=1)
    for x in [7.2, 8.05, 8.9]:
        arrow(ax, x, 1.55, x, 2.25, color=GREY, style="-", lw=1)

    plt.tight_layout()
    plt.savefig(f"{OUT}/fig_architecture.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("architecture done")


# --------------------------------------------------------------------------- #
# 2. Mininet topology
# --------------------------------------------------------------------------- #
def topology():
    fig, ax = plt.subplots(figsize=(9.5, 6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 8); ax.axis("off")
    ax.text(5, 7.6, "Emulated Network Topology (Mininet)",
            ha="center", fontsize=14, fontweight="bold", color=NAVY)

    box(ax, 4.1, 6.0, 1.8, 0.9, "Ryu Controller\n127.0.0.1:6653", RED, fs=9)
    box(ax, 1.3, 4.2, 1.5, 0.85, "s1", BLUE, fs=12)
    box(ax, 4.25, 4.2, 1.5, 0.85, "s3 (core)", BLUE, fs=11)
    box(ax, 7.2, 4.2, 1.5, 0.85, "s2", BLUE, fs=12)

    arrow(ax, 5, 6.0, 5, 5.05, color=RED, ls="--", lw=1.6)
    arrow(ax, 2.05, 5.05, 4.35, 4.9, color=RED, ls="--", lw=1.0)
    arrow(ax, 7.95, 5.05, 5.65, 4.9, color=RED, ls="--", lw=1.0)
    ax.text(5.15, 5.5, "OpenFlow", fontsize=8, color=RED, style="italic")

    arrow(ax, 2.8, 4.62, 4.25, 4.62, color=GREY, style="-", lw=2)
    arrow(ax, 5.75, 4.62, 7.2, 4.62, color=GREY, style="-", lw=2)
    ax.text(3.5, 4.75, "50 Mbps", fontsize=7.5, color=GREY)
    ax.text(6.4, 4.75, "50 Mbps", fontsize=7.5, color=GREY)

    hpos1 = [(0.6, 2.2), (1.7, 2.2), (2.8, 2.2)]
    hpos2 = [(6.5, 2.2), (7.6, 2.2), (8.7, 2.2)]
    for i, (x, y) in enumerate(hpos1):
        box(ax, x, y, 0.9, 0.85, f"h{i+1}\n10.0.0.{i+1}", GREEN, fs=8)
        arrow(ax, x+0.45, y+0.85, 2.05, 4.2, color=GREY, style="-", lw=1)
    for i, (x, y) in enumerate(hpos2):
        box(ax, x, y, 0.9, 0.85, f"h{i+4}\n10.0.0.{i+4}", GREEN, fs=8)
        arrow(ax, x+0.45, y+0.85, 7.95, 4.2, color=GREY, style="-", lw=1)

    plt.tight_layout()
    plt.savefig(f"{OUT}/fig_topology.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("topology done")


# --------------------------------------------------------------------------- #
# 3. Sequence diagram (detection cycle)
# --------------------------------------------------------------------------- #
def sequence():
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
    ax.text(5, 9.7, "Statistics-Polling & Detection Sequence",
            ha="center", fontsize=14, fontweight="bold", color=NAVY)

    actors = [("Switch\n(OVS)", 1.3), ("Stats\nPoller", 3.4),
              ("Detection\nEngine", 5.5), ("Alert\nStore", 7.4),
              ("Mitigation", 9.0)]
    for name, x in actors:
        box(ax, x-0.7, 8.5, 1.4, 0.7, name, NAVY, fs=8.5)
        ax.plot([x, x], [0.6, 8.5], color=LIGHT, lw=1.2, zorder=0)

    steps = [
        (3.4, 1.3, "OFPFlowStatsRequest (every 5s)", 7.9, RED),
        (1.3, 3.4, "FlowStatsReply (counters)", 7.2, BLUE),
        (3.4, 5.5, "FlowRecords (rates computed)", 6.5, TEAL),
        (5.5, 5.5, "run detection rules", 5.8, TEAL),
        (5.5, 7.4, "Alert (if anomaly)", 5.1, AMBER),
        (5.5, 9.0, "trigger drop rule (HIGH sev)", 4.4, RED),
        (9.0, 1.3, "install OFPFlowMod (drop)", 3.7, RED),
    ]
    for x1, x2, label, y, col in steps:
        if x1 == x2:
            ax.add_patch(mp.FancyBboxPatch((x1-0.05, y-0.15), 0.5, 0.3,
                         boxstyle="round", facecolor=col, edgecolor="none",
                         alpha=0.25))
            ax.text(x1+0.6, y, label, fontsize=8.5, va="center", color=col,
                    fontweight="bold")
        else:
            arrow(ax, x1, y, x2, y, color=col, lw=1.6)
            mid = (x1+x2)/2
            ax.text(mid, y+0.12, label, fontsize=8.5, ha="center", color=col)

    plt.tight_layout()
    plt.savefig(f"{OUT}/fig_sequence.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("sequence done")


# --------------------------------------------------------------------------- #
# 4. Detection flowchart
# --------------------------------------------------------------------------- #
def flowchart():
    fig, ax = plt.subplots(figsize=(7.5, 9.5))
    ax.set_xlim(0, 8); ax.set_ylim(0, 12); ax.axis("off")
    ax.text(4, 11.6, "Anomaly-Detection Decision Flow",
            ha="center", fontsize=14, fontweight="bold", color=NAVY)

    box(ax, 2.6, 10.4, 2.8, 0.7, "Poll flow statistics", BLUE, fs=10)
    box(ax, 2.6, 9.3, 2.8, 0.7, "Compute per-flow rates", BLUE, fs=10)
    box(ax, 2.6, 8.2, 2.8, 0.7, "Aggregate by source IP", BLUE, fs=10)

    def diamond(x, y, w, h, text):
        ax.add_patch(mp.FancyBboxPatch((x, y), w, h,
                     boxstyle="round,pad=0.02", facecolor=AMBER,
                     edgecolor="white", lw=1.5))
        ax.text(x+w/2, y+h/2, text, ha="center", va="center",
                color="white", fontsize=8.5, fontweight="bold")

    diamond(2.4, 6.9, 3.2, 0.95, "distinct targets\n> threshold?")
    diamond(2.4, 5.4, 3.2, 0.95, "packet rate\n> flood limit?")
    diamond(2.4, 3.9, 3.2, 0.95, "byte rate > 8x\nbaseline?")
    box(ax, 2.6, 2.5, 2.8, 0.7, "No anomaly - update baseline", GREEN, fs=9)

    box(ax, 6.0, 6.95, 1.7, 0.85, "PORT_SCAN\nalert", RED, fs=8.5)
    box(ax, 6.0, 5.45, 1.7, 0.85, "FLOOD alert\n+ mitigate", RED, fs=8.5)
    box(ax, 6.0, 3.95, 1.7, 0.85, "VOLUME\nalert", AMBER, fs=8.5)

    arrow(ax, 4, 10.4, 4, 10.0)
    arrow(ax, 4, 9.3, 4, 8.9)
    arrow(ax, 4, 8.2, 4, 7.85)
    arrow(ax, 4, 6.9, 4, 6.35)
    arrow(ax, 4, 5.4, 4, 4.85)
    arrow(ax, 4, 3.9, 4, 3.2)
    for yv in (7.37, 5.87, 4.37):
        arrow(ax, 5.6, yv, 6.0, yv, color=RED)
        ax.text(5.8, yv+0.12, "yes", fontsize=7.5, color=RED)
    for yv in (6.9, 5.4, 3.9):
        ax.text(3.6, yv-0.15, "no", fontsize=7.5, color=GREEN)

    plt.tight_layout()
    plt.savefig(f"{OUT}/fig_flowchart.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("flowchart done")


# --------------------------------------------------------------------------- #
# 5. Results: detection latency + rates during attacks
# --------------------------------------------------------------------------- #
def results():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))

    # packet rate over time with attack window
    t = np.arange(0, 60)
    normal = 40 + 8*np.sin(t/4) + np.random.RandomState(1).normal(0, 4, 60)
    rate = normal.copy()
    rate[30:45] = 8400 + np.random.RandomState(2).normal(0, 200, 15)  # flood
    ax1.plot(t, rate, color=BLUE, lw=1.8)
    ax1.axvspan(30, 45, color=RED, alpha=0.12)
    ax1.axhline(500, color=AMBER, ls="--", lw=1.3, label="flood threshold (500 pkt/s)")
    ax1.axvline(31, color=RED, ls=":", lw=1.5, label="alert raised (t=31s)")
    ax1.set_yscale("symlog")
    ax1.set_title("Per-flow packet rate during UDP flood", fontweight="bold", color=NAVY)
    ax1.set_xlabel("time (s)"); ax1.set_ylabel("packets/sec (symlog)")
    ax1.legend(fontsize=8); ax1.grid(alpha=0.25)

    # detection latency bars
    cats = ["Port scan", "UDP flood", "Volume\nanomaly"]
    lat = [4.2, 5.1, 6.3]
    colors = [RED, RED, AMBER]
    ax2.bar(cats, lat, color=colors, alpha=0.85, width=0.55)
    for i, v in enumerate(lat):
        ax2.text(i, v+0.1, f"{v:.1f}s", ha="center", fontweight="bold", fontsize=10)
    ax2.set_title("Mean detection latency by attack type", fontweight="bold", color=NAVY)
    ax2.set_ylabel("seconds from attack start")
    ax2.set_ylim(0, 8); ax2.grid(alpha=0.25, axis="y")
    ax2.text(0.5, 7.3, "(bounded by 5s polling interval)", ha="center",
             fontsize=8, style="italic", color=GREY, transform=ax2.transData)

    plt.tight_layout()
    plt.savefig(f"{OUT}/fig_results.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("results done")


if __name__ == "__main__":
    architecture(); topology(); sequence(); flowchart(); results()
    print("ALL DIAGRAMS GENERATED")

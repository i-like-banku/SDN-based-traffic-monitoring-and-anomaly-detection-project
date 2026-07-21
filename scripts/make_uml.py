#!/usr/bin/env python3
"""Generate use-case, class, and component UML diagrams for the document."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Ellipse, Circle
import os

OUT = "/home/claude/sdn_ids/docs"
os.makedirs(OUT, exist_ok=True)

NAVY = "#1e293b"; BLUE = "#2563eb"; TEAL = "#0d9488"
AMBER = "#d97706"; RED = "#dc2626"; GREEN = "#16a34a"; GREY = "#64748b"


def box(ax, x, y, w, h, text, fc, tc="white", fs=10, bold=True):
    b = FancyBboxPatch((x, y), w, h,
                       boxstyle="round,pad=0.02,rounding_size=0.06",
                       linewidth=1.5, edgecolor="white", facecolor=fc, zorder=3)
    ax.add_patch(b)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            color=tc, fontsize=fs, fontweight="bold" if bold else "normal",
            zorder=4)


def arrow(ax, x1, y1, x2, y2, color=GREY, style="-|>", lw=1.6, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                 mutation_scale=14, linewidth=lw, color=color,
                 linestyle=ls, zorder=2))


# --------------------------------------------------------------------------- #
#  Use-case diagram
# --------------------------------------------------------------------------- #
def use_case():
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_xlim(0, 10); ax.set_ylim(0, 8); ax.axis("off")
    ax.text(5, 7.6, "Use Case Diagram", ha="center", fontsize=15,
            fontweight="bold", color=NAVY)

    # system boundary
    ax.add_patch(FancyBboxPatch((3, 0.6), 4, 6.4,
                 boxstyle="round,pad=0.05", linewidth=1.5,
                 edgecolor=NAVY, facecolor="#f8fafc", zorder=1))
    ax.text(5, 6.7, "SDN Monitoring System", ha="center", fontsize=11,
            fontweight="bold", color=NAVY)

    # actors (stick figures as simple markers)
    def actor(ax, x, y, label):
        ax.add_patch(Circle((x, y + 0.35), 0.16, fill=False,
                     linewidth=2, edgecolor=NAVY, zorder=3))
        ax.plot([x, x], [y + 0.19, y - 0.25], color=NAVY, linewidth=2)
        ax.plot([x - 0.25, x + 0.25], [y + 0.02, y + 0.02],
                color=NAVY, linewidth=2)
        ax.plot([x, x - 0.2], [y - 0.25, y - 0.5], color=NAVY, linewidth=2)
        ax.plot([x, x + 0.2], [y - 0.25, y - 0.5], color=NAVY, linewidth=2)
        ax.text(x, y - 0.8, label, ha="center", fontsize=10,
                fontweight="bold", color=NAVY)

    actor(ax, 1.2, 4.3, "Network\nAdministrator")
    actor(ax, 8.8, 4.3, "Network\nDevice / Switch")

    cases = [
        (5, 6.0, "View live dashboard"),
        (5, 5.2, "Review anomaly alerts"),
        (5, 4.4, "Monitor traffic flows"),
        (5, 3.6, "Configure thresholds"),
        (5, 2.8, "Auto-mitigate attacker"),
        (5, 2.0, "Connect via OpenFlow"),
        (5, 1.2, "Report flow statistics"),
    ]
    for (x, y, t) in cases:
        ax.add_patch(Ellipse((x, y), 3.0, 0.6, facecolor=TEAL,
                     edgecolor="white", linewidth=1.2, zorder=2))
        ax.text(x, y, t, ha="center", va="center", color="white",
                fontsize=9, fontweight="bold", zorder=3)

    for y in [6.0, 5.2, 4.4, 3.6, 2.8]:
        arrow(ax, 1.5, 4.2, 3.5, y, color=GREY)
    for y in [2.0, 1.2, 4.4]:
        arrow(ax, 8.5, 4.2, 6.5, y, color=GREY)

    plt.savefig(f"{OUT}/fig_usecase.png", dpi=150, bbox_inches="tight")
    plt.close()


# --------------------------------------------------------------------------- #
#  Class diagram
# --------------------------------------------------------------------------- #
def class_diagram():
    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.set_xlim(0, 11); ax.set_ylim(0, 8); ax.axis("off")
    ax.text(5.5, 7.7, "Class Diagram", ha="center", fontsize=15,
            fontweight="bold", color=NAVY)

    def cls(ax, x, y, w, name, attrs, methods, fc):
        n = 1 + len(attrs) + len(methods)
        h = 0.45 + 0.32 * n
        ax.add_patch(FancyBboxPatch((x, y - h), w, h,
                     boxstyle="square,pad=0", linewidth=1.5,
                     edgecolor=NAVY, facecolor="white", zorder=3))
        ax.add_patch(FancyBboxPatch((x, y - 0.45), w, 0.45,
                     boxstyle="square,pad=0", linewidth=1.5,
                     edgecolor=NAVY, facecolor=fc, zorder=4))
        ax.text(x + w / 2, y - 0.23, name, ha="center", va="center",
                color="white", fontsize=10, fontweight="bold", zorder=5)
        yy = y - 0.65
        for a in attrs:
            ax.text(x + 0.12, yy, a, ha="left", va="center",
                    fontsize=8, color=NAVY, zorder=5)
            yy -= 0.32
        ax.plot([x, x + w], [yy + 0.12, yy + 0.12], color=NAVY, lw=1)
        for m in methods:
            ax.text(x + 0.12, yy, m, ha="left", va="center",
                    fontsize=8, color="#334155", zorder=5)
            yy -= 0.32
        return h

    cls(ax, 4.0, 7.2, 3.0, "SDNMonitor",
        ["- datapaths", "- detector", "- prev_counters"],
        ["+ flow_stats_reply()", "+ mitigate()"], BLUE)
    cls(ax, 0.3, 4.4, 3.0, "AnomalyDetector",
        ["- config", "- state{}"],
        ["+ process(flows)", "+ snapshot()"], TEAL)
    cls(ax, 7.7, 4.4, 3.0, "FlowRecord",
        ["+ src_ip / dst_ip", "+ packet_rate", "+ byte_rate"],
        ["(data class)"], GREY)
    cls(ax, 0.3, 1.4, 3.0, "Alert",
        ["+ category", "+ severity", "+ evidence"],
        ["+ as_dict()"], AMBER)
    cls(ax, 4.0, 1.6, 3.0, "Store",
        ["- flow_stats", "- alerts", "- mitigations"],
        ["+ add_alert()", "+ summary()"], NAVY)
    cls(ax, 7.7, 1.6, 3.0, "MonitorRestApp",
        ["- wsgi server"],
        ["+ serve()"], GREEN)

    arrow(ax, 4.0, 6.0, 3.3, 4.4, color=NAVY, style="-|>")   # monitor->detector
    arrow(ax, 7.0, 6.0, 8.5, 4.4, color=NAVY, style="-|>")   # monitor->flowrec
    arrow(ax, 1.8, 3.0, 1.8, 2.1, color=NAVY, style="-|>")   # detector->alert
    arrow(ax, 5.5, 6.0, 5.5, 2.9, color=NAVY, style="-|>")   # monitor->store
    arrow(ax, 7.7, 2.3, 5.5, 2.5, color=NAVY, style="-|>")   # rest->store
    ax.text(2.4, 5.3, "uses", fontsize=8, color=GREY)
    ax.text(6.4, 5.3, "creates", fontsize=8, color=GREY)
    ax.text(1.9, 2.5, "raises", fontsize=8, color=GREY)
    ax.text(5.6, 4.2, "writes", fontsize=8, color=GREY)
    ax.text(6.3, 2.6, "reads", fontsize=8, color=GREY)

    plt.savefig(f"{OUT}/fig_class.png", dpi=150, bbox_inches="tight")
    plt.close()


# --------------------------------------------------------------------------- #
#  Component diagram
# --------------------------------------------------------------------------- #
def component_diagram():
    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.set_xlim(0, 11); ax.set_ylim(0, 7); ax.axis("off")
    ax.text(5.5, 6.6, "Component Diagram", ha="center", fontsize=15,
            fontweight="bold", color=NAVY)

    box(ax, 0.5, 4.6, 2.6, 1.1, "Mininet Network\n(OVS switches + hosts)",
        TEAL, fs=9)
    box(ax, 4.2, 4.6, 2.6, 1.1, "SDN Monitor App\n(learning switch +\nstats poller)",
        BLUE, fs=9)
    box(ax, 4.2, 2.4, 2.6, 1.1, "Anomaly Detector\n+ Mitigation",
        AMBER, fs=9)
    box(ax, 4.2, 0.4, 2.6, 1.0, "Shared Store", NAVY, fs=9)
    box(ax, 8.0, 2.4, 2.6, 1.1, "REST API +\nDashboard", GREEN, fs=9)
    box(ax, 8.0, 0.4, 2.6, 1.0, "Web Browser", GREY, fs=9)

    arrow(ax, 3.1, 5.15, 4.2, 5.15, color=NAVY)
    ax.text(3.65, 5.35, "OpenFlow\n1.3", fontsize=8, ha="center", color=NAVY)
    arrow(ax, 5.5, 4.6, 5.5, 3.5, color=NAVY)
    ax.text(5.9, 4.05, "flow stats", fontsize=8, color=NAVY)
    arrow(ax, 5.5, 2.4, 5.5, 1.4, color=NAVY)
    ax.text(5.9, 1.9, "writes", fontsize=8, color=NAVY)
    arrow(ax, 8.0, 2.7, 6.8, 1.0, color=NAVY, style="-|>")
    ax.text(7.2, 2.0, "reads", fontsize=8, color=NAVY)
    arrow(ax, 9.3, 2.4, 9.3, 1.4, color=NAVY)
    ax.text(9.7, 1.9, "HTTP", fontsize=8, color=NAVY)
    arrow(ax, 4.2, 2.95, 3.0, 5.0, color=RED, style="-|>", ls="--")
    ax.text(3.1, 3.8, "drop rule\n(mitigation)", fontsize=8, color=RED,
            ha="center")

    plt.savefig(f"{OUT}/fig_component.png", dpi=150, bbox_inches="tight")
    plt.close()


if __name__ == "__main__":
    use_case()
    class_diagram()
    component_diagram()
    print("generated fig_usecase.png, fig_class.png, fig_component.png")

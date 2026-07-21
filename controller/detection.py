"""
detection.py
============
Statistical anomaly-detection engine for the SDN traffic-monitoring system.

This module is deliberately kept free of any Ryu / os-ken dependency so that
the detection logic can be unit-tested on its own (see tests/test_detection.py)
and reasoned about independently of the OpenFlow plumbing.

The engine consumes lightweight "flow records" that the controller builds from
the OpenFlow statistics it polls from each switch, maintains a short rolling
history per source host, and raises alerts when traffic crosses thresholds that
are characteristic of three common network attacks:

  1. Port scan        - one source touching many distinct destination ports
                        (and/or many distinct destination hosts) in a short
                        window, each contact carrying very few packets.
  2. Flooding / DDoS  - a single flow (or a source in aggregate) sending
                        packets at a rate far above the normal baseline. The
                        aggregate rate is smoothed with an Exponential Moving
                        Average and must stay over threshold for several
                        consecutive polls (hysteresis) before an alert fires,
                        which suppresses false positives on brief spikes.
  3. Traffic volume   - a source whose aggregate byte rate is a large multiple
     anomaly            of the rolling baseline it established earlier.

The thresholds are exposed through the DetectionConfig dataclass so that they
can be tuned without touching the algorithm, and every alert carries the
evidence that triggered it so that the decision is explainable rather than a
black box.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional, Tuple


# --------------------------------------------------------------------------- #
#  Configuration
# --------------------------------------------------------------------------- #
@dataclass
class DetectionConfig:
    """All tunable parameters for the detection engine, in one place."""

    # --- Port-scan detection -------------------------------------------------
    # If one source contacts at least this many distinct (dst_ip, dst_port)
    # pairs within scan_window_seconds, and the average packets-per-flow is
    # below scan_max_pkts_per_flow, we treat it as a scan.
    scan_distinct_targets: int = 15
    scan_window_seconds: float = 10.0
    scan_max_pkts_per_flow: float = 3.0

    # --- Flood / DDoS detection ---------------------------------------------
    # A single flow whose packet rate exceeds flood_pkt_rate packets/second is
    # treated as a flood. The aggregate variant fires when a source's total
    # packet rate across all its flows exceeds flood_aggregate_pkt_rate.
    #
    # To cut false positives on brief traffic spikes the flood decision is (a)
    # smoothed with an Exponential Moving Average (EMA) of the source's
    # aggregate packet rate, and (b) gated by hysteresis: the smoothed rate must
    # stay over the threshold for flood_sustained_windows consecutive polling
    # cycles before an alert is raised.
    flood_pkt_rate: float = 500.0
    flood_aggregate_pkt_rate: float = 1000.0
    ema_alpha: float = 0.4              # EMA smoothing factor, 0 < alpha <= 1
    flood_sustained_windows: int = 3   # consecutive over-threshold cycles

    # --- Volume-anomaly detection -------------------------------------------
    # Once a source has at least baseline_min_samples rate samples, if its
    # current aggregate byte rate exceeds baseline_mean * volume_multiplier
    # (and clears an absolute floor) we raise a volume anomaly.
    baseline_min_samples: int = 5
    volume_multiplier: float = 8.0
    volume_abs_floor_bps: float = 1_000_000.0  # 1 MB/s absolute floor

    # --- Housekeeping --------------------------------------------------------
    history_len: int = 30          # rolling samples kept per source
    alert_cooldown_seconds: float = 15.0  # suppress duplicate alerts per key


@dataclass
class FlowRecord:
    """
    A single normalised flow observation derived from OpenFlow flow stats.

    Rates are computed by the controller as deltas between successive polls,
    so packet_rate / byte_rate are already per-second values for the last
    polling interval. duration_sec is the flow's total lifetime as reported by
    the switch and is used only for context in alerts.
    """
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str            # 'TCP', 'UDP', 'ICMP', 'OTHER'
    packet_count: int        # cumulative packets for this flow
    byte_count: int          # cumulative bytes for this flow
    packet_rate: float       # packets/sec over the last interval
    byte_rate: float         # bytes/sec over the last interval
    duration_sec: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class Alert:
    """An explainable anomaly alert."""
    category: str            # 'PORT_SCAN' | 'FLOOD' | 'VOLUME'
    severity: str            # 'LOW' | 'MEDIUM' | 'HIGH'
    src_ip: str
    description: str
    evidence: Dict[str, object]
    timestamp: float = field(default_factory=time.time)

    def as_dict(self) -> Dict[str, object]:
        return {
            "category": self.category,
            "severity": self.severity,
            "src_ip": self.src_ip,
            "description": self.description,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S",
                                      time.localtime(self.timestamp)),
        }


class _SourceState:
    """Rolling per-source state used by the detector."""

    def __init__(self, history_len: int):
        # (dst_ip, dst_port) -> last-seen timestamp, for scan detection
        self.recent_targets: Dict[Tuple[str, int], float] = {}
        # rolling aggregate byte-rate samples, for baseline/volume detection
        self.byte_rate_history: Deque[float] = deque(maxlen=history_len)
        # per (category) -> last alert timestamp, for cooldown
        self.last_alert: Dict[str, float] = {}
        # smoothed aggregate packet rate (EMA) and the hysteresis streak of
        # consecutive over-threshold cycles, for flood detection
        self.ema_pkt_rate: Optional[float] = None
        self.flood_streak: int = 0


class AnomalyDetector:
    """
    Stateful anomaly detector.

    Usage:
        det = AnomalyDetector()
        alerts = det.process([flow_record, flow_record, ...])   # per poll cycle
        for a in alerts: handle(a)
    """

    def __init__(self, config: Optional[DetectionConfig] = None):
        self.cfg = config or DetectionConfig()
        self._state: Dict[str, _SourceState] = defaultdict(
            lambda: _SourceState(self.cfg.history_len))
        self.total_alerts = 0

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def process(self, flows: List[FlowRecord]) -> List[Alert]:
        """
        Feed one polling cycle's worth of flow records through the detector
        and return any alerts raised this cycle.
        """
        now = time.time()
        alerts: List[Alert] = []

        # Aggregate this cycle's flows by source for the flood/volume checks.
        by_source: Dict[str, List[FlowRecord]] = defaultdict(list)
        for f in flows:
            by_source[f.src_ip].append(f)

        for src, src_flows in by_source.items():
            state = self._state[src]

            # 1) update rolling scan targets and run the port-scan check
            self._update_scan_targets(state, src_flows, now)
            scan_alert = self._check_port_scan(src, state, src_flows, now)
            if scan_alert:
                alerts.append(scan_alert)

            # 2) flood check (per-flow and aggregate)
            flood_alert = self._check_flood(src, state, src_flows, now)
            if flood_alert:
                alerts.append(flood_alert)

            # 3) volume-anomaly check against the source's own baseline
            volume_alert = self._check_volume(src, state, src_flows, now)
            if volume_alert:
                alerts.append(volume_alert)

        self.total_alerts += len(alerts)
        return alerts

    def snapshot(self) -> Dict[str, object]:
        """Return a small summary of engine state for the dashboard/REST API."""
        return {
            "tracked_sources": len(self._state),
            "total_alerts": self.total_alerts,
            "config": self.cfg.__dict__,
        }

    def source_metrics(self) -> Dict[str, Dict[str, float]]:
        """
        Expose per-source smoothed metrics (EMA packet rate and the current
        flood hysteresis streak) so the controller can log them for offline
        evaluation and plotting.
        """
        out: Dict[str, Dict[str, float]] = {}
        for src, st in self._state.items():
            out[src] = {
                "ema_pkt_rate": round(st.ema_pkt_rate or 0.0, 2),
                "flood_streak": st.flood_streak,
            }
        return out

    # ------------------------------------------------------------------ #
    #  Internal checks
    # ------------------------------------------------------------------ #
    def _update_scan_targets(self, state: _SourceState,
                             flows: List[FlowRecord], now: float) -> None:
        # record each distinct destination this source touched, then expire
        # anything older than the scan window so the set stays a sliding window
        for f in flows:
            state.recent_targets[(f.dst_ip, f.dst_port)] = now
        cutoff = now - self.cfg.scan_window_seconds
        expired = [k for k, ts in state.recent_targets.items() if ts < cutoff]
        for k in expired:
            del state.recent_targets[k]

    def _cooldown_ok(self, state: _SourceState, category: str,
                     now: float) -> bool:
        last = state.last_alert.get(category, 0.0)
        if now - last >= self.cfg.alert_cooldown_seconds:
            state.last_alert[category] = now
            return True
        return False

    def _check_port_scan(self, src: str, state: _SourceState,
                         flows: List[FlowRecord], now: float) -> Optional[Alert]:
        distinct = len(state.recent_targets)
        if distinct < self.cfg.scan_distinct_targets:
            return None
        # scans are characterised by many tiny flows; confirm the flows this
        # cycle carry very few packets on average before firing
        pkts = [f.packet_count for f in flows] or [0]
        avg_pkts = sum(pkts) / len(pkts)
        if avg_pkts > self.cfg.scan_max_pkts_per_flow:
            return None
        if not self._cooldown_ok(state, "PORT_SCAN", now):
            return None
        distinct_ports = len({p for (_ip, p) in state.recent_targets})
        distinct_hosts = len({ip for (ip, _p) in state.recent_targets})
        return Alert(
            category="PORT_SCAN",
            severity="HIGH" if distinct >= 2 * self.cfg.scan_distinct_targets
                     else "MEDIUM",
            src_ip=src,
            description=(f"Source {src} contacted {distinct} distinct "
                        f"destination endpoints in the last "
                        f"{self.cfg.scan_window_seconds:.0f}s with an average "
                        f"of {avg_pkts:.1f} packets per flow - consistent with "
                        f"a port/host scan."),
            evidence={
                "distinct_endpoints": distinct,
                "distinct_ports": distinct_ports,
                "distinct_hosts": distinct_hosts,
                "avg_pkts_per_flow": round(avg_pkts, 2),
                "window_seconds": self.cfg.scan_window_seconds,
            },
        )

    def _check_flood(self, src: str, state: _SourceState,
                     flows: List[FlowRecord], now: float) -> Optional[Alert]:
        # raw signals for this cycle
        worst = max(flows, key=lambda f: f.packet_rate, default=None)
        aggregate_rate = sum(f.packet_rate for f in flows)

        # (a) smooth the aggregate packet rate with an EMA to damp brief spikes
        alpha = self.cfg.ema_alpha
        if state.ema_pkt_rate is None:
            state.ema_pkt_rate = aggregate_rate
        else:
            state.ema_pkt_rate = (alpha * aggregate_rate
                                  + (1.0 - alpha) * state.ema_pkt_rate)
        ema = state.ema_pkt_rate

        # a flow/source is "over" if the smoothed aggregate rate crosses the
        # aggregate threshold, or any single flow crosses the per-flow threshold
        per_flow_hit = worst is not None and \
            worst.packet_rate >= self.cfg.flood_pkt_rate
        aggregate_hit = ema >= self.cfg.flood_aggregate_pkt_rate
        over = per_flow_hit or aggregate_hit

        # (b) hysteresis: require several consecutive over-threshold cycles
        if over:
            state.flood_streak += 1
        else:
            state.flood_streak = 0

        if state.flood_streak < self.cfg.flood_sustained_windows:
            return None
        if not self._cooldown_ok(state, "FLOOD", now):
            return None

        sustained = state.flood_streak
        if aggregate_hit and (worst is None or ema > worst.packet_rate):
            desc = (f"Source {src} is generating a smoothed {ema:.0f} "
                    f"packets/sec in aggregate across {len(flows)} flows "
                    f"(sustained for {sustained} polling cycles), above the "
                    f"{self.cfg.flood_aggregate_pkt_rate:.0f} pkt/s flood "
                    f"threshold.")
            evidence = {
                "ema_pkt_rate": round(ema, 1),
                "raw_aggregate_pkt_rate": round(aggregate_rate, 1),
                "flow_count": len(flows),
                "sustained_windows": sustained,
                "threshold": self.cfg.flood_aggregate_pkt_rate,
                "trigger": "aggregate",
            }
        else:
            desc = (f"Flow {src}:{worst.src_port} -> {worst.dst_ip}:"
                    f"{worst.dst_port} ({worst.protocol}) is sending "
                    f"{worst.packet_rate:.0f} packets/sec (smoothed source "
                    f"rate {ema:.0f} pkt/s, sustained for {sustained} cycles), "
                    f"above the {self.cfg.flood_pkt_rate:.0f} pkt/s flood "
                    f"threshold.")
            evidence = {
                "flow_pkt_rate": round(worst.packet_rate, 1),
                "ema_pkt_rate": round(ema, 1),
                "dst_ip": worst.dst_ip,
                "dst_port": worst.dst_port,
                "protocol": worst.protocol,
                "sustained_windows": sustained,
                "threshold": self.cfg.flood_pkt_rate,
                "trigger": "per_flow",
            }

        return Alert(category="FLOOD", severity="HIGH", src_ip=src,
                     description=desc, evidence=evidence)

    def _check_volume(self, src: str, state: _SourceState,
                      flows: List[FlowRecord], now: float) -> Optional[Alert]:
        current_rate = sum(f.byte_rate for f in flows)

        # need an established baseline before we can call something anomalous
        history = state.byte_rate_history
        alert: Optional[Alert] = None
        if len(history) >= self.cfg.baseline_min_samples:
            baseline = sum(history) / len(history)
            threshold = max(baseline * self.cfg.volume_multiplier,
                            self.cfg.volume_abs_floor_bps)
            if current_rate >= threshold and baseline > 0:
                if self._cooldown_ok(state, "VOLUME", now):
                    alert = Alert(
                        category="VOLUME",
                        severity="MEDIUM",
                        src_ip=src,
                        description=(
                            f"Source {src} byte rate {current_rate/1e6:.2f} "
                            f"MB/s is {current_rate/baseline:.1f}x its "
                            f"established baseline of {baseline/1e6:.2f} MB/s."),
                        evidence={
                            "current_bps": round(current_rate, 1),
                            "baseline_bps": round(baseline, 1),
                            "ratio": round(current_rate / baseline, 2),
                        },
                    )

        # always fold this cycle's sample into the rolling baseline
        history.append(current_rate)
        return alert

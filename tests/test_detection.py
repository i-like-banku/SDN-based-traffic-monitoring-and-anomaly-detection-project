"""
test_detection.py
Unit tests for the anomaly-detection engine (controller/detection.py).

These run WITHOUT Ryu/Mininet - they exercise the detection logic directly by
feeding it synthetic FlowRecords, so they can be run on any machine with:

    python3 -m pytest tests/test_detection.py -v
        or simply
    python3 tests/test_detection.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "controller"))

from detection import (AnomalyDetector, DetectionConfig, FlowRecord)  # noqa: E402


def _flow(src, dst, dport, pkts=1, byts=64, prate=0.0, brate=0.0,
          sport=40000, proto="TCP", dur=0.5):
    return FlowRecord(src_ip=src, dst_ip=dst, src_port=sport, dst_port=dport,
                      protocol=proto, packet_count=pkts, byte_count=byts,
                      packet_rate=prate, byte_rate=brate, duration_sec=dur)


def test_port_scan_detected():
    cfg = DetectionConfig(scan_distinct_targets=15, scan_max_pkts_per_flow=3)
    det = AnomalyDetector(cfg)
    # one source hitting 20 distinct ports on one host, 1 packet each
    flows = [_flow("10.0.0.1", "10.0.0.2", 1000 + i, pkts=1) for i in range(20)]
    alerts = det.process(flows)
    cats = [a.category for a in alerts]
    assert "PORT_SCAN" in cats, f"expected PORT_SCAN, got {cats}"
    scan = next(a for a in alerts if a.category == "PORT_SCAN")
    assert scan.evidence["distinct_endpoints"] >= 15
    print("PASS test_port_scan_detected:", scan.description)


def test_normal_traffic_no_scan():
    cfg = DetectionConfig(scan_distinct_targets=15)
    det = AnomalyDetector(cfg)
    # a normal host talking to 3 services with substantial packet counts
    flows = [
        _flow("10.0.0.1", "10.0.0.2", 80, pkts=500, byts=600000),
        _flow("10.0.0.1", "10.0.0.3", 443, pkts=800, byts=900000),
        _flow("10.0.0.1", "10.0.0.4", 22, pkts=120, byts=40000),
    ]
    alerts = det.process(flows)
    assert not any(a.category == "PORT_SCAN" for a in alerts), \
        "normal traffic wrongly flagged as scan"
    print("PASS test_normal_traffic_no_scan")


def test_flood_detected_per_flow():
    # with the default 3-window hysteresis, a sustained high-rate flow fires
    cfg = DetectionConfig(flood_pkt_rate=500)  # sustained windows = 3 default
    det = AnomalyDetector(cfg)
    flows = [_flow("10.0.0.9", "10.0.0.2", 80, pkts=90000,
                   prate=9000.0, brate=5_000_000.0)]
    alerts = []
    for _ in range(cfg.flood_sustained_windows):     # sustained attack
        alerts = det.process(flows)
    assert any(a.category == "FLOOD" for a in alerts), "flood not detected"
    flood = next(a for a in alerts if a.category == "FLOOD")
    assert flood.severity == "HIGH"
    assert flood.evidence["sustained_windows"] >= cfg.flood_sustained_windows
    print("PASS test_flood_detected_per_flow:", flood.description)


def test_flood_detected_aggregate():
    cfg = DetectionConfig(flood_pkt_rate=5000,
                          flood_aggregate_pkt_rate=1000)
    det = AnomalyDetector(cfg)
    # 10 modest flows that individually stay under the per-flow bar but whose
    # smoothed sum crosses the aggregate bar
    flows = [_flow("10.0.0.9", f"10.0.0.{i}", 80, prate=150.0)
             for i in range(2, 12)]
    alerts = []
    for _ in range(cfg.flood_sustained_windows):
        alerts = det.process(flows)
    flood = [a for a in alerts if a.category == "FLOOD"]
    assert flood and flood[0].evidence["trigger"] == "aggregate"
    print("PASS test_flood_detected_aggregate:", flood[0].description)


def test_flood_hysteresis_ignores_single_spike():
    # a single brief cycle just over the per-flow threshold must NOT raise a
    # flood, because the sustained-window hysteresis is not satisfied and the
    # smoothed rate falls straight back below threshold
    cfg = DetectionConfig(flood_pkt_rate=500, flood_aggregate_pkt_rate=1000,
                          flood_sustained_windows=3)
    det = AnomalyDetector(cfg)
    normal = [_flow("10.0.0.5", "10.0.0.2", 80, prate=50.0)]
    spike = [_flow("10.0.0.5", "10.0.0.2", 80, prate=600.0)]
    alerts = []
    alerts += det.process(normal)
    alerts += det.process(spike)     # single transient over-threshold cycle
    alerts += det.process(normal)
    alerts += det.process(normal)
    assert not any(a.category == "FLOOD" for a in alerts), \
        "a single transient spike should not trigger a flood alert"
    print("PASS test_flood_hysteresis_ignores_single_spike")


def test_flood_ema_smooths_toward_rate():
    # the smoothed EMA should climb toward the true rate over successive polls
    cfg = DetectionConfig(flood_pkt_rate=500, ema_alpha=0.4,
                          flood_sustained_windows=3)
    det = AnomalyDetector(cfg)
    flow = [_flow("10.0.0.7", "10.0.0.2", 80, prate=1000.0)]
    for _ in range(cfg.flood_sustained_windows):
        det.process(flow)
    ema = det.source_metrics()["10.0.0.7"]["ema_pkt_rate"]
    assert 500.0 < ema <= 1000.0, f"EMA did not converge sensibly: {ema}"
    print(f"PASS test_flood_ema_smooths_toward_rate: EMA={ema:.0f} pkt/s")


def test_volume_anomaly_after_baseline():
    cfg = DetectionConfig(baseline_min_samples=5, volume_multiplier=8,
                          volume_abs_floor_bps=1_000_000,
                          alert_cooldown_seconds=0)
    det = AnomalyDetector(cfg)
    # establish a calm baseline of ~0.2 MB/s over several cycles
    for _ in range(6):
        det.process([_flow("10.0.0.1", "10.0.0.2", 80, brate=200_000.0)])
    # now a spike to 5 MB/s (25x baseline)
    alerts = det.process([_flow("10.0.0.1", "10.0.0.2", 80,
                                brate=5_000_000.0)])
    assert any(a.category == "VOLUME" for a in alerts), "volume spike missed"
    vol = next(a for a in alerts if a.category == "VOLUME")
    assert vol.evidence["ratio"] >= 8
    print("PASS test_volume_anomaly_after_baseline:", vol.description)


def test_cooldown_suppresses_duplicates():
    cfg = DetectionConfig(flood_pkt_rate=500, alert_cooldown_seconds=60,
                          flood_sustained_windows=1)
    det = AnomalyDetector(cfg)
    f = [_flow("10.0.0.9", "10.0.0.2", 80, prate=9000.0)]
    first = det.process(f)
    second = det.process(f)   # immediately again -> should be suppressed
    assert any(a.category == "FLOOD" for a in first)
    assert not any(a.category == "FLOOD" for a in second), \
        "cooldown failed to suppress duplicate flood alert"
    print("PASS test_cooldown_suppresses_duplicates")


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
    print(f"\n{passed}/{len(tests)} detection tests passed.")


if __name__ == "__main__":
    _run_all()

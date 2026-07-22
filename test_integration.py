"""
test_integration.py
===================
End-to-end test of the controller's statistics -> detection -> alert -> store
pipeline, WITHOUT requiring root privileges, Open vSwitch, or Mininet.

Full network emulation (Mininet + OVS + real OpenFlow handshakes) needs root
and kernel networking that isn't available in every CI sandbox. This test
instead drives the *real* SDNMonitor flow-stats handler with synthetic
OpenFlow flow-stats reply objects, so every layer the production controller
uses - the delta/rate computation, the AnomalyDetector, the shared STORE, and
the mitigation trigger - is exercised exactly as it is in the live system.

The Mininet path is validated separately by tests/run_mininet_test.sh on a host
that has Mininet installed.

Run:
    python3 tests/test_integration.py
"""

import os
import sys
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "controller"))

# Import the controller module (this also installs the ryu->os_ken shim and
# puts controller/ on sys.path). We then import `store` as the SAME top-level
# module the controller writes to, so the test observes the controller's data.
import controller.sdn_monitor as mon   # noqa: E402
from store import STORE                 # noqa: E402


# --------------------------------------------------------------------------- #
#  Minimal fakes for the OpenFlow objects the handler touches
# --------------------------------------------------------------------------- #
class FakeMatch(dict):
    """OFPMatch behaves like a dict of field->value with a .get()."""


class FakeFlowStat:
    def __init__(self, match, packet_count, byte_count, duration_sec=1.0):
        self.match = match
        self.packet_count = packet_count
        self.byte_count = byte_count
        self.duration_sec = duration_sec


class FakeDatapath:
    def __init__(self, dpid=1):
        self.id = dpid
        self.sent = []
        # give it just enough ofproto/parser surface for _mitigate/_add_flow
        self.ofproto = types.SimpleNamespace(
            OFPIT_APPLY_ACTIONS=4, OFPP_ANY=0xffffffff, OFP_NO_BUFFER=0xffffffff)

        parser = types.SimpleNamespace()
        parser.OFPMatch = lambda **kw: FakeMatch(kw)
        parser.OFPActionOutput = lambda *a, **k: ("out", a, k)
        parser.OFPInstructionActions = lambda *a, **k: ("inst", a, k)

        def _flowmod(**kw):
            return ("flowmod", kw)
        parser.OFPFlowMod = _flowmod
        parser.OFPFlowStatsRequest = lambda dp: ("flowreq", dp)
        parser.OFPPortStatsRequest = lambda dp, a, b: ("portreq",)
        self.ofproto_parser = parser

    def send_msg(self, m):
        self.sent.append(m)


class FakeMsg:
    def __init__(self, datapath, body):
        self.datapath = datapath
        self.body = body


class FakeEvent:
    def __init__(self, msg):
        self.msg = msg


def _make_controller():
    # Build an SDNMonitor without running RyuApp.__init__'s hub machinery.
    c = mon.SDNMonitor.__new__(mon.SDNMonitor)
    c.mac_to_port = {}
    c.datapaths = {}
    c.detector = mon.AnomalyDetector(mon.DetectionConfig())
    c._prev_flow_counters = {}
    c._mitigated = {}

    # a no-op logger
    c.logger = types.SimpleNamespace(
        info=lambda *a, **k: None,
        warning=lambda *a, **k: None,
        error=lambda *a, **k: None)
    return c


def _tcp_match(src, dst, dport, sport=40000):
    return FakeMatch({
        "ipv4_src": src, "ipv4_dst": dst, "ip_proto": 6,
        "tcp_dst": dport, "tcp_src": sport,
    })


# --------------------------------------------------------------------------- #
#  Tests
# --------------------------------------------------------------------------- #
def test_rate_computation_and_no_false_alert():
    c = _make_controller()
    dp = FakeDatapath(1)
    c.datapaths[dp.id] = dp

    # First poll: three normal flows, cumulative counters, no prior sample.
    body1 = [
        FakeFlowStat(_tcp_match("10.0.0.1", "10.0.0.4", 8000),
                     packet_count=100, byte_count=100_000),
        FakeFlowStat(_tcp_match("10.0.0.1", "10.0.0.4", 8001),
                     packet_count=120, byte_count=110_000),
    ]
    c._flow_stats_reply(FakeEvent(FakeMsg(dp, body1)))
    # after first poll there should be no alerts (rates are zero, no baseline)
    assert len(STORE.alerts()) == 0
    # flow stats made it into the store
    flows = STORE.flow_stats().get(1, [])
    assert len(flows) == 2
    print("PASS test_rate_computation_and_no_false_alert")


def test_end_to_end_flood_alert_and_mitigation():
    c = _make_controller()
    dp = FakeDatapath(1)
    c.datapaths[dp.id] = dp
    mon.ENABLE_MITIGATION = True

    m = _tcp_match("10.0.0.9", "10.0.0.4", 80)
    # poll 1 establishes the counter baseline for this flow
    c._flow_stats_reply(FakeEvent(FakeMsg(dp, [
        FakeFlowStat(m, packet_count=0, byte_count=0)])))

    # Drive several sustained high-rate polls so the EMA + hysteresis gate is
    # satisfied. Each poll adds 6000 packets over ~1s -> ~6000 pkt/s.
    key = (1, "10.0.0.9", "10.0.0.4", 40000, 80, 6)
    total = 0
    for i in range(1, 6):
        pc, bc, _ = c._prev_flow_counters[key]
        c._prev_flow_counters[key] = (pc, bc, time.time() - 1.0)
        total = 6000 * i
        c._flow_stats_reply(FakeEvent(FakeMsg(dp, [
            FakeFlowStat(m, packet_count=total, byte_count=total * 500)])))
        if "10.0.0.9" in c._mitigated:
            break

    alerts = STORE.alerts()
    assert any(a["category"] == "FLOOD" for a in alerts), \
        f"no FLOOD alert; got {[a['category'] for a in alerts]}"
    # HIGH severity flood should have triggered a mitigation drop rule
    assert "10.0.0.9" in c._mitigated, "attacker was not mitigated"
    # and a drop flowmod (instructions == []) should have been sent to the switch
    flowmods = [s for s in dp.sent if isinstance(s, tuple) and s[0] == "flowmod"]
    assert flowmods, "no flow-mod sent for mitigation"
    print("PASS test_end_to_end_flood_alert_and_mitigation "
          f"({len(alerts)} alert(s), attacker blocked)")


def test_end_to_end_port_scan_alert():
    c = _make_controller()
    dp = FakeDatapath(2)
    c.datapaths[dp.id] = dp

    # 20 flows from one source to 20 different ports, tiny packet counts
    body = [FakeFlowStat(_tcp_match("10.0.0.1", "10.0.0.4", 1000 + i),
                         packet_count=1, byte_count=64) for i in range(20)]
    c._flow_stats_reply(FakeEvent(FakeMsg(dp, body)))

    assert any(a["category"] == "PORT_SCAN" for a in STORE.alerts()), \
        "port scan not detected end-to-end"
    print("PASS test_end_to_end_port_scan_alert")


def test_learned_flow_match_is_ip_aware():
    """
    Regression test.

    The statistics poller can only reason about flows whose match exposes
    ipv4_src/ipv4_dst. If the learning switch installed MAC-only rules, every
    flow would be silently discarded and the dashboard would sit at zero
    flows and zero alerts while traffic was clearly flowing. This asserts the
    learned match carries the IP and transport fields the detector needs.
    """
    from ryu.lib.packet import packet, ethernet, ether_types, ipv4, tcp, udp
    from ryu.ofproto import ofproto_v1_3_parser as parser
    from controller.sdn_monitor import SDNMonitor

    def build(layers):
        p = packet.Packet()
        for layer in layers:
            p.add_protocol(layer)
        p.serialize()
        return packet.Packet(p.data)

    eth = ethernet.ethernet(dst="00:00:00:00:00:04",
                            src="00:00:00:00:00:03",
                            ethertype=ether_types.ETH_TYPE_IP)

    # TCP flow
    pk = build([eth, ipv4.ipv4(src="10.0.0.3", dst="10.0.0.4", proto=6),
                tcp.tcp(src_port=40000, dst_port=80)])
    m = dict(SDNMonitor._build_match(parser, 1, "00:00:00:00:00:03",
                                     "00:00:00:00:00:04", pk).items())
    for field in ("ipv4_src", "ipv4_dst", "ip_proto", "tcp_src", "tcp_dst"):
        assert field in m, f"TCP match missing {field}: {sorted(m)}"
    assert m["ipv4_src"] == "10.0.0.3" and m["tcp_dst"] == 80

    # UDP flow (the flood case)
    pk = build([ethernet.ethernet(dst="00:00:00:00:00:04",
                                  src="00:00:00:00:00:03",
                                  ethertype=ether_types.ETH_TYPE_IP),
                ipv4.ipv4(src="10.0.0.3", dst="10.0.0.4", proto=17),
                udp.udp(src_port=50000, dst_port=80)])
    m = dict(SDNMonitor._build_match(parser, 1, "00:00:00:00:00:03",
                                     "00:00:00:00:00:04", pk).items())
    for field in ("ipv4_src", "ipv4_dst", "ip_proto", "udp_src", "udp_dst"):
        assert field in m, f"UDP match missing {field}: {sorted(m)}"

    # non-IP traffic (e.g. ARP) falls back to plain L2 matching
    pk = build([ethernet.ethernet(dst="ff:ff:ff:ff:ff:ff",
                                  src="00:00:00:00:00:03", ethertype=0x0806)])
    m = dict(SDNMonitor._build_match(parser, 1, "00:00:00:00:00:03",
                                     "ff:ff:ff:ff:ff:ff", pk).items())
    assert "ipv4_src" not in m and "eth_dst" in m

    print("PASS test_learned_flow_match_is_ip_aware "
          "(learned flows carry IPv4 + transport fields)")


def _run_all():
    tests = [test_rate_computation_and_no_false_alert,
             test_end_to_end_flood_alert_and_mitigation,
             test_end_to_end_port_scan_alert,
             test_learned_flow_match_is_ip_aware]
    for t in tests:
        t()
    print(f"\n{len(tests)}/{len(tests)} integration tests passed.")


if __name__ == "__main__":
    _run_all()

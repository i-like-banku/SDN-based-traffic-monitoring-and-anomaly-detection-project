"""
sdn_monitor.py
==============
SDN traffic-monitoring / anomaly-detection controller application.

Runs on the Ryu SDN framework (or the API-compatible os-ken fork). It does
four things:

  1. Acts as an OpenFlow 1.3 L2 learning switch so the emulated network has
     working connectivity.
  2. Periodically polls every connected switch for per-flow and per-port
     statistics using OFPFlowStatsRequest / OFPPortStatsRequest.
  3. Converts those raw statistics into normalised FlowRecords (computing
     per-interval packet/byte *rates* as deltas between successive polls) and
     feeds them to the AnomalyDetector engine.
  4. On each alert it logs the event, appends it to a shared alert store, and -
     when mitigation is enabled - installs a temporary drop rule against the
     offending source so the attack is contained automatically.

A companion WSGI application (rest.py) exposes the collected statistics and
alerts over HTTP so the dashboard can display them live.

Launch (classic Ryu):
    ryu-manager controller/sdn_monitor.py controller/rest.py

Launch (os-ken, or where ryu-manager is unavailable):
    python3 run_controller.py controller.sdn_monitor
"""

from __future__ import annotations

import os
import sys
import csv
import time

# Ensure this directory is importable as a top-level location so that
# `from store import STORE` and `from detection import ...` resolve to the
# same single module objects regardless of how the app is launched
# (ryu-manager by file path, python3 run_controller.py, or the test harness).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- Ryu / os-ken import shim ------------------------------------------------
# The code is written against the `ryu.*` API. On a classic Ryu install these
# import directly. Where only the maintained os-ken fork is present, importing
# `ryu` fails; we transparently alias `ryu.*` onto `os_ken.*` so the identical
# application code runs unmodified on both.
try:  # pragma: no cover - exercised implicitly by whichever stack is present
    import ryu  # noqa: F401
except ImportError:  # pragma: no cover
    import importlib
    import importlib.abc
    import importlib.util
    import sys

    class _RyuOsKenFinder(importlib.abc.MetaPathFinder,
                          importlib.abc.Loader):
        def find_spec(self, name, path, target=None):
            if name == "ryu" or name.startswith("ryu."):
                osk = "os_ken" + name[3:]
                try:
                    importlib.import_module(osk)
                except ImportError:
                    return None
                return importlib.util.spec_from_loader(name, self)
            return None

        def create_module(self, spec):
            mod = importlib.import_module("os_ken" + spec.name[3:])
            sys.modules[spec.name] = mod
            return mod

        def exec_module(self, module):
            pass

    sys.meta_path.insert(0, _RyuOsKenFinder())

from ryu.base import app_manager                       # noqa: E402
from ryu.controller import ofp_event                   # noqa: E402
from ryu.controller.handler import (                   # noqa: E402
    CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER, set_ev_cls)
from ryu.ofproto import ofproto_v1_3                   # noqa: E402
from ryu.lib import hub                                # noqa: E402
from ryu.lib.packet import (                           # noqa: E402
    packet, ethernet, ether_types)

from detection import (AnomalyDetector, DetectionConfig,  # noqa: E402
                       FlowRecord)
from store import STORE                                # noqa: E402


# Toggle automatic mitigation (installing drop rules against attackers).
ENABLE_MITIGATION = True
# How often (seconds) to poll switches for statistics. A shorter interval means
# faster detection at a modest cost in controller/switch chatter.
POLL_INTERVAL = 2
# An auto-installed drop rule uses an IDLE timeout: it stays on the switch while
# attack traffic keeps matching it and removes itself this many seconds after
# the attack stops, giving automatic recovery without a fixed cut-off.
MITIGATION_IDLE_TIMEOUT = 30
# Directory for CSV logs used by analysis/evaluate.py and analysis/plot_stats.py
LOG_DIR = os.environ.get("SDN_LOG_DIR",
                         os.path.join(os.path.dirname(os.path.dirname(
                             os.path.abspath(__file__))), "logs"))


def _proto_name(ip_proto: int) -> str:
    return {1: "ICMP", 6: "TCP", 17: "UDP"}.get(ip_proto, "OTHER")


# Ryu's application base class is RyuApp; the os-ken fork renamed it OSKenApp.
# Resolve whichever is present so the same class definition works on both.
AppBase = getattr(app_manager, "RyuApp", None) or app_manager.OSKenApp


class SDNMonitor(AppBase):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SDNMonitor, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.detector = AnomalyDetector(DetectionConfig())
        # remember previous cumulative counters per flow key so we can turn
        # them into per-interval rates: key -> (packets, bytes, timestamp)
        self._prev_flow_counters = {}
        # sources we have already installed a mitigation rule for (with expiry)
        self._mitigated = {}
        self._init_csv_logs()
        self.monitor_thread = hub.spawn(self._monitor_loop)
        self.logger.info("SDNMonitor started (mitigation=%s, poll=%ss, logs=%s)",
                         ENABLE_MITIGATION, POLL_INTERVAL, LOG_DIR)

    # ------------------------------------------------------------------ #
    #  Switch lifecycle
    # ------------------------------------------------------------------ #
    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        dp = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if dp.id not in self.datapaths:
                self.datapaths[dp.id] = dp
                self.logger.info("switch %016x connected", dp.id)
        elif ev.state == DEAD_DISPATCHER:
            if dp.id in self.datapaths:
                del self.datapaths[dp.id]
                self.logger.info("switch %016x disconnected", dp.id)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        dp = ev.msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        # table-miss -> send to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER,
                                          ofp.OFPCML_NO_BUFFER)]
        self._add_flow(dp, 0, match, actions)

    def _add_flow(self, dp, priority, match, actions,
                  hard_timeout=0, idle_timeout=0):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=priority, match=match,
                                instructions=inst, hard_timeout=hard_timeout,
                                idle_timeout=idle_timeout)
        dp.send_msg(mod)

    # ------------------------------------------------------------------ #
    #  L2 learning switch
    # ------------------------------------------------------------------ #
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst, src = eth.dst, eth.src
        dpid = dp.id
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        out_port = self.mac_to_port[dpid].get(dst, ofp.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]

        # install a flow so subsequent packets are switched in hardware and
        # start accruing the statistics we later poll
        if out_port != ofp.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            self._add_flow(dp, 1, match, actions, idle_timeout=30)

        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        out = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        dp.send_msg(out)

    # ------------------------------------------------------------------ #
    #  Statistics polling loop
    # ------------------------------------------------------------------ #
    def _monitor_loop(self):
        while True:
            for dp in list(self.datapaths.values()):
                self._request_stats(dp)
            self._expire_mitigations()
            hub.sleep(POLL_INTERVAL)

    def _request_stats(self, dp):
        parser = dp.ofproto_parser
        dp.send_msg(parser.OFPFlowStatsRequest(dp))
        dp.send_msg(parser.OFPPortStatsRequest(dp, 0, dp.ofproto.OFPP_ANY))

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply(self, ev):
        rows = []
        for stat in ev.msg.body:
            rows.append({
                "dpid": ev.msg.datapath.id,
                "port": stat.port_no,
                "rx_packets": stat.rx_packets,
                "tx_packets": stat.tx_packets,
                "rx_bytes": stat.rx_bytes,
                "tx_bytes": stat.tx_bytes,
                "rx_errors": stat.rx_errors,
                "tx_errors": stat.tx_errors,
            })
        STORE.update_port_stats(ev.msg.datapath.id, rows)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply(self, ev):
        now = time.time()
        dp = ev.msg.datapath
        records = []
        raw_rows = []

        for stat in ev.msg.body:
            m = stat.match
            # only reason about IPv4 flows that carry the fields we need
            if "ipv4_src" not in m or "ipv4_dst" not in m:
                continue
            ip_proto = m.get("ip_proto", 0)
            proto = _proto_name(ip_proto)
            src_ip = m["ipv4_src"]
            dst_ip = m["ipv4_dst"]
            dst_port = m.get("tcp_dst", m.get("udp_dst", 0))
            src_port = m.get("tcp_src", m.get("udp_src", 0))

            key = (dp.id, src_ip, dst_ip, src_port, dst_port, ip_proto)
            prev = self._prev_flow_counters.get(key)
            self._prev_flow_counters[key] = (stat.packet_count,
                                             stat.byte_count, now)
            if prev is None:
                # first observation of this flow: no rate yet
                p_rate = b_rate = 0.0
            else:
                dt = max(now - prev[2], 1e-3)
                p_rate = max(stat.packet_count - prev[0], 0) / dt
                b_rate = max(stat.byte_count - prev[1], 0) / dt

            records.append(FlowRecord(
                src_ip=src_ip, dst_ip=dst_ip, src_port=src_port,
                dst_port=dst_port, protocol=proto,
                packet_count=stat.packet_count, byte_count=stat.byte_count,
                packet_rate=p_rate, byte_rate=b_rate,
                duration_sec=stat.duration_sec))

            raw_rows.append({
                "src_ip": src_ip, "dst_ip": dst_ip,
                "src_port": src_port, "dst_port": dst_port,
                "protocol": proto, "packets": stat.packet_count,
                "bytes": stat.byte_count, "pkt_rate": round(p_rate, 1),
                "byte_rate": round(b_rate, 1),
            })

        STORE.update_flow_stats(dp.id, raw_rows)

        # run detection on this cycle's flow records
        alerts = self.detector.process(records)
        # log per-source smoothed rates for offline analysis/plotting
        self._log_rates(records)
        for alert in alerts:
            self.logger.warning("[ALERT] %s | %s", alert.category,
                               alert.description)
            STORE.add_alert(alert.as_dict())
            self._log_event("ALERT", alert.src_ip, alert.category,
                            alert.severity, alert.description)
            if ENABLE_MITIGATION and alert.severity == "HIGH":
                self._mitigate(alert.src_ip)

        STORE.set_engine_snapshot(self.detector.snapshot())

    # ------------------------------------------------------------------ #
    #  CSV logging (for analysis/evaluate.py and analysis/plot_stats.py)
    # ------------------------------------------------------------------ #
    def _init_csv_logs(self):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            self._rates_path = os.path.join(LOG_DIR, "rates.csv")
            self._events_path = os.path.join(LOG_DIR, "events.csv")
            with open(self._rates_path, "w", newline="") as f:
                csv.writer(f).writerow(
                    ["timestamp", "src_ip", "agg_pkt_rate", "ema_pkt_rate",
                     "flood_streak", "agg_byte_rate"])
            with open(self._events_path, "w", newline="") as f:
                csv.writer(f).writerow(
                    ["timestamp", "iso_time", "event", "src_ip", "category",
                     "severity", "detail"])
            self._csv_ok = True
        except Exception as exc:  # logging must never break the controller
            self.logger.warning("CSV logging disabled: %s", exc)
            self._csv_ok = False

    def _log_event(self, event, src_ip, category="", severity="", detail=""):
        if not getattr(self, "_csv_ok", False):
            return
        now = time.time()
        try:
            with open(self._events_path, "a", newline="") as f:
                csv.writer(f).writerow([
                    f"{now:.3f}",
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
                    event, src_ip, category, severity, detail])
        except Exception:
            pass

    def _log_rates(self, records):
        if not getattr(self, "_csv_ok", False):
            return
        now = time.time()
        # aggregate this cycle's rates per source, then attach the detector's
        # smoothed EMA and hysteresis streak for that source
        agg = {}
        for r in records:
            a = agg.setdefault(r.src_ip, [0.0, 0.0])
            a[0] += r.packet_rate
            a[1] += r.byte_rate
        metrics = self.detector.source_metrics()
        try:
            with open(self._rates_path, "a", newline="") as f:
                w = csv.writer(f)
                for src, (pr, br) in agg.items():
                    m = metrics.get(src, {})
                    w.writerow([f"{now:.3f}", src, round(pr, 1),
                                m.get("ema_pkt_rate", 0.0),
                                m.get("flood_streak", 0), round(br, 1)])
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  Automatic mitigation
    # ------------------------------------------------------------------ #
    def _mitigate(self, src_ip: str):
        if src_ip in self._mitigated:
            return
        expiry = time.time() + MITIGATION_IDLE_TIMEOUT
        self._mitigated[src_ip] = expiry
        for dp in list(self.datapaths.values()):
            parser = dp.ofproto_parser
            # high-priority match on the source IP with no actions == drop.
            # An IDLE timeout keeps the rule alive while attack packets keep
            # matching it and removes it MITIGATION_IDLE_TIMEOUT seconds after
            # the attack stops, giving automatic recovery.
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,
                                    ipv4_src=src_ip)
            self._add_flow(dp, 100, match, actions=[],
                           idle_timeout=MITIGATION_IDLE_TIMEOUT)
        self.logger.warning("[MITIGATION] installed drop rule for %s "
                            "(idle timeout %ss)", src_ip,
                            MITIGATION_IDLE_TIMEOUT)
        STORE.add_mitigation({"src_ip": src_ip, "expires": expiry,
                              "time_str": time.strftime("%H:%M:%S")})
        self._log_event("MITIGATION", src_ip, "FLOOD", "HIGH",
                        f"drop rule installed (idle_timeout={MITIGATION_IDLE_TIMEOUT}s)")

    def _expire_mitigations(self):
        now = time.time()
        for ip in [ip for ip, exp in self._mitigated.items() if exp <= now]:
            del self._mitigated[ip]
            self._log_event("RECOVERY", ip, "FLOOD", "",
                            "mitigation expired, source unblocked")

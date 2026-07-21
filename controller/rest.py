"""
rest.py
=======
REST API + live dashboard for the SDN traffic-monitoring system.

Registered as a second application alongside sdn_monitor.py:

    ryu-manager controller/sdn_monitor.py controller/rest.py
        or
    python3 run_controller.py controller.sdn_monitor controller.rest

Rather than depend on ryu.app.wsgi (which the slim os-ken fork does not ship),
this app runs its own lightweight WSGI server on an eventlet green thread via
ryu.lib.hub. eventlet ships with both Ryu and os-ken, so the identical code
runs on either stack. It serves, on http://0.0.0.0:8080 by default:

    GET /monitor/summary       -> counts of switches/flows/alerts/mitigations
    GET /monitor/flows         -> per-switch flow statistics
    GET /monitor/ports         -> per-switch port statistics
    GET /monitor/alerts        -> most recent anomaly alerts
    GET /monitor/mitigations   -> auto-installed drop rules
    GET /monitor/dashboard     -> a self-contained live HTML dashboard
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- Ryu / os-ken import shim (mirrors sdn_monitor.py) ----------------------
try:
    import ryu  # noqa: F401
except ImportError:  # pragma: no cover
    import importlib
    import importlib.abc
    import importlib.util

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

from ryu.base import app_manager   # noqa: E402
from ryu.lib import hub            # noqa: E402
import eventlet                    # noqa: E402
from eventlet import wsgi          # noqa: E402

from store import STORE            # noqa: E402


REST_HOST = "0.0.0.0"
REST_PORT = 8080

AppBase = getattr(app_manager, "RyuApp", None) or app_manager.OSKenApp


class MonitorRestApp(AppBase):
    def __init__(self, *args, **kwargs):
        super(MonitorRestApp, self).__init__(*args, **kwargs)
        self.logger.info("REST dashboard on http://%s:%s/monitor/dashboard",
                         REST_HOST, REST_PORT)
        hub.spawn(self._serve)

    def _serve(self):
        listener = eventlet.listen((REST_HOST, REST_PORT))
        wsgi.server(listener, _application, log_output=False)


# --------------------------------------------------------------------------- #
#  WSGI application
# --------------------------------------------------------------------------- #
def _json_response(start_response, obj, status="200 OK"):
    body = json.dumps(obj).encode("utf-8")
    start_response(status, [("Content-Type", "application/json"),
                            ("Content-Length", str(len(body))),
                            ("Access-Control-Allow-Origin", "*")])
    return [body]


def _html_response(start_response, html):
    body = html.encode("utf-8")
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"),
                              ("Content-Length", str(len(body)))])
    return [body]


def _application(environ, start_response):
    path = environ.get("PATH_INFO", "")
    if path in ("/", "/monitor", "/monitor/dashboard"):
        return _html_response(start_response, _DASHBOARD_HTML)
    if path == "/monitor/summary":
        return _json_response(start_response, STORE.summary())
    if path == "/monitor/flows":
        return _json_response(start_response, STORE.flow_stats())
    if path == "/monitor/ports":
        return _json_response(start_response, STORE.port_stats())
    if path == "/monitor/alerts":
        return _json_response(start_response, STORE.alerts())
    if path == "/monitor/mitigations":
        return _json_response(start_response, STORE.mitigations())
    return _json_response(start_response, {"error": "not found"},
                          status="404 Not Found")


_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>SDN Traffic Monitor</title>
<style>
  :root { --bg:#0f172a; --panel:#1e293b; --line:#334155; --txt:#e2e8f0;
          --muted:#94a3b8; --hi:#ef4444; --med:#f59e0b; --ok:#22c55e; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:system-ui,Segoe UI,Roboto,sans-serif;
         background:var(--bg); color:var(--txt); }
  header { padding:16px 24px; border-bottom:1px solid var(--line);
           display:flex; align-items:center; gap:16px; }
  header h1 { font-size:18px; margin:0; font-weight:650; }
  .dot { width:10px; height:10px; border-radius:50%; background:var(--ok);
         box-shadow:0 0 8px var(--ok); }
  .cards { display:grid; grid-template-columns:repeat(4,1fr); gap:16px;
           padding:20px 24px; }
  .card { background:var(--panel); border:1px solid var(--line);
          border-radius:10px; padding:16px; }
  .card .n { font-size:28px; font-weight:700; }
  .card .l { color:var(--muted); font-size:12px; text-transform:uppercase;
             letter-spacing:.05em; }
  .wrap { display:grid; grid-template-columns:1fr 1fr; gap:16px;
          padding:0 24px 24px; }
  .box { background:var(--panel); border:1px solid var(--line);
         border-radius:10px; overflow:hidden; }
  .box h2 { font-size:13px; margin:0; padding:12px 16px;
            border-bottom:1px solid var(--line); color:var(--muted);
            text-transform:uppercase; letter-spacing:.05em; }
  table { width:100%; border-collapse:collapse; font-size:12px; }
  th,td { text-align:left; padding:7px 16px; border-bottom:1px solid #26324a; }
  th { color:var(--muted); font-weight:600; }
  .sev-HIGH { color:var(--hi); font-weight:700; }
  .sev-MEDIUM { color:var(--med); font-weight:700; }
  .sev-LOW { color:var(--muted); }
  .scroll { max-height:340px; overflow:auto; }
  .empty { padding:16px; color:var(--muted); font-size:12px; }
</style>
</head>
<body>
<header>
  <span class="dot"></span>
  <h1>SDN Traffic Monitor &amp; Anomaly Detection</h1>
  <span id="clock" style="color:var(--muted);font-size:12px;"></span>
</header>

<div class="cards">
  <div class="card"><div class="n" id="c-switches">0</div><div class="l">Switches</div></div>
  <div class="card"><div class="n" id="c-flows">0</div><div class="l">Active flows</div></div>
  <div class="card"><div class="n" id="c-alerts" style="color:var(--hi)">0</div><div class="l">Alerts</div></div>
  <div class="card"><div class="n" id="c-mit" style="color:var(--med)">0</div><div class="l">Mitigations</div></div>
</div>

<div class="wrap">
  <div class="box">
    <h2>Recent Alerts</h2>
    <div class="scroll"><table id="t-alerts">
      <thead><tr><th>Time</th><th>Category</th><th>Sev</th><th>Source</th><th>Detail</th></tr></thead>
      <tbody></tbody></table><div class="empty" id="e-alerts">No alerts yet.</div>
    </div>
  </div>
  <div class="box">
    <h2>Auto-Mitigations</h2>
    <div class="scroll"><table id="t-mit">
      <thead><tr><th>Time</th><th>Blocked source</th></tr></thead>
      <tbody></tbody></table><div class="empty" id="e-mit">None.</div>
    </div>
  </div>
  <div class="box" style="grid-column:1 / span 2;">
    <h2>Live Flows</h2>
    <div class="scroll"><table id="t-flows">
      <thead><tr><th>Switch</th><th>Src IP</th><th>Dst IP</th><th>Proto</th>
      <th>Dst port</th><th>Pkts</th><th>Pkt/s</th><th>Bytes</th><th>Byte/s</th></tr></thead>
      <tbody></tbody></table><div class="empty" id="e-flows">Waiting for flows.</div>
    </div>
  </div>
</div>

<script>
async function j(u){ const r = await fetch(u); return r.json(); }
function set(id,v){ document.getElementById(id).textContent = v; }
function show(eid,has){ document.getElementById(eid).style.display = has ? 'none':'block'; }

async function tick(){
  try{
    const s = await j('/monitor/summary');
    set('c-switches', s.switches||0); set('c-flows', s.active_flows||0);
    set('c-alerts', s.alerts||0); set('c-mit', s.mitigations||0);

    const alerts = await j('/monitor/alerts');
    const ab = document.querySelector('#t-alerts tbody'); ab.innerHTML='';
    alerts.forEach(a=>{ const tr=document.createElement('tr');
      tr.innerHTML = `<td>${a.time_str||''}</td><td>${a.category}</td>
        <td class="sev-${a.severity}">${a.severity}</td><td>${a.src_ip}</td>
        <td>${a.description}</td>`; ab.appendChild(tr); });
    show('e-alerts', alerts.length>0);

    const mit = await j('/monitor/mitigations');
    const mb = document.querySelector('#t-mit tbody'); mb.innerHTML='';
    mit.forEach(m=>{ const tr=document.createElement('tr');
      tr.innerHTML = `<td>${m.time_str||''}</td><td>${m.src_ip}</td>`;
      mb.appendChild(tr); });
    show('e-mit', mit.length>0);

    const flows = await j('/monitor/flows');
    const fb = document.querySelector('#t-flows tbody'); fb.innerHTML='';
    let n=0;
    Object.keys(flows).forEach(dp=>{ flows[dp].forEach(f=>{ n++;
      const tr=document.createElement('tr');
      tr.innerHTML = `<td>${dp}</td><td>${f.src_ip}</td><td>${f.dst_ip}</td>
        <td>${f.protocol}</td><td>${f.dst_port}</td><td>${f.packets}</td>
        <td>${f.pkt_rate}</td><td>${f.bytes}</td><td>${f.byte_rate}</td>`;
      fb.appendChild(tr); }); });
    show('e-flows', n>0);

    set('clock', new Date().toLocaleTimeString());
  }catch(e){ console.error(e); }
}
tick(); setInterval(tick, 3000);
</script>
</body>
</html>"""

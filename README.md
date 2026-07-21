# SDN Traffic Monitoring & Anomaly Detection

An SDN-based network intrusion-detection system built on the **Ryu** SDN
framework and **Mininet**. A controller application continuously polls
OpenFlow statistics from the switches, detects **port scans**, **floods/DoS**
and **traffic-volume anomalies** using an explainable statistical engine, and
can **automatically block** attackers by installing drop rules. A live web
dashboard shows flows, alerts, and mitigations in real time.

The code runs unmodified on classic **Ryu** and on the maintained **os-ken**
fork (it detects which is installed).

## Project layout

```
sdn_ids/
├── controller/
│   ├── detection.py      # explainable anomaly-detection engine (no SDN deps)
│   ├── sdn_monitor.py    # Ryu app: L2 switch + stats polling + detection + mitigation
│   ├── rest.py           # REST API + live HTML dashboard (self-contained WSGI)
│   └── store.py          # thread-safe shared store for stats/alerts
├── topology/
│   └── topology.py       # Mininet network: 3 switches, 6 hosts
├── traffic/
│   ├── server.py         # multi-port TCP sink (attack/traffic target)
│   ├── normal_traffic.py # benign background traffic generator
│   ├── port_scan.py      # port-scan attack simulation
│   └── flood.py          # UDP flood / DoS simulation
├── tests/
│   ├── test_detection.py     # unit tests for the engine (6 tests)
│   ├── test_integration.py   # end-to-end pipeline tests (3 tests)
│   └── run_mininet_test.sh   # full live scenario on a Mininet host
├── scripts/
│   └── demo_offline.py   # narrated offline demonstration
├── analysis/
│   ├── evaluate.py       # precision/recall/latency metrics from the CSV logs
│   ├── plot_stats.py     # packet-rate/EMA, event-timeline and action plots
│   └── simulate_run.py   # produce sample logs without Mininet (for the above)
├── logs/                 # CSV logs (rates.csv, events.csv) + generated plots
├── docs/
│   └── INSTALL_AND_TEST.md   # full setup + test walkthrough
├── run_controller.py     # launcher (needed when ryu-manager is unavailable)
└── requirements.txt
```

## Quick start

```bash
# offline checks (no root/Mininet needed)
python3 tests/test_detection.py
python3 tests/test_integration.py
python3 scripts/demo_offline.py

# live system (see docs/INSTALL_AND_TEST.md for full steps)
# terminal 1:
ryu-manager controller/sdn_monitor.py controller/rest.py     # or: python3 run_controller.py
# terminal 2:
sudo python3 topology/topology.py
# browser:
#   http://localhost:8080/monitor/dashboard
```

Full instructions, including how to install on a fresh server and run the
attack scenarios, are in **docs/INSTALL_AND_TEST.md**.

## How detection works (in brief)

Every few seconds the controller asks each switch for its per-flow and
per-port counters. It turns the raw cumulative counters into per-second
**rates** (by differencing successive polls) and feeds them to the engine,
which keeps a short rolling history per source host and checks three things:

1. **Port scan** — one source touching many distinct destination ports/hosts
   in a short window, each contact carrying very few packets.
2. **Flood / DoS** — a source whose packet rate far exceeds a threshold. The
   aggregate rate is smoothed with an Exponential Moving Average (EMA) and must
   stay over threshold for several consecutive polls (hysteresis) before an
   alert fires, which suppresses false alarms on brief spikes.
3. **Volume anomaly** — a source whose byte rate jumps to a large multiple of
   the baseline it previously established.

Each alert carries the evidence that triggered it, so decisions are
explainable rather than a black box. High-severity alerts trigger an automatic,
time-limited drop rule against the source.

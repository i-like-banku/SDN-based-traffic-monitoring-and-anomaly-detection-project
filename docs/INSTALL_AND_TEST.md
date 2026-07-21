# SDN Traffic Monitoring & Anomaly Detection — Install and Test Guide

This guide walks you through setting the system up on a Linux server and
running it, first as quick offline checks (no root, no Mininet) and then as a
full live demo (controller + Mininet + simulated attacks).

Everything here has been kept in plain, practical steps. If you follow it top
to bottom on a clean Ubuntu machine you will end up with a working SDN
intrusion-detection setup and a live dashboard in your browser.

---

## 0. What you are building

* A **Ryu SDN controller app** that watches an OpenFlow network, pulls
  statistics from the switches every few seconds, and raises alerts when it
  sees the fingerprints of three common attacks: **port scans**, **packet
  floods / DoS**, and **sudden traffic-volume spikes**. When it sees a
  high-severity attack it can automatically install a **drop rule** on the
  switches to block the attacker.
* A **Mininet virtual network** (3 switches, 6 hosts) that the controller
  manages, so you can generate normal traffic and launch test attacks safely
  inside a sandbox.
* A small **web dashboard** that shows live flows, alerts, and mitigations.

---

## 1. Recommended platform

Use **Ubuntu 20.04 LTS** (physical machine, VM, or WSL2). It ships with
Python 3.8, which the classic Ryu package installs against cleanly, and
Mininet is available straight from apt.

> **Why 20.04?** On Ubuntu 22.04/24.04 (Python 3.10+) the classic `ryu`
> package fails to build because of a setuptools incompatibility. If you must
> use a newer system, install **os-ken** instead of ryu (see 2b). The
> application code detects which one is present and runs on either without any
> changes.

You need about 2 GB RAM and 4 GB free disk for a comfortable setup.

---

## 2. Install the software

### 2a. Classic Ryu on Ubuntu 20.04 (recommended)

```bash
sudo apt update
sudo apt install -y python3 python3-pip mininet openvswitch-switch git

# Ryu needs an older setuptools to build; pin it inside a virtualenv
python3 -m venv ~/sdnenv
source ~/sdnenv/bin/activate
pip install --upgrade pip
pip install "setuptools<58" wheel
pip install ryu==4.34 eventlet==0.30.2
```

Verify Ryu is present:

```bash
ryu-manager --version
```

### 2b. os-ken alternative (Ubuntu 22.04/24.04 or if ryu won't install)

```bash
sudo apt update
sudo apt install -y python3 python3-pip mininet openvswitch-switch git
python3 -m venv ~/sdnenv
source ~/sdnenv/bin/activate
pip install --upgrade pip
pip install os-ken eventlet
```

With os-ken there is no `ryu-manager` command, so you start the controller
with the bundled launcher (`python3 run_controller.py`) shown below. The
application code is identical either way.

### 2c. Get the project

```bash
# copy/unzip the sdn_ids project folder onto the server, then:
cd sdn_ids
```

---

## 3. Quick offline checks (no root, no Mininet)

These confirm the detection logic works before you bring up the full network.
They run anywhere Python is installed.

```bash
source ~/sdnenv/bin/activate

# 1) unit tests for the detection engine
python3 tests/test_detection.py

# 2) end-to-end pipeline test (stats -> detection -> alert -> mitigation)
python3 tests/test_integration.py

# 3) a narrated demo you can watch
python3 scripts/demo_offline.py
```

Expected: `6/6 detection tests passed`, `3/3 integration tests passed`, and the
demo prints a normal-traffic phase followed by port-scan, flood, and volume
alerts.

---

## 4. Run the live system

You will need **three terminals** (all with `source ~/sdnenv/bin/activate`).

### Terminal 1 — start the controller

Classic Ryu:

```bash
cd sdn_ids
ryu-manager controller/sdn_monitor.py controller/rest.py
```

os-ken (or if you prefer the bundled launcher):

```bash
cd sdn_ids
python3 run_controller.py
```

You should see the controller start and print that the dashboard is available
at `http://localhost:8080/monitor/dashboard`. Leave this running.

### Terminal 2 — start the network

```bash
cd sdn_ids
sudo python3 topology/topology.py
```

This drops you at a `mininet>` prompt with 6 hosts (`h1`–`h6`, IPs
`10.0.0.1`–`10.0.0.6`) and 3 switches. Confirm connectivity:

```
mininet> pingall
```

Back in Terminal 1 you will see the switches connect and flows begin to be
polled.

### Open the dashboard

In a browser on the server (or via port-forward) open:

```
http://localhost:8080/monitor/dashboard
```

You will see live flow counts updating every few seconds.

### Terminal 3 — (optional) prepare the traffic sink

From the mininet prompt in Terminal 2 you can launch helpers on hosts. Start
the sink server on h4 so there is something to talk to:

```
mininet> h4 python3 traffic/server.py &
```

---

## 5. Generate traffic and attacks

Run these from the `mininet>` prompt in Terminal 2. Watch the dashboard and
Terminal 1 as you do.

**Normal traffic (should NOT alert):**

```
mininet> h1 python3 traffic/normal_traffic.py 10.0.0.4 30 &
```

**Port scan (should raise a PORT_SCAN alert):**

```
mininet> h2 python3 traffic/port_scan.py 10.0.0.4 1 1024
```

**Flood / DoS (should raise a HIGH FLOOD alert and auto-block h3):**

```
mininet> h3 python3 traffic/flood.py 10.0.0.4 80 15
```

After the flood, check the mitigations panel on the dashboard (or
`curl http://localhost:8080/monitor/mitigations`) — you should see `10.0.0.9`/
the attacker's address listed with a temporary drop rule. During the block,
`h3 ping 10.0.0.4` from the mininet prompt will fail until the rule expires.

---

## 6. One-command live test (on a Mininet host)

If you would rather run the whole scenario automatically:

```bash
sudo bash tests/run_mininet_test.sh
```

It starts the controller, builds the network, runs benign traffic then a scan
then a flood, prints the alerts it observed, and tears everything down. The
full controller log is left at `/tmp/sdn_controller.log`.

---

## 7. Inspecting results with the REST API

While the controller runs you can query it directly:

```bash
curl http://localhost:8080/monitor/summary       # counts
curl http://localhost:8080/monitor/flows         # live flow stats
curl http://localhost:8080/monitor/alerts        # anomaly alerts
curl http://localhost:8080/monitor/mitigations   # auto-installed drop rules
```

## 7b. Evaluation metrics and plots

While it runs, the controller writes two CSV logs to `logs/`: `rates.csv` (per
source, per poll: raw packet rate, smoothed EMA, hysteresis streak, byte rate)
and `events.csv` (alerts, mitigations, recoveries with timestamps). Two tools
turn these into quantitative results:

```bash
# precision / recall / F1 / latency / recovery for a known attacker + window
python3 analysis/evaluate.py --attacker 10.0.0.1 \
    --attack-start "14:03:10" --attack-end "14:04:05"

# or let it infer the attack window from the attacker's rate
python3 analysis/evaluate.py --attacker 10.0.0.1 --auto

# packet-rate vs EMA, event timeline and action-breakdown plots (-> logs/*.png)
python3 analysis/plot_stats.py --attacker 10.0.0.1 --threshold 1000
```

If you want to see the metrics and plots without setting up Mininet, generate a
sample run first (this drives the real detector through a scripted
benign → attack → benign timeline and writes the same CSV logs the controller
would):

```bash
python3 analysis/simulate_run.py
python3 analysis/evaluate.py --attacker 10.0.0.1 --auto
python3 analysis/plot_stats.py --attacker 10.0.0.1 --threshold 1000
```

---

## 8. Tuning the detector

All thresholds live in `controller/detection.py` in the `DetectionConfig`
class — for example how many distinct ports counts as a scan, or the packets
per second that counts as a flood. Edit those values and restart the
controller. Lower thresholds catch more but risk false positives; higher
thresholds are quieter but may miss slow attacks.

---

## 9. Shutting down

* In the mininet prompt: `quit`
* Stop the controller with `Ctrl-C` in Terminal 1.
* Clean up any leftover network state: `sudo mn -c`

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `ryu-manager: command not found` | You are on Python 3.10+. Use os-ken and `python3 run_controller.py` (2b). |
| Switches never connect in Terminal 1 | Make sure the controller started first, and that the topology uses `OpenFlow13` and controller port 6653. |
| Dashboard is blank | Give it 10–15 s after `pingall` so flows exist; check the controller is running. |
| `Cannot find required executable ovs-vsctl` | `sudo apt install openvswitch-switch` and `sudo service openvswitch-switch start`. |
| Port scan/flood not detected | Lower the relevant thresholds in `DetectionConfig`, or increase the attack intensity/duration. |
| Permission errors from Mininet | Mininet needs root — run the topology with `sudo`. |

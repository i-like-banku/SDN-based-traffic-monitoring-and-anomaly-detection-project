#!/usr/bin/env bash
#
# run_mininet_test.sh
# ===================
# Drives the full LIVE test on a real Linux server that has the controller
# stack + Mininet + Open vSwitch installed. It:
#
#   1. starts the Ryu/os-ken controller in the background,
#   2. builds the Mininet topology,
#   3. starts the traffic sink on h4,
#   4. runs benign traffic, then a port scan, then a flood,
#   5. leaves the controller log and dashboard for inspection,
#   6. tears everything down.
#
# Run as root from the project root:
#     sudo bash tests/run_mininet_test.sh
#
# NOTE: this script must run on a host with Mininet; it will not work inside a
# plain container without Open vSwitch and kernel networking. The offline test
# suite (tests/test_detection.py, tests/test_integration.py) covers the
# detection logic without those requirements.

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
CTL_LOG="/tmp/sdn_controller.log"

echo "[*] cleaning any previous mininet state"
mn -c >/dev/null 2>&1 || true

echo "[*] starting controller (log -> $CTL_LOG)"
$PY run_controller.py > "$CTL_LOG" 2>&1 &
CTL_PID=$!
sleep 5
echo "    controller PID $CTL_PID; dashboard: http://localhost:8080/monitor/dashboard"

cleanup() {
  echo "[*] tearing down"
  mn -c >/dev/null 2>&1 || true
  kill "$CTL_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "[*] building Mininet topology and running scenario"
# feed a scripted scenario into the mininet CLI via stdin
$PY topology/topology.py <<'SCENARIO'
h4 python3 traffic/server.py &
h1 python3 traffic/normal_traffic.py 10.0.0.4 8 &
sh sleep 10
h2 python3 traffic/port_scan.py 10.0.0.4 1 400
sh sleep 3
h3 python3 traffic/flood.py 10.0.0.4 80 12
sh sleep 5
quit
SCENARIO

echo
echo "[*] ===== controller alerts observed ====="
grep -i "ALERT\|MITIGATION" "$CTL_LOG" || echo "  (see $CTL_LOG for full log)"
echo
echo "[*] done. Full controller log at $CTL_LOG"

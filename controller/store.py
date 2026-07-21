"""
store.py
========
A small thread-safe in-memory store shared between the controller application
(which writes statistics and alerts) and the REST API (which reads them for the
dashboard). Kept intentionally simple - a process-local singleton guarded by a
lock - because both the controller and the WSGI app run inside the same
ryu-manager process and event loop.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List


class _Store:
    def __init__(self, max_alerts: int = 500):
        self._lock = threading.Lock()
        self._flow_stats: Dict[int, List[dict]] = {}
        self._port_stats: Dict[int, List[dict]] = {}
        self._alerts: deque = deque(maxlen=max_alerts)
        self._mitigations: deque = deque(maxlen=200)
        self._engine: dict = {}

    # --- writers (controller side) --------------------------------------- #
    def update_flow_stats(self, dpid: int, rows: List[dict]) -> None:
        with self._lock:
            self._flow_stats[dpid] = rows

    def update_port_stats(self, dpid: int, rows: List[dict]) -> None:
        with self._lock:
            self._port_stats[dpid] = rows

    def add_alert(self, alert: dict) -> None:
        with self._lock:
            self._alerts.appendleft(alert)

    def add_mitigation(self, mit: dict) -> None:
        with self._lock:
            self._mitigations.appendleft(mit)

    def set_engine_snapshot(self, snap: dict) -> None:
        with self._lock:
            self._engine = snap

    # --- readers (REST side) --------------------------------------------- #
    def flow_stats(self) -> Dict[int, List[dict]]:
        with self._lock:
            return {k: list(v) for k, v in self._flow_stats.items()}

    def port_stats(self) -> Dict[int, List[dict]]:
        with self._lock:
            return {k: list(v) for k, v in self._port_stats.items()}

    def alerts(self, limit: int = 100) -> List[dict]:
        with self._lock:
            return list(self._alerts)[:limit]

    def mitigations(self, limit: int = 100) -> List[dict]:
        with self._lock:
            return list(self._mitigations)[:limit]

    def engine(self) -> dict:
        with self._lock:
            return dict(self._engine)

    def summary(self) -> dict:
        with self._lock:
            n_flows = sum(len(v) for v in self._flow_stats.values())
            return {
                "switches": len(self._flow_stats),
                "active_flows": n_flows,
                "alerts": len(self._alerts),
                "mitigations": len(self._mitigations),
                "engine": dict(self._engine),
            }


# process-wide singleton
STORE = _Store()

#!/usr/bin/env python3
r"""
topology.py
===========
Mininet topology for the SDN traffic-monitoring / anomaly-detection project.

It builds a small but non-trivial network - two edge switches joined by a core
switch, with several hosts on each edge - and points every switch at a REMOTE
controller (the Ryu SDNMonitor app) using OpenFlow 1.3.

Layout:

        h1  h2  h3            h4  h5  h6
          \ | /                \ | /
           s1 ------- s3(core) ------- s2
                        |
                    (remote controller  127.0.0.1:6653)

Run (needs root, Mininet installed, controller already started):

    sudo python3 topology/topology.py

Then use the mininet CLI (pingall, iperf, etc.) or run the attack scripts in
traffic/ from another terminal via  h1 python3 ...  inside the CLI.
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

CONTROLLER_IP = "127.0.0.1"
CONTROLLER_PORT = 6653


def build():
    net = Mininet(controller=None, switch=OVSKernelSwitch,
                  link=TCLink, autoSetMacs=True)

    info("*** Adding remote controller\n")
    c0 = net.addController("c0", controller=RemoteController,
                           ip=CONTROLLER_IP, port=CONTROLLER_PORT)

    info("*** Adding switches (OpenFlow 1.3)\n")
    s1 = net.addSwitch("s1", protocols="OpenFlow13")
    s2 = net.addSwitch("s2", protocols="OpenFlow13")
    s3 = net.addSwitch("s3", protocols="OpenFlow13")  # core

    info("*** Adding hosts\n")
    hosts = []
    for i in range(1, 7):
        h = net.addHost(f"h{i}", ip=f"10.0.0.{i}/24")
        hosts.append(h)

    info("*** Wiring links\n")
    # edge s1: h1-h3 ; edge s2: h4-h6
    for h in hosts[:3]:
        net.addLink(h, s1, bw=100)
    for h in hosts[3:]:
        net.addLink(h, s2, bw=100)
    # core links (slightly constrained so floods are observable)
    net.addLink(s1, s3, bw=50)
    net.addLink(s2, s3, bw=50)

    info("*** Starting network\n")
    net.build()
    c0.start()
    for s in (s1, s2, s3):
        s.start([c0])

    info("*** Network ready. 6 hosts (10.0.0.1-6), 3 switches.\n")
    info("*** Try:  pingall   then run traffic/ scripts from another xterm.\n")
    CLI(net)
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    build()

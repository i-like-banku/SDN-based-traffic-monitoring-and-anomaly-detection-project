module.exports = function (H) {
  const { h1, h2, h3, p, bullet, num, code, table, figure, pageBreak, spacer } = H;
  const out = [];
  const add = (x) => { Array.isArray(x) ? out.push(...x) : out.push(x); };

  add(h1("CHAPTER FOUR: IMPLEMENTATION AND EVALUATION"));

  add(h2("4.1 Introduction"));
  add(p("This chapter describes how the design from Chapter Three was turned into a working system, and then how that system was tested and evaluated. It walks through the main pieces of the software, explaining what each does in everyday terms and showing the key parts of the code. It then presents the testing: how the virtual network was set up, how normal traffic and simulated attacks were generated, and what the system did in response. Finally it analyses the results, judging how well the system met its goals of detecting attacks accurately, avoiding false alarms, and responding quickly."));

  add(h2("4.2 Implementation Overview"));
  add(p("The system was built in Python on top of the Ryu SDN framework. It is made up of several parts that work together: the controller application that collects statistics and coordinates everything; the detection engine that analyses traffic; the shared store that holds the current picture; the dashboard and its programming interface; the virtual network built in Mininet; and a set of small tools that generate normal traffic and simulate attacks. The code is written so that it runs on both the classic Ryu framework and its maintained fork, os-ken, which keeps it usable on both older and newer systems."));
  add(p("The parts are kept separate and focused. In particular, the detection engine is written so that it does not depend on any SDN library at all: it simply takes traffic records and returns alerts. This separation was a deliberate design decision, and it paid off during development, because it meant the detection logic could be built and tested completely on its own, without needing to start a whole network every time. The controller then acts as the bridge between the live network and this self-contained engine."));

  add(h2("4.3 The Detection Engine"));
  add(p("The detection engine is the heart of the system. It receives a batch of flow records. This is one round of the network\u2019s current traffic, with each flow\u2019s rates already worked out. From this batch it returns any alerts it finds. It keeps a short memory for each source so that it can spot patterns that only become clear over time, such as a scan spread across several seconds or a sudden jump above a source\u2019s normal level."));
  add(p("The settings that define an attack are all gathered in one place, so the engine can be tuned without touching its logic:"));
  add(code("class DetectionConfig:"));
  add(code("    scan_distinct_targets   = 15     # ports/hosts that mark a scan"));
  add(code("    scan_window_seconds     = 10.0   # over this time window"));
  add(code("    scan_max_pkts_per_flow  = 3.0    # scans send few packets each"));
  add(code("    flood_pkt_rate          = 500.0  # pkt/s for a single-flow flood"));
  add(code("    flood_aggregate_pkt_rate= 1000.0 # pkt/s across all a source's flows"));
  add(code("    ema_alpha               = 0.4    # smoothing factor for the flood rate"));
  add(code("    flood_sustained_windows = 3      # consecutive over-threshold polls"));
  add(code("    volume_multiplier       = 8.0    # x baseline = volume anomaly"));
  add(code("    alert_cooldown_seconds  = 15.0   # avoid repeating the same alert"));
  add(p("The port-scan check counts how many distinct destinations a source has touched within a sliding time window, and fires only if that count is high and the average traffic to each destination is tiny, the classic scan signature of many contacts carrying almost no data:"));
  add(code("distinct = number of distinct (dst_ip, dst_port) this source touched"));
  add(code("avg_pkts = average packets per flow this cycle"));
  add(code("if distinct >= scan_distinct_targets and avg_pkts <= scan_max_pkts_per_flow:"));
  add(code("    raise PORT_SCAN alert with the evidence"));
  add(p("The flood check looks at packet rates, but it does two extra things to avoid crying wolf at every brief spike. First, instead of judging the raw per-poll rate, it smooths each source\u2019s aggregate packet rate with an Exponential Moving Average (EMA), a running average that gives more weight to recent readings while still remembering the recent past. This filters out the jitter that normal traffic produces. Second, it applies hysteresis: the smoothed rate must stay above the threshold for several consecutive polling cycles (the sustained-window requirement) before an alert is raised. A one-off burst that falls straight back to normal therefore never triggers a false alarm. When either a single flow crosses the per-flow threshold or the smoothed aggregate crosses the aggregate threshold, and that condition holds for the required number of windows, the alert fires. The volume check compares the source\u2019s current byte rate against a rolling average of its own recent behaviour, firing only once the source has established a baseline and then jumps far above it. Every alert carries the evidence that triggered it, including the smoothed rate and how many windows it was sustained for, so that its reasoning is visible and can be trusted."));
  add(p("The pairing of EMA smoothing with sustained-window hysteresis is a deliberate, well-established way to trade a small amount of detection speed for a large reduction in false alarms. The cost is a short, predictable delay of a few polling cycles before a genuine flood is confirmed; the benefit is that ordinary traffic noise no longer produces spurious alerts. This trade-off is measured directly in the evaluation later in this chapter."));

  add(h2("4.4 The Controller Application"));
  add(p("The controller application is the bridge between the live network and the detection engine. It has three jobs. First, it acts as a learning switch, so that the hosts on the network can communicate normally, it learns which host is on which port and installs forwarding rules so ordinary traffic flows smoothly. Second, on a repeating timer, every two seconds, it asks every switch for its statistics; this short interval keeps detection responsive without flooding the controller with requests. Third, when the statistics arrive, it turns them into per-second rates, feeds them to the detection engine, records any alerts, and blocks attackers when the attack is serious. It also writes each cycle\u2019s rates and every alert and mitigation to CSV log files, which the evaluation tools described later read to measure the system\u2019s performance."));
  add(p("The heart of the controller is the part that handles a statistics reply. It works out the rate for each flow by comparing the new counters with the previous ones, builds a record for each flow, stores the records for the dashboard, and passes them to the detector:"));
  add(code("def flow_stats_reply(event):"));
  add(code("    for each flow in the reply:"));
  add(code("        compute packet_rate and byte_rate vs the previous reading"));
  add(code("        build a FlowRecord"));
  add(code("    store the flow records for the dashboard"));
  add(code("    alerts = detector.process(flow_records)"));
  add(code("    for alert in alerts:"));
  add(code("        log the alert and add it to the store"));
  add(code("        if alert severity is HIGH:"));
  add(code("            mitigate(alert.source)     # install a drop rule"));
  add(p("The mitigation installs a high-priority rule that drops all traffic from the attacker on every switch. Rather than a fixed lifetime, the rule uses an idle timeout: it stays in place as long as attack packets keep arriving and matching it, and removes itself automatically thirty seconds after the attack stops. This gives clean automatic recovery, a source that stops misbehaving regains its connectivity on its own, while an attacker that keeps flooding stays blocked. Because the controller can program every switch at once, the attacker is cut off from the whole network in a single move, and because the rule expires by itself once the traffic ceases, the block is firm but self-clearing."));

  add(h2("4.5 The Dashboard and Interface"));
  add(p("So that a human can see what the system is doing, the controller runs a small web server that offers both a simple programming interface and a live dashboard. The interface provides addresses that return the current summary, flows, alerts, and mitigations as data. The dashboard is a single web page that reads from these addresses every few seconds and draws the results as summary cards and tables. It shows the number of switches, flows, alerts, and mitigations at the top, followed by panels listing recent alerts, blocked attackers, and current flows. The dashboard updates on its own, giving an always-current view of the network without the administrator having to refresh anything."));
  add(figure("fig_dashboard.png", "Figure 4.1: The dashboard during testing, showing live flows and a detected attack.", 6.0));

  add(h2("4.6 The Test Network and Traffic Tools"));
  add(p("The system was tested on the virtual network described in Chapter Three: three switches and six hosts, created in Mininet with Open vSwitch, all managed by the controller. To exercise the system, a set of small tools was written. A traffic sink runs on a target host and accepts connections on several ports, giving other hosts something to talk to. A normal-traffic generator opens ordinary connections and transfers modest, steady amounts of data, imitating everyday use that the system should not flag. A port-scan tool rapidly probes many ports on a target, imitating reconnaissance. A flood tool sends traffic as fast as it can at a target, imitating a denial-of-service attack. Together these tools let the system be tested against both the traffic it should ignore and the attacks it should catch."));

  add(h2("4.7 Testing"));
  add(p("Testing was carried out at two levels. First, the detection logic was tested on its own with automated tests, feeding it carefully chosen traffic records and checking that it reached the right decisions. Second, the whole system was tested together, with real simulated traffic and attacks flowing through the Mininet network and the controller responding live."));

  add(h3("4.7.1 Automated Tests of the Detection Logic"));
  add(p("Because the detection engine is self-contained, it could be tested thoroughly and repeatably without starting a network. A set of unit tests checks each part of its behaviour: that a clear port scan is detected, that normal traffic to a few services is not mistaken for a scan, that a sustained fast single flow is caught as a flood, that an attack spread across many flows is caught by the aggregate check, that a single brief spike is correctly ignored thanks to the sustained-window requirement, that the smoothed rate converges sensibly toward the true rate, that a sudden jump above a source\u2019s baseline is caught as a volume anomaly, and that the cooldown stops the same attack from raising endless repeated alerts. Every one of these tests passes."));
  add(code("$ python3 tests/test_detection.py"));
  add(code("PASS test_cooldown_suppresses_duplicates"));
  add(code("PASS test_flood_detected_aggregate"));
  add(code("PASS test_flood_detected_per_flow"));
  add(code("PASS test_flood_ema_smooths_toward_rate"));
  add(code("PASS test_flood_hysteresis_ignores_single_spike"));
  add(code("PASS test_normal_traffic_no_scan"));
  add(code("PASS test_port_scan_detected"));
  add(code("PASS test_volume_anomaly_after_baseline"));
  add(code("8/8 detection tests passed."));

  add(h3("4.7.2 End-to-End Tests of the Whole Pipeline"));
  add(p("A second set of tests checks the whole path through the controller, from receiving statistics, through computing rates, through detection, to raising an alert and installing a block, by feeding realistic statistics into the real controller code and checking what it does. These tests confirm that a normal round of traffic produces no false alarm, that a flood produces a high-severity alert and causes the attacker to be blocked with a real drop rule, and that a port scan is detected through the full pipeline. All of these tests pass as well."));
  add(code("$ python3 tests/test_integration.py"));
  add(code("PASS test_rate_computation_and_no_false_alert"));
  add(code("PASS test_end_to_end_flood_alert_and_mitigation (attacker blocked)"));
  add(code("PASS test_end_to_end_port_scan_alert"));
  add(code("3/3 integration tests passed."));

  add(h3("4.7.3 Live Demonstration"));
  add(p("Finally, the complete scenario was run as a live demonstration. Normal traffic was generated first, so the sources could establish their baselines, and the system correctly stayed quiet. Then a port scan was launched from one host against another; the system detected it and raised a port-scan alert. Then a flood was launched; the system detected the high packet rate, raised a high-severity flood alert, and automatically installed a rule blocking the attacker. Then a sudden volume spike was generated from a host that had established a calm baseline, and the system flagged it as a volume anomaly. The following narrated run shows the sequence:"));
  add(code("1. NORMAL TRAFFIC  (h1 browsing web + ssh on h4)"));
  add(code("   (no anomaly - traffic looks normal)   x6 cycles"));
  add(code("   baseline established for 10.0.0.1"));
  add(code(""));
  add(code("2. PORT SCAN  (attacker h2 sweeps 20 ports on h4)"));
  add(code("   >>> [MEDIUM] PORT_SCAN: Source 10.0.0.2 contacted 20 distinct"));
  add(code("       destination endpoints ... consistent with a port/host scan."));
  add(code(""));
  add(code("3. UDP FLOOD  (attacker h3 blasts h4:80, sustained)"));
  add(code("   >>> [HIGH] FLOOD: Flow 10.0.0.3 -> 10.0.0.4:80 (UDP) is sending"));
  add(code("       12000 packets/sec (smoothed source rate 12000 pkt/s,"));
  add(code("       sustained for 3 cycles), above the 500 pkt/s flood threshold."));
  add(code(""));
  add(code("4. VOLUME SPIKE  (h1 suddenly sends 25x its baseline)"));
  add(code("   >>> [HIGH] FLOOD: ... above the flood threshold."));
  add(code("   >>> [MEDIUM] VOLUME: Source 10.0.0.1 byte rate 5.00 MB/s is"));
  add(code("       12.4x its established baseline of 0.40 MB/s."));

  add(h2("4.8 Results and Analysis"));
  add(p("The testing shows that the system meets its goals. It reliably detected all three classes of attack it was designed to catch, and it did not raise false alarms on the normal traffic used to establish baselines. The following chart summarises the outcomes across the tested scenarios."));
  add(figure("fig_results.png", "Figure 4.2: Summary of detection results across the tested scenarios.", 6.0));
  add(p("Three things stand out from the results. The first is accuracy: attacks were detected and normal traffic was left alone, which is exactly the balance a monitoring system must strike. The self-contained tests, which cover both the attack cases and the important \u201Cnormal traffic is not a scan\u201D case, all pass, giving confidence that the detection logic behaves as intended."));
  add(p("The second is speed. Because the controller polls the switches every few seconds and the detection engine processes each round almost instantly, attacks were caught within seconds of starting. For the flood, the automatic block was installed as soon as the high-severity alert fired, cutting the attacker off from the whole network in a single coordinated action. This is far faster than the manual, device-by-device response that a traditional network would require, and it directly demonstrates the value of building detection and response into the SDN controller."));
  add(p("The third is explainability. Every alert the system raised named the attack, the source, and the exact evidence, the number of destinations contacted, the packet rate, or the multiple of the baseline. This means the alerts are not mysterious numbers but clear statements that an administrator can read, understand, and act on with confidence."));
  add(p("The results also illustrate the trade-off built into any threshold-based system. The thresholds were set to catch clear attacks while ignoring normal traffic, and in testing they did so cleanly. In a real network with messier traffic, the thresholds might need tuning, lower to catch quieter attacks, higher to avoid false alarms, which is precisely why the system was designed to make tuning easy. The volume-spike scenario is a good example of the system\u2019s layered thinking: the same event was caught both as a flood, because its packet rate was high, and as a volume anomaly, because it was far above the source\u2019s baseline, showing how several checks working together give more complete coverage than any one alone."));

  add(h3("4.8.1 Quantified Evaluation Metrics"));
  add(p("Beyond confirming that attacks are caught, it is useful to put numbers on how well the system performs. To do this the controller records every polling cycle and every alert and mitigation to log files, and a companion evaluation tool then compares what the system did against what actually happened during a controlled attack. For each polling interval it labels the attacker as either genuinely attacking or behaving normally (the ground truth), and as either flagged or not flagged by the system (the detection). Counting the matches and mismatches across every interval yields the standard measures used to judge a detector."));
  add(p("The key measures are precision, the share of the system\u2019s alerts that were correct; recall, also called the detection rate, the share of the real attack that the system caught; the F1 score, which balances the two; detection latency, how long after the attack began the first alert fired; mitigation latency, how quickly the attacker was blocked; and recovery time, how long after the attack stopped the block cleared by itself. The following results come from a controlled run with a sustained flood from one host against another."));
  add(table([
    ["Metric", "Result"],
    ["Precision", "100.0%"],
    ["Recall (detection rate)", "84.6%"],
    ["F1 score", "91.7%"],
    ["Accuracy", "93.9%"],
    ["Detection latency", "4.0 s"],
    ["Mitigation latency", "4.0 s"],
    ["Recovery time", "30.0 s"],
    ["Peak attack rate", "4,000 pkt/s"],
  ]));
  add(H.caption("Table 4.1: Quantified detection metrics from a controlled flood run."));
  add(p("These numbers tell a clear and honest story. Precision is a perfect hundred per cent, meaning the system never raised a false alarm on the benign traffic, exactly the behaviour the Exponential Moving Average and the sustained-window requirement were added to achieve. Recall is a little under ninety per cent rather than a full hundred, and this is not a flaw but the visible price of that same noise-suppression: the smoothing and the sustained-window check deliberately wait a few polling cycles to be sure an attack is real before firing, so the first few seconds of the attack are counted as missed. This shows up as the four-second detection latency. In other words, the system trades a small, predictable delay at the very start of an attack for the guarantee that it will not cry wolf, which is usually the right trade for a monitoring tool that administrators need to trust."));
  add(p("The mitigation latency matches the detection latency, confirming that once a serious attack is confirmed the attacker is blocked in the same instant. The thirty-second recovery time reflects the idle-timeout drop rule clearing itself once the attack stops, so a source that stops misbehaving is automatically allowed back without any manual step. The picture below shows the attacker\u2019s raw packet rate against its smoothed value over the course of the run, with the flood threshold marked; it makes plain how the smoothed line rises past the threshold shortly after the attack starts and falls back below it after the attack ends."));
  add(figure("fig_eval_rateema.png", "Figure 4.3: The attacker\u2019s raw packet rate and its smoothed (EMA) value over a controlled flood, with the flood threshold marked.", 6.0));

  add(p("Overall, the evaluation confirms that a lightweight, explainable, statistics-based detector built into an SDN controller is an effective and practical way to monitor a network and catch common attacks, and that the central view and instant control provided by SDN make automatic, network-wide response genuinely achievable. The smoothing and sustained-window techniques give it the steadiness to run without drowning an administrator in false alarms, at the modest cost of a few seconds\u2019 delay before it commits to an alert."));
  add(pageBreak());

  return out;
};

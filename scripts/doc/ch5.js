module.exports = function (H) {
  const { h1, h2, h3, p, bullet, num, pageBreak } = H;
  return [
    h1("CHAPTER FIVE: CONCLUSION AND FUTURE WORKS"),

    h2("5.1 Introduction"),
    p("This final chapter brings the project to a close. It summarises what was set out to be done and what was achieved, offers recommendations based on the experience of building and testing the system, and suggests directions in which the work could be taken further. It ends by reflecting on what the project shows about using Software-Defined Networking for network security."),

    h2("5.2 Summary of the Project"),
    p("The project set out to design, build, and evaluate a traffic-monitoring and anomaly-detection system that runs inside an SDN controller and uses the network-wide view provided by Software-Defined Networking to detect and automatically respond to common network attacks in real time. Every part of that aim was met."),
    p("A working controller application was built on the Ryu SDN framework, written so that it also runs on the maintained os-ken fork. It acts as a switch so the network functions normally, and on a repeating timer it collects flow and port statistics from every switch it manages. These raw counters are turned into meaningful per-second traffic rates and fed to a detection engine."),
    p("The detection engine, built as a self-contained and explainable component, recognises three common and important classes of attack: port scans, in which one machine probes many services; floods or denial-of-service attacks, in which a machine sends traffic far faster than normal; and volume anomalies, in which a machine\u2019s traffic jumps far above its own usual level. Every alert the engine raises carries the evidence that triggered it, so its decisions can be understood and trusted, and all of its thresholds are gathered in one place so it can be tuned easily."),
    p("Beyond detection, the system responds. When it sees a serious attack it automatically installs a temporary blocking rule on the switches, cutting the attacker off from the whole network in a single coordinated action, without any human having to intervene. A live dashboard presents flows, alerts, and mitigations in a form an administrator can understand at a glance, backed by a simple programming interface."),
    p("The system was tested on a realistic virtual network built with Mininet and Open vSwitch. Automated tests of the detection logic all passed, end-to-end tests of the whole pipeline all passed, and a live demonstration showed the system correctly ignoring normal traffic and then detecting, in turn, a port scan, a flood, and a volume spike, blocking the flood attacker automatically. The results confirm that the system detects attacks accurately, avoids false alarms on normal traffic, and responds within seconds."),

    h2("5.3 Achievement of Objectives"),
    p("Measured against the objectives set out in Chapter One, the project succeeded on every count:"),
    bullet("The relevant literature was reviewed, providing a solid foundation for the design."),
    bullet("A controller application was built that collects statistics and computes traffic rates."),
    bullet("An explainable, tunable detection engine was built that recognises port scans, floods, and volume anomalies."),
    bullet("Automatic mitigation was added, blocking serious attackers across the whole network."),
    bullet("A live dashboard and programming interface were provided."),
    bullet("A realistic virtual test network was built and driven with normal traffic and simulated attacks."),
    bullet("The system was evaluated and shown to detect attacks accurately, avoid false alarms, and respond quickly."),

    h2("5.4 Recommendations"),
    p("Based on the experience of building and testing this system, several recommendations can be made to anyone deploying or extending it:"),
    num("Tune the thresholds to the network. The default thresholds worked cleanly in testing, but every real network has its own normal traffic patterns. The thresholds should be observed and adjusted against real traffic before the system is relied upon, lowering them to catch quieter attacks or raising them to avoid false alarms."),
    num("Treat automatic blocking as a fast first line of defence, not a complete one. Blocking by source address stops a straightforward attacker quickly, but a determined attacker who can change addresses may work around it. The automatic block buys time and contains the immediate damage; it should sit alongside, not replace, other defences."),
    num("Keep the detection engine lightweight. The decision to use explainable statistical detection rather than a heavy machine-learning model kept the system fast and easy to trust. This balance should be preserved; any added complexity should be weighed against the cost to speed and clarity."),
    num("Protect the controller. Because the controller is the brain of the network and the home of the monitoring system, it deserves strong protection. In a real deployment it should be secured and, ideally, run in a resilient configuration so that it is not a single point of failure."),
    num("Keep a permanent record where it matters. The system holds its data in memory for speed, which suits live monitoring. Where a lasting record of alerts is valuable, for audits or investigations, the alerts should also be written to permanent storage."),

    h2("5.5 Future Work"),
    p("The system provides a solid, working foundation that could be extended in several worthwhile directions:"),
    num("Add a machine-learning layer. The self-contained design of the detection engine means a machine-learning model could be added alongside the statistical checks, learning subtler patterns while the statistical rules continue to provide a transparent, trusted baseline. Combining the two would blend detection power with explainability."),
    num("Detect more classes of attack. The three attacks covered here are common and important, but the same statistics could be used to catch others, such as slow scans that stay under the current thresholds, unusual protocol mixes, or traffic to known-bad destinations."),
    num("Smarter mitigation. Instead of blocking an attacker outright, the controller could slow their traffic, redirect it for closer inspection, or block only the specific offending flows, giving a more measured response that reduces the impact of any false alarm."),
    num("Scale to larger networks. Testing on large physical networks, and running several controllers together for resilience and capacity, would show how the system behaves under heavy real-world load and would prepare it for production use."),
    num("Richer visualisation and history. The dashboard could be extended with graphs of traffic over time, a searchable history of past alerts, and configurable notifications, turning the live view into a fuller monitoring console."),
    num("Integration with other security tools. The system\u2019s alerts could be fed to a wider security platform, so that the SDN-based detection becomes one trusted source among several in an organisation\u2019s overall defence."),

    h2("5.6 Conclusion"),
    p("Networks have grown larger, busier, and more exposed to attack than ever, while the traditional way of watching over them, device by device, by hand, and after the fact, has struggled to keep pace. This project set out to show that Software-Defined Networking offers a better way, and it did."),
    p("By lifting the network\u2019s decision-making into a central controller with a complete view, SDN makes it possible to watch the whole network from one place and to act on it instantly. This project used that vantage point to build a practical system that continuously monitors traffic, recognises the fingerprints of common attacks through a lightweight and explainable engine, and blocks serious attackers automatically across the whole network within seconds, all presented through a live dashboard and proven on a realistic simulated network."),
    p("The wider lesson is that security monitoring need not be a separate, expensive add-on bolted onto the edge of a network. When the network itself is programmable and self-aware, as SDN makes it, detection and response can be built right into its brain. As networks continue to grow and threats continue to evolve, this kind of built-in, automatic, network-wide intelligence will only become more important. This project demonstrates, in a small but complete and working form, that it is both achievable and worthwhile."),
    pageBreak(),
  ];
};

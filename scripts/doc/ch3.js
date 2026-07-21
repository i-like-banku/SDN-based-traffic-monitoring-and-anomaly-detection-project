module.exports = function (H) {
  const { h1, h2, h3, p, bullet, num, code, table, figure, pageBreak, spacer } = H;
  const out = [];
  const add = (x) => { Array.isArray(x) ? out.push(...x) : out.push(x); };

  add(h1("CHAPTER THREE: SYSTEM ANALYSIS AND DESIGN"));

  add(h2("3.1 Introduction"));
  add(p("This chapter explains how the system was analysed and designed before any code was written. Good design is what separates a system that works by luck from one that works by intention. The chapter begins by describing the methodology used to carry out the project. It then sets out the requirements, both what the system must do and how well it must do it. After that it presents the design in detail: how information enters the system, how results come out, how data is held, and how the parts fit together. This is illustrated with a full set of diagrams and with pseudocode for the main processes. The chapter closes with the hardware and software needed to build and run the system."));

  add(h2("3.2 Methodology"));
  add(p("Every project needs a plan for how the work will be done, and choosing the right plan matters. The main methodologies used in building software and network systems are Waterfall, Agile, Rapid Application Development, and Prototyping. Waterfall works through fixed stages in strict order and suits projects whose requirements are completely known in advance. Agile works in short repeated cycles and suits projects with changing requirements and a team delivering features continuously. Rapid Application Development emphasises building quickly with reusable parts. Prototyping builds a working version early and improves it through repeated cycles of testing and refinement."));
  add(p("This project used the prototyping methodology. The reason is that the project brings together several complex and interacting technologies, an SDN controller, the OpenFlow protocol, a detection engine, a virtual network, and traffic-generation tools, whose combined behaviour is genuinely hard to predict fully in advance. It is one thing to reason on paper about how a detection threshold should behave; it is another to watch real simulated traffic flow through the system and see what actually happens. Prototyping is designed for exactly this kind of situation, where building something and observing it teaches you things that planning alone cannot."));
  add(h3("3.2.1 Why Prototyping Was Chosen"));
  add(p("Several specific features of the project made prototyping the right fit. First, the project is exploratory: the exact thresholds that best separate attacks from normal traffic could only be found by experiment. Second, the system is made of many parts that must work together, and prototyping allowed each part to be built and tested both on its own and as part of the whole, catching problems early before they could spread. Third, being able to watch the system run in the Mininet network gave concrete, visible feedback, seeing an alert appear the moment a simulated attack started was far more informative than any amount of planning. Fourth, the methodology welcomed change: when testing revealed that a threshold was too sensitive or a piece of logic needed adjusting, making the change was a normal part of the process rather than a disruption."));
  add(h3("3.2.2 Phases of the Methodology"));
  add(p("The work followed a series of phases that flowed into one another in a continuous cycle of building, testing, and improving:"));
  add(num("Literature review and requirements gathering: understanding the technologies and deciding what the system needed to do, as presented in Chapter Two and section 3.3."));
  add(num("System design: working out the architecture, the detection logic, the data flow, and the interfaces, as presented in this chapter."));
  add(num("Implementation: building the controller application, the detection engine, the dashboard, the virtual network, and the traffic tools, as described in Chapter Four."));
  add(num("Testing and refinement: running normal traffic and simulated attacks, observing the results, and adjusting the system, repeating this cycle until the system behaved reliably."));
  add(num("Evaluation: measuring how well the finished system detected attacks, avoided false alarms, and responded, as presented in Chapter Four."));

  add(h2("3.3 Requirements Analysis"));
  add(p("Before building a system it is essential to be clear about what it must do and how well it must do it. Requirements come in two kinds. Functional requirements describe what the system does, its specific capabilities and behaviours. Non-functional requirements describe how well it does them, qualities such as speed, reliability, and ease of use."));
  add(h3("3.3.1 Functional Requirements"));
  add(p("The system must meet the following functional requirements:"));
  add(num("Provide network connectivity: the controller must act as a working switch so that the hosts on the network can communicate normally, because there is no point monitoring a network that does not work."));
  add(num("Collect statistics: the controller must regularly ask every connected switch for its flow and port statistics."));
  add(num("Compute traffic rates: the system must turn the raw, ever-growing counters into meaningful per-second rates by comparing successive readings."));
  add(num("Detect port scans: the system must recognise when one source contacts an unusually large number of distinct destinations or ports in a short time with little traffic to each."));
  add(num("Detect floods and denial-of-service: the system must recognise when a source sends traffic at an unusually high packet rate, whether in a single flow or across many flows combined."));
  add(num("Detect volume anomalies: the system must learn each source\u2019s normal traffic level and flag sudden jumps far above it."));
  add(num("Raise explainable alerts: every alert must state clearly what triggered it and include the evidence, so that a human can understand and trust it."));
  add(num("Mitigate automatically: when a serious attack is detected, the system must install a temporary rule on the switches that blocks the attacker."));
  add(num("Present a dashboard: the system must offer a live view of flows, alerts, and mitigations, updating automatically."));
  add(num("Expose an interface: the system must provide a simple programming interface (a REST API) so that its data can be read by the dashboard or other tools."));
  add(h3("3.3.2 Non-Functional Requirements"));
  add(p("The system must also meet the following non-functional requirements:"));
  add(bullet("Performance: the detection engine must be lightweight enough to run inside the controller without slowing it down, and must process each round of statistics quickly."));
  add(bullet("Timeliness: the system must detect and respond to attacks within seconds, not minutes, since the value of the system depends on speed."));
  add(bullet("Accuracy: the system must correctly identify attacks while keeping false alarms on normal traffic low, so that its alerts are trusted."));
  add(bullet("Reliability: the system must run continuously without crashing and must handle switches connecting and disconnecting gracefully."));
  add(bullet("Usability: the dashboard must be clear enough that an administrator can understand the state of the network at a glance."));
  add(bullet("Tunability: the thresholds that define an attack must be easy to adjust in one place, so the system can be tuned to different networks."));
  add(bullet("Portability: the system should run on common Linux systems and on both the classic Ryu framework and its maintained fork."));

  add(h2("3.4 System Architecture Design"));
  add(p("The system is organised into three layers, following the standard shape of an SDN system. This layered design keeps each part\u2019s job clear and separate, which makes the system easier to understand, build, and maintain."));
  add(figure("fig_architecture.png", "Figure 3.1: The three-layer architecture of the system.", 5.6));
  add(h3("3.4.1 The Application Layer"));
  add(p("The top layer contains the programs that give the network its purpose. In this project these are the monitoring and detection application and the dashboard. This layer decides what the network should watch for and how it should respond, but it does not talk to the switches directly; instead it works through the controller beneath it."));
  add(h3("3.4.2 The Control Layer"));
  add(p("The middle layer is the Ryu controller together with this project\u2019s core logic: the part that collects statistics, the detection engine, the mitigation logic, and the shared store that holds the current picture of the network. This layer is the brain. It receives statistics from the switches below, studies them, decides whether anything is wrong, and, when necessary, sends blocking rules back down to the switches."));
  add(h3("3.4.3 The Infrastructure Layer"));
  add(p("The bottom layer is the network itself, the Open vSwitch software switches and the hosts connected to them, all created inside Mininet. This layer does the actual forwarding of traffic and keeps the counters that the control layer reads. It follows the rules the controller installs and reports its statistics on request."));
  add(h3("3.4.4 How the Layers Communicate"));
  add(p("The application layer talks to the control layer through a programming interface within the controller. The control layer talks to the infrastructure layer through the OpenFlow protocol. This clean separation means each layer can be understood on its own, and it mirrors exactly the standard SDN architecture described in Chapter Two."));

  add(h2("3.5 Network Topology Design"));
  add(p("To test the system realistically, a virtual network was designed with enough structure to be interesting but not so much as to be unwieldy. The topology has three switches and six hosts. Two of the switches are edge switches, each connecting a group of three hosts, and the third is a core switch that joins the two edges together. Every switch connects to the same controller. This shape resembles a small real network, with hosts grouped behind edge switches and traffic between groups passing through a core, which makes attacks that cross the network, such as one host scanning or flooding another, pass through the switches where they can be observed."));
  add(figure("fig_topology.png", "Figure 3.2: The Mininet test network of three switches and six hosts, all managed by one controller.", 5.6));

  add(h2("3.6 Input Design"));
  add(p("Input design describes the information that flows into the system. Unlike a typical form-based application, this system\u2019s main input is not typed by a person but streamed automatically from the network. There are two main kinds of input."));
  add(h3("3.6.1 Flow and Port Statistics"));
  add(p("The primary input is the statistics the controller collects from the switches. For each flow, the switch reports the source and destination addresses and ports, the protocol, and the cumulative counts of packets and bytes the flow has carried, along with how long it has existed. For each port, the switch reports the packets and bytes sent and received and any errors. These numbers arrive every few seconds in response to the controller\u2019s requests, and they are the raw material the whole system works from."));
  add(h3("3.6.2 Configuration Input"));
  add(p("The second kind of input is configuration: the thresholds and settings that define what counts as an attack, such as how many distinct destinations make a port scan or how many packets per second make a flood. These are gathered in one place so they can be adjusted easily. They are read once when the system starts and shape every decision the detection engine makes."));

  add(h2("3.7 Output Design"));
  add(p("Output design describes what the system produces for the people and tools that use it. The system has three main outputs."));
  add(h3("3.7.1 Alerts"));
  add(p("The most important output is an alert. When the detection engine decides that traffic matches an attack pattern, it produces an alert that names the category of attack, its severity, the source responsible, a plain-language description of what happened, and the evidence that triggered the decision, for example, the exact packet rate or the number of distinct destinations contacted. Because each alert carries its evidence, an administrator can see not just that something was flagged but why, which makes the alerts trustworthy and useful."));
  add(h3("3.7.2 Mitigations"));
  add(p("When an attack is serious, the system produces a second kind of output: a mitigation. This is a blocking rule installed on the switches that drops traffic from the attacker for a set period. The system records each mitigation, which source was blocked and when, so that administrators can see what automatic actions have been taken."));
  add(h3("3.7.3 The Live Dashboard"));
  add(p("The third output is the dashboard, which gathers everything into a single web page that updates itself every few seconds. It shows summary counts of switches, flows, alerts, and mitigations; a list of recent alerts with their details; a list of blocked attackers; and a table of the current traffic flows. The dashboard turns the system\u2019s raw outputs into a picture an administrator can understand at a glance."));
  add(figure("fig_dashboard.png", "Figure 3.3: The live monitoring dashboard showing flows, alerts, and mitigations.", 6.0));

  add(h2("3.8 Database and Data Design"));
  add(p("Because the system works on live, fast-changing data and must be lightweight, it does not use a heavy traditional database. Instead it keeps its working data in a shared in-memory store held inside the controller. This choice keeps the system fast and simple, which matters for a tool that must react within seconds. The store holds four kinds of information, each organised for quick access."));
  add(table([
    ["Data held", "Purpose"],
    ["Flow statistics (per switch)", "The current flows and their rates, shown on the dashboard."],
    ["Port statistics (per switch)", "The current per-port counters, for overall traffic health."],
    ["Alerts", "A rolling list of recent anomaly alerts with their evidence."],
    ["Mitigations", "A record of attackers that have been automatically blocked."],
  ]));
  add(H.caption("Table 3.1: The four kinds of information held in the shared store."));
  add(p("The store is protected so that the part of the system writing new data and the part reading it for the dashboard never interfere with each other. Older alerts and mitigations are automatically dropped once the lists reach a sensible size, so the system\u2019s memory use stays bounded no matter how long it runs. For a monitoring tool whose data is valuable only while it is fresh, this in-memory design is a deliberate and appropriate choice; if a permanent record were ever needed, the same alerts could easily be written to a database as well."));

  add(h2("3.9 UML and Design Diagrams"));
  add(p("A set of diagrams describes the system from several angles. Together they give a complete visual picture that complements the written explanations. Each diagram answers a different question about the system."));

  add(h3("3.9.1 Use Case Diagram"));
  add(p("The use case diagram shows who uses the system and what they can do with it. There are two actors. The network administrator is the human who watches the dashboard, reviews alerts, and can adjust the thresholds. The network device, each switch, is a non-human actor that connects to the controller and reports its statistics. The diagram makes clear that the administrator interacts with the system from above, through the dashboard and settings, while the switches interact from below, feeding in the data that everything else depends on."));
  add(figure("fig_usecase.png", "Figure 3.4: Use case diagram showing the administrator and the switches interacting with the system.", 5.4));

  add(h3("3.9.2 Sequence Diagram"));
  add(p("The sequence diagram shows the order in which things happen during a single round of monitoring. Time flows downward. The controller sends a statistics request to a switch; the switch replies with its flow statistics; the controller computes the rates and passes the flow records to the detection engine; the engine checks them and, if it finds an attack, returns an alert; the controller records the alert in the store and, if the attack is serious, sends a blocking rule back to the switch. This cycle repeats every few seconds. The diagram shows that the whole process, from asking for statistics to blocking an attacker, happens automatically without any human step."));
  add(figure("fig_sequence.png", "Figure 3.5: Sequence diagram of one monitoring cycle, from statistics request to automatic mitigation.", 6.0));

  add(h3("3.9.3 Class Diagram"));
  add(p("The class diagram shows the main software building blocks and how they relate. The monitor sits at the centre, collecting statistics and coordinating the others. It uses the detector to analyse traffic and creates flow records to feed it. The detector raises alerts. The monitor writes flows, alerts, and mitigations to the store, and the dashboard application reads from the same store to display them. This structure keeps each piece focused on a single job, which makes the system easier to understand and to change."));
  add(figure("fig_class.png", "Figure 3.6: Class diagram of the main software components and their relationships.", 6.0));

  add(h3("3.9.4 Flowchart"));
  add(p("The flowchart shows the step-by-step decision process the system follows for each round of statistics. It gathers the statistics, computes the rates, and then runs three checks in turn: is this a port scan, is this a flood, is this a volume anomaly. Each check can branch to raising an alert, and a serious alert branches further to installing a block. If none of the checks fire, the traffic is treated as normal and the system simply waits for the next round. The diagram makes plain that the process is automatic and that there are clear decision points where an attack is separated from normal traffic."));
  add(figure("fig_flowchart.png", "Figure 3.7: Flowchart of the detection and response process for each monitoring cycle.", 5.2));

  add(h3("3.9.5 Component Diagram"));
  add(p("The component diagram shows the major building blocks of the whole system and the interfaces through which they connect. The Mininet network connects to the monitor application through OpenFlow. The monitor feeds the detector, which can send a drop rule back to the network to mitigate an attack. The monitor writes to the shared store, and the REST and dashboard component reads from the store and serves it to a web browser over HTTP. The diagram gives a high-level view of how the pieces plug together and which protocol each connection uses."));
  add(figure("fig_component.png", "Figure 3.8: Component diagram showing the major building blocks and their interfaces.", 6.0));

  add(h2("3.10 Pseudocode Design"));
  add(p("Pseudocode describes the logic of the main processes in plain, structured language, without the fine detail of real code. It bridges the gap between the design and the implementation, making the intended logic clear before the actual programming begins. Three processes are central to the system."));

  add(h3("3.10.1 Statistics Collection and Rate Computation"));
  add(p("This process runs every few seconds. It asks each switch for its statistics, and when the reply arrives it turns the raw counters into per-second rates by comparing them with the previous reading."));
  add(code("BEGIN monitoring loop"));
  add(code("  EVERY few seconds:"));
  add(code("    FOR each connected switch:"));
  add(code("      SEND flow-statistics request"));
  add(code("      SEND port-statistics request"));
  add(code(""));
  add(code("ON receiving flow statistics from a switch:"));
  add(code("  FOR each flow in the reply:"));
  add(code("    IF flow is not IPv4: skip it"));
  add(code("    key = (switch, src, dst, src_port, dst_port, protocol)"));
  add(code("    previous = remembered counters for key"));
  add(code("    IF previous exists:"));
  add(code("      elapsed = now - previous.time"));
  add(code("      packet_rate = (packets - previous.packets) / elapsed"));
  add(code("      byte_rate   = (bytes   - previous.bytes)   / elapsed"));
  add(code("    ELSE:"));
  add(code("      packet_rate = byte_rate = 0   // first sighting"));
  add(code("    remember current counters for key"));
  add(code("    build a flow record with the rates"));
  add(code("  store all flow records for the dashboard"));
  add(code("  pass the flow records to the detection engine"));
  add(code("END"));
  add(p("The key idea here is the comparison with the previous reading. A switch\u2019s counters only ever grow, so a single reading tells you little; it is the change between two readings, divided by the time between them, that reveals how fast traffic is flowing right now."));

  add(h3("3.10.2 Anomaly Detection"));
  add(p("This process takes one round of flow records and checks them against the three attack patterns, returning any alerts it finds."));
  add(code("BEGIN detection(flow_records):"));
  add(code("  alerts = empty list"));
  add(code("  group flow_records by source address"));
  add(code("  FOR each source and its flows:"));
  add(code("    // Port-scan check"));
  add(code("    update the sliding set of destinations this source touched"));
  add(code("    IF distinct destinations >= scan threshold"));
  add(code("       AND average packets per flow is very small:"));
  add(code("      add a PORT_SCAN alert"));
  add(code(""));
  add(code("    // Flood check (smoothed, with hysteresis)"));
  add(code("    update the source's EMA of its aggregate packet rate"));
  add(code("    IF any single flow's packet rate >= flood threshold"));
  add(code("       OR the smoothed aggregate rate >= aggregate threshold:"));
  add(code("      increase the source's over-threshold streak"));
  add(code("    ELSE reset the streak to zero"));
  add(code("    IF streak >= sustained_windows:"));
  add(code("      add a FLOOD alert (HIGH severity)"));
  add(code(""));
  add(code("    // Volume-anomaly check"));
  add(code("    IF source has an established baseline"));
  add(code("       AND current byte rate >= baseline * multiplier:"));
  add(code("      add a VOLUME alert"));
  add(code("    update the source's rolling baseline with this reading"));
  add(code(""));
  add(code("    apply a cooldown so the same alert is not repeated too often"));
  add(code("  RETURN alerts"));
  add(code("END"));
  add(p("Each check looks for the specific fingerprint of one kind of attack. The port-scan check looks for many destinations with little traffic each. The flood check looks for an unusually high packet rate, but it first smooths that rate with an Exponential Moving Average and then requires it to stay high for several consecutive polls before reacting, so a brief harmless spike is ignored while a real, sustained flood is caught. The volume check compares the current traffic against the source\u2019s own learned normal level. A cooldown prevents the same ongoing attack from generating a flood of repeated alerts."));

  add(h3("3.10.3 Automatic Mitigation"));
  add(p("This process runs when a serious attack is detected. It installs a blocking rule against the attacker on every switch that clears itself once the attack stops."));
  add(code("BEGIN mitigate(attacker_address):"));
  add(code("  IF attacker is already blocked: do nothing"));
  add(code("  mark attacker as blocked"));
  add(code("  FOR each connected switch:"));
  add(code("    install a high-priority rule that matches the attacker's"));
  add(code("    source address and drops the traffic, with an IDLE timeout"));
  add(code("    so it expires once no more attack packets arrive"));
  add(code("  record the mitigation in the store"));
  add(code("END"));
  add(p("The rule is given high priority so it takes precedence over the normal forwarding rules. It uses an idle timeout, which means it stays in place while attack packets keep matching it and removes itself automatically once the attack stops for a set period. This gives clean automatic recovery: an attacker who keeps flooding stays blocked, while a source that stops misbehaving regains its connectivity on its own. Because the controller can install this rule on every switch at once, the attacker is cut off from the whole network in a single coordinated action."));

  add(h2("3.11 Hardware and Software Requirements"));
  add(h3("3.11.1 Hardware Requirements"));
  add(p("The system is deliberately lightweight and runs comfortably on ordinary hardware. The recommended minimum is a computer with a dual-core processor, four gigabytes of memory, and a few gigabytes of free disk space. Hardware virtualization support (Intel VT-x or AMD-V) is helpful if the system is run inside a virtual machine. No special networking hardware is needed, because the entire test network is created in software by Mininet."));
  add(table([
    ["Component", "Minimum", "Recommended"],
    ["Processor", "Dual-core", "Quad-core"],
    ["Memory", "4 GB", "8 GB"],
    ["Disk space", "4 GB free", "10 GB free"],
    ["Virtualization", "Optional", "VT-x / AMD-V enabled"],
  ]));
  add(H.caption("Table 3.2: Hardware requirements."));
  add(h3("3.11.2 Software Requirements"));
  add(p("The software requirements are all free and open-source. The system runs on a Linux operating system, with Ubuntu recommended because the SDN tools are best supported there. It needs the Python programming language, the Ryu SDN framework (or its maintained fork, os-ken), the Mininet network emulator, and Open vSwitch to provide the software switches. A modern web browser is used to view the dashboard, and a text editor is used for any configuration."));
  add(table([
    ["Software", "Purpose"],
    ["Ubuntu Linux", "Operating system, best support for SDN tools"],
    ["Python 3", "Language the controller and tools are written in"],
    ["Ryu / os-ken", "The SDN controller framework"],
    ["Mininet", "Creates the virtual test network"],
    ["Open vSwitch", "Provides the OpenFlow software switches"],
    ["Web browser", "Displays the live dashboard"],
  ]));
  add(H.caption("Table 3.3: Software requirements."));
  add(p("These requirements ensure that the system can be built and tested on a single ordinary computer, which keeps the project accessible and reproducible. The next chapter describes how the design set out here was turned into a working system, and presents the results of testing it."));
  add(pageBreak());

  return out;
};

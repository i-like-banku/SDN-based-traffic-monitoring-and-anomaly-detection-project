const fs = require("fs");

module.exports = function (H, extra) {
  const { h1, h2, p, code, pageBreak } = H;
  const { Paragraph, TextRun, AlignmentType } = H;

  function ref(text) {
    return new Paragraph({
      spacing: { after: 120, line: 300 },
      indent: { left: 720, hanging: 720 },
      alignment: AlignmentType.JUSTIFIED,
      children: [new TextRun({ text, size: 24, font: "Calibri" })],
    });
  }

  function fullListing(path) {
    const lines = fs.readFileSync(path, "utf8").split("\n");
    while (lines.length && lines[lines.length - 1].trim() === "") lines.pop();
    return lines.map((l) => code(l.replace(/\t/g, "    ")));
  }

  const references = [
    h1("REFERENCES"),
    p("The references below are presented in APA style. They include the primary journal and conference literature that informed the design, together with the technical specifications and tool documentation the implementation relied upon."),
    ref("Abdi, A., Audah, L., Salh, A., Alhartomi, M., Rasheed, H., Ahmed, S., & Tahir, A. (2024). Security control and data planes of SDN: A comprehensive review of traditional, AI, and MTD approaches to security solutions. IEEE Access, 12, 69941-69980."),
    ref("Ahmad, S., & Mir, A. (2020). Scalability, consistency, reliability and security in SDN controllers: A survey of diverse SDN controllers. Journal of Network and Systems Management, 29(9)."),
    ref("Ahmed, K., Blech, J., Gregory, M., & Schmidt, H. (2018). Software defined networks in industrial automation. Journal of Sensor and Actuator Networks, 7(3), 33."),
    ref("Bakhshi, T. (2017). State of the art and recent research advances in software defined networking. Wireless Communications and Mobile Computing, 2017, 1-35."),
    ref("Braun, W., & Menth, M. (2014). Software-defined networking using OpenFlow: Protocols, applications and architectural design choices. Future Internet, 6(2), 302-336."),
    ref("Dhawan, M., Poddar, R., Mahajan, K., & Mann, V. (2015). SPHINX: Detecting security attacks in software-defined networks. Proceedings of the Network and Distributed System Security Symposium (NDSS)."),
    ref("Esch, J. (2014). Software-defined networking: A comprehensive survey. Proceedings of the IEEE, 103(1), 10-13."),
    ref("Giotis, K., Argyropoulos, C., Androulidakis, G., Kalogeras, D., & Maglaris, V. (2014). Combining OpenFlow and sFlow for an effective and scalable anomaly detection and mitigation mechanism in SDN environments. Computer Networks, 62, 122-136."),
    ref("Jarraya, Y., Madi, T., & Debbabi, M. (2014). A survey and a layered taxonomy of software-defined networking. IEEE Communications Surveys & Tutorials, 16(4), 1955-1980."),
    ref("Kreutz, D., Ramos, F., Verissimo, P., Rothenberg, C., Azodolmolky, S., & Uhlig, S. (2015). Software-defined networking: A comprehensive survey. Proceedings of the IEEE, 103(1), 14-76."),
    ref("Lantz, B., Heller, B., & McKeown, N. (2010). A network in a laptop: Rapid prototyping for software-defined networks. Proceedings of the 9th ACM SIGCOMM Workshop on Hot Topics in Networks, 1-6."),
    ref("McKeown, N., Anderson, T., Balakrishnan, H., Parulkar, G., Peterson, L., Rexford, J., Shenker, S., & Turner, J. (2008). OpenFlow: Enabling innovation in campus networks. ACM SIGCOMM Computer Communication Review, 38(2), 69-74."),
    ref("Mousavi, S. M., & St-Hilaire, M. (2015). Early detection of DDoS attacks against SDN controllers. Proceedings of the International Conference on Computing, Networking and Communications (ICNC), 77-81."),
    ref("Nunes, B., Mendonca, M., Nguyen, X., Obraczka, K., & Turletti, T. (2014). A survey of software-defined networking: Past, present, and future of programmable networks. IEEE Communications Surveys & Tutorials, 16(3), 1617-1634."),
    ref("Open Networking Foundation. (2015). OpenFlow switch specification, version 1.3.5. Open Networking Foundation."),
    ref("Rawat, D., & Reddy, S. (2017). Software defined networking architecture, security and energy efficiency: A survey. IEEE Communications Surveys & Tutorials, 19(1), 325-346."),
    ref("Scott-Hayward, S., Natarajan, S., & Sezer, S. (2016). A survey of security in software defined networks. IEEE Communications Surveys & Tutorials, 18(1), 623-654."),
    ref("Shu, Z., Wan, J., Li, D., Lin, J., Vasilakos, A., & Imran, M. (2016). Security in software-defined networking: Threats and countermeasures. Mobile Networks and Applications, 21(5), 764-776."),
    ref("Xie, J., Yu, F., Huang, T., Xie, R., Liu, J., Wang, C., & Liu, Y. (2018). A survey of machine learning techniques applied to software defined networking (SDN): Research issues and challenges. IEEE Communications Surveys & Tutorials, 21(1), 393-430."),
    ref("Zhao, Y., Li, Y., Zhang, X., Geng, G., Zhang, W., & Sun, Y. (2019). A survey of networking applications applying the software defined networking concept based on machine learning. IEEE Access, 7, 95397-95417."),
    pageBreak(),
  ];

  const A = [h1("APPENDICES")];
  A.push(p("The appendices contain the complete source code of the system, so that the implementation can be examined and reproduced in full. Each appendix corresponds to one component described in Chapter Four."));
  A.push(pageBreak());

  function appendixFile(label, title, intro, path) {
    A.push(h2(label + ": " + title));
    A.push(p(intro));
    fullListing(path).forEach((c) => A.push(c));
    A.push(pageBreak());
  }

  appendixFile("Appendix A", "Anomaly Detection Engine (detection.py)",
    "The self-contained detection engine. It receives flow records, keeps a short rolling history per source, and returns explainable alerts for port scans, floods, and volume anomalies. It has no dependency on any SDN library, so it can be tested in isolation.",
    "/home/claude/sdn_ids/controller/detection.py");

  appendixFile("Appendix B", "Controller Application (sdn_monitor.py)",
    "The Ryu controller application. It acts as a learning switch, polls the switches for statistics, computes per-second rates, feeds them to the detection engine, records alerts, and installs blocking rules to mitigate serious attacks.",
    "/home/claude/sdn_ids/controller/sdn_monitor.py");

  appendixFile("Appendix C", "Shared Store (store.py)",
    "A small thread-safe in-memory store shared between the controller (which writes statistics and alerts) and the REST interface (which reads them for the dashboard).",
    "/home/claude/sdn_ids/controller/store.py");

  appendixFile("Appendix D", "REST Interface and Dashboard (rest.py)",
    "The self-contained web server that exposes the system's data over HTTP and serves the live dashboard. It uses a lightweight WSGI server so it runs on both Ryu and os-ken.",
    "/home/claude/sdn_ids/controller/rest.py");

  appendixFile("Appendix E", "Mininet Test Network (topology.py)",
    "The Mininet script that builds the virtual test network of three switches and six hosts and points every switch at the remote controller.",
    "/home/claude/sdn_ids/topology/topology.py");

  A.push(h2("Appendix F: Traffic and Attack Tools"));
  A.push(p("The port-scan attack simulator, which rapidly probes many ports on a target to imitate reconnaissance."));
  fullListing("/home/claude/sdn_ids/traffic/port_scan.py").forEach((c) => A.push(c));
  A.push(pageBreak());
  A.push(h2("Appendix F (continued): Flood Simulator (flood.py)"));
  A.push(p("The flood simulator, which sends traffic as fast as possible at a target to imitate a denial-of-service attack."));
  fullListing("/home/claude/sdn_ids/traffic/flood.py").forEach((c) => A.push(c));
  A.push(pageBreak());

  appendixFile("Appendix G", "Detection Engine Tests (test_detection.py)",
    "The automated unit tests that validate the detection engine's behaviour on synthetic traffic, covering each attack type, the EMA smoothing, the sustained-window hysteresis, and the important normal-traffic case.",
    "/home/claude/sdn_ids/tests/test_detection.py");

  appendixFile("Appendix H", "Evaluation Metrics Script (evaluate.py)",
    "The offline evaluation tool that reads the controller's CSV logs and computes precision, recall, F1, accuracy, detection latency, mitigation latency, and recovery time for a controlled attack.",
    "/home/claude/sdn_ids/analysis/evaluate.py");

  return references.concat(A);
};

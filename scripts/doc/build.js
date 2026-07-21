/*
 * build.js - generates the full project document (Word .docx).
 * Content lives in chapter modules (ch1.js ... ch5.js, refs.js, appendix.js).
 * Run: node scripts/doc/build.js
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  TableOfContents, PageBreak, ImageRun, PageNumber, Header, Footer,
  Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
  LevelFormat, convertInchesToTwip,
} = require("docx");

const DOCS = "/home/claude/sdn_ids/docs";

// ---- shared style constants ------------------------------------------------
const FONT = "Calibri";
const BODY = 24;   // 12pt (half-points)
const NAVY = "1F3864";
const ACCENT = "2563EB";

// ---- helper builders -------------------------------------------------------
function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 160 },
    children: [new TextRun({ text, bold: true, color: NAVY, size: 32, font: FONT })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 260, after: 120 },
    children: [new TextRun({ text, bold: true, color: NAVY, size: 28, font: FONT })],
  });
}
function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 100 },
    children: [new TextRun({ text, bold: true, color: ACCENT, size: 25, font: FONT })],
  });
}
// paragraph of body text; accepts a string
function p(text) {
  return new Paragraph({
    spacing: { after: 140, line: 300 },
    alignment: AlignmentType.JUSTIFIED,
    children: [new TextRun({ text, size: BODY, font: FONT })],
  });
}
// bulleted item
function bullet(text) {
  return new Paragraph({
    bullet: { level: 0 },
    spacing: { after: 60, line: 290 },
    children: [new TextRun({ text, size: BODY, font: FONT })],
  });
}
// numbered item (uses reference "nums")
function num(text) {
  return new Paragraph({
    numbering: { reference: "nums", level: 0 },
    spacing: { after: 60, line: 290 },
    children: [new TextRun({ text, size: BODY, font: FONT })],
  });
}
// monospace code line(s)
function code(text) {
  return new Paragraph({
    spacing: { after: 0, line: 240 },
    shading: { type: ShadingType.CLEAR, fill: "F1F5F9" },
    children: [new TextRun({ text, font: "Consolas", size: 18 })],
  });
}
function caption(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 60, after: 200 },
    children: [new TextRun({ text, italics: true, size: 20, color: "555555", font: FONT })],
  });
}
function figure(file, cap, widthIn) {
  const w = (widthIn || 6.0);
  const data = fs.readFileSync(path.join(DOCS, file));
  // read intrinsic size ratio via png header (width/height at bytes 16-24)
  const iw = data.readUInt32BE(16), ih = data.readUInt32BE(20);
  const wEmuPx = w * 96; // px at 96dpi
  const hEmuPx = wEmuPx * (ih / iw);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 120, after: 40 },
      children: [new ImageRun({
        type: "png",
        data,
        transformation: { width: Math.round(wEmuPx), height: Math.round(hEmuPx) },
      })],
    }),
    caption(cap),
  ];
}
function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}
function spacer() {
  return new Paragraph({ children: [new TextRun({ text: "" })] });
}

// simple 2-col or N-col table from array-of-arrays; first row is header
function table(rows, widths) {
  const totalW = 9360; // ~6.5in in DXA
  const colW = widths || rows[0].map(() => Math.floor(totalW / rows[0].length));
  const border = { style: BorderStyle.SINGLE, size: 4, color: "CBD5E1" };
  const borders = { top: border, bottom: border, left: border, right: border };
  const trs = rows.map((r, ri) =>
    new TableRow({
      tableHeader: ri === 0,
      children: r.map((cell, ci) =>
        new TableCell({
          width: { size: colW[ci], type: WidthType.DXA },
          shading: ri === 0
            ? { type: ShadingType.CLEAR, fill: NAVY }
            : { type: ShadingType.CLEAR, fill: ri % 2 ? "FFFFFF" : "F1F5F9" },
          margins: { top: 60, bottom: 60, left: 90, right: 90 },
          children: [new Paragraph({
            spacing: { after: 0, line: 260 },
            children: [new TextRun({
              text: String(cell),
              bold: ri === 0,
              color: ri === 0 ? "FFFFFF" : "000000",
              size: 20, font: FONT,
            })],
          })],
        })
      ),
    })
  );
  return new Table({
    columnWidths: colW,
    width: { size: totalW, type: WidthType.DXA },
    rows: trs,
  });
}

// expose helpers to chapter modules
const H = { h1, h2, h3, p, bullet, num, code, caption, figure, pageBreak,
            spacer, table, TextRun, Paragraph, AlignmentType };

// ---- front matter ----------------------------------------------------------
function titlePage() {
  const line = (t, opts) => new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: opts && opts.after != null ? opts.after : 120 },
    children: [new TextRun(Object.assign({ text: t, font: FONT }, opts || {}))],
  });
  return [
    new Paragraph({ spacing: { before: 600 }, children: [] }),
    line("SDN-BASED TRAFFIC MONITORING AND ANOMALY DETECTION", { bold: true, size: 40, color: NAVY, after: 80 }),
    line("A Software-Defined Networking Approach to Real-Time Network Intrusion Detection", { italics: true, size: 26, color: "334155", after: 400 }),
    line("A Project Report Submitted in Partial Fulfilment of the Requirements for the Degree of", { size: 22, after: 60 }),
    line("Bachelor of Science in Computer Science", { bold: true, size: 24, after: 500 }),
    line("By", { size: 22, after: 60 }),
    line("Martey Kelvin Mamah", { bold: true, size: 28, after: 40 }),
    line("11237476", { size: 24, after: 600 }),
    line("Department of Computer Science", { size: 22, after: 40 }),
    line("2026", { size: 22, after: 40 }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

function declaration() {
  return [
    h1("DECLARATION"),
    p("I hereby declare that this project report titled \u201CSDN-Based Traffic Monitoring and Anomaly Detection\u201D is the result of my own original work carried out under supervision, except where due acknowledgement has been made in the text. It has not been submitted, in whole or in part, for any other degree or qualification at this or any other institution."),
    spacer(), spacer(),
    p("Student: Martey Kelvin Mamah (11237476)"),
    p("Signature: ..............................................    Date: ...................."),
    spacer(), spacer(),
    p("Supervisor: ..............................................................."),
    p("Signature: ..............................................    Date: ...................."),
    pageBreak(),
  ];
}

function acknowledgements() {
  return [
    h1("ACKNOWLEDGEMENTS"),
    p("I am grateful to my supervisor for the guidance, patience, and useful feedback that shaped this project from an idea into a working system. I also thank the members of the Department of Computer Science for creating an environment where practical, hands-on projects like this one are encouraged."),
    p("I thank the open-source communities behind Ryu, Open vSwitch, and Mininet, whose freely available tools made it possible to build and test a realistic software-defined network on ordinary hardware. Finally, I thank my family and friends for their constant support and encouragement throughout the period of this work."),
    pageBreak(),
  ];
}

function abstractPage() {
  return [
    h1("ABSTRACT"),
    p("Modern computer networks carry more traffic, connect more devices, and face more attacks than ever before. Traditional networks spread their control logic across many individual devices, which makes it hard to see what is happening across the whole network at once and slow to react when something goes wrong. Software-Defined Networking (SDN) changes this picture by separating the part of the network that decides where traffic should go (the control plane) from the part that actually forwards it (the data plane), and placing the decision-making in a single central controller that has a complete view of the network."),
    p("This project uses that central view to build a traffic-monitoring and anomaly-detection system. A controller application written for the Ryu SDN framework continuously collects traffic statistics from the switches it manages, turns those statistics into per-second rates, and passes them to a detection engine. The engine looks for the tell-tale signs of three common problems: port scans, in which one machine probes many services looking for a way in; floods or denial-of-service attacks, in which a machine sends traffic far faster than normal to overwhelm a target; and sudden volume anomalies, in which a machine\u2019s traffic jumps far above its own usual level. When the system sees a serious attack it does not just raise an alert. It can automatically install a rule on the switches that blocks the attacker for a period of time, containing the problem without any human having to intervene."),
    p("The system was built and tested on a virtual network created with Mininet, using Open vSwitch software switches and simulated hosts. Normal traffic, port scans, and floods were generated between the hosts, and the system was measured on whether it correctly distinguished attacks from normal behaviour and how quickly it responded. The detection logic was also validated by an automated test suite. The results show that placing lightweight statistical detection directly inside the SDN controller is an effective and practical way to spot and stop common attacks early, and that the central vantage point of SDN makes this kind of network-wide monitoring far simpler than it would be in a traditional network."),
    p("Keywords: Software-Defined Networking, OpenFlow, Ryu, Mininet, network monitoring, anomaly detection, intrusion detection, port scan, denial of service, network security."),
    pageBreak(),
  ];
}

function tocPage(entries) {
  const rows = (entries || []).map((e) => {
    const indent = e.level === 2 ? 480 : 0;
    return new Paragraph({
      spacing: { after: 60, line: 288 },
      indent: { left: indent },
      tabStops: [{ type: AlignmentType.RIGHT, position: 9360, leader: "dot" }],
      children: [
        new TextRun({ text: e.text, bold: e.level === 1, size: 22, font: FONT,
                      color: e.level === 1 ? NAVY : "000000" }),
        new TextRun({ text: "\t" + e.page, size: 22, font: FONT }),
      ],
    });
  });
  return [h1("TABLE OF CONTENTS"), ...rows, pageBreak()];
}

function listLine(left, right) {
  return new Paragraph({
    spacing: { after: 90, line: 290 },
    tabStops: [{ type: "left", position: 1400 }],
    children: [
      new TextRun({ text: left, bold: true, size: 22, font: FONT }),
      new TextRun({ text: "\t" + right, size: 22, font: FONT }),
    ],
  });
}

function listOfFigures() {
  return [
    h1("LIST OF FIGURES"),
    listLine("Figure 3.1", "The three-layer architecture of the system"),
    listLine("Figure 3.2", "The Mininet test network"),
    listLine("Figure 3.3", "The live monitoring dashboard"),
    listLine("Figure 3.4", "Use case diagram"),
    listLine("Figure 3.5", "Sequence diagram of one monitoring cycle"),
    listLine("Figure 3.6", "Class diagram of the main components"),
    listLine("Figure 3.7", "Flowchart of the detection and response process"),
    listLine("Figure 3.8", "Component diagram of the system"),
    listLine("Figure 4.1", "The dashboard during testing"),
    listLine("Figure 4.2", "Summary of detection results"),
    listLine("Figure 4.3", "Attacker packet rate and smoothed EMA during a flood"),
    pageBreak(),
  ];
}

function listOfTables() {
  return [
    h1("LIST OF TABLES"),
    listLine("Table 2.1", "Comparison of the three main SDN controllers"),
    listLine("Table 3.1", "The four kinds of information held in the shared store"),
    listLine("Table 3.2", "Hardware requirements"),
    listLine("Table 3.3", "Software requirements"),
    listLine("Table 4.1", "Quantified detection metrics from a controlled flood run"),
    pageBreak(),
  ];
}

function listOfAbbreviations() {
  const rowsData = [
    ["SDN", "Software-Defined Networking"],
    ["IDS", "Intrusion Detection System"],
    ["DoS", "Denial of Service"],
    ["DDoS", "Distributed Denial of Service"],
    ["API", "Application Programming Interface"],
    ["REST", "Representational State Transfer"],
    ["HTTP", "Hypertext Transfer Protocol"],
    ["OVS", "Open vSwitch"],
    ["TCP", "Transmission Control Protocol"],
    ["UDP", "User Datagram Protocol"],
    ["IP", "Internet Protocol"],
    ["ICMP", "Internet Control Message Protocol"],
    ["MAC", "Media Access Control (address)"],
    ["VM", "Virtual Machine"],
    ["ONF", "Open Networking Foundation"],
  ];
  return [
    h1("LIST OF ABBREVIATIONS"),
    ...rowsData.map(([a, b]) => new Paragraph({
      spacing: { after: 70, line: 290 },
      children: [
        new TextRun({ text: a, bold: true, size: 22, font: FONT }),
        new TextRun({ text: "   " + b, size: 22, font: FONT }),
      ],
    })),
    pageBreak(),
  ];
}

module.exports = { H, titlePage, declaration, acknowledgements, abstractPage,
                   tocPage, listOfFigures, listOfTables, listOfAbbreviations,
                   DOCS, NAVY, ACCENT, FONT, BODY,
                   Document, Packer, Paragraph, TextRun, HeadingLevel,
                   AlignmentType, PageNumber, Header, Footer, LevelFormat };

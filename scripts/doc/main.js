/* main.js - assemble and render the full project document with a static TOC. */
const fs = require("fs");
const B = require("./build.js");
const {
  H, titlePage, declaration, acknowledgements, abstractPage, tocPage,
  listOfFigures, listOfTables, listOfAbbreviations,
  Document, Packer, Paragraph, TextRun, AlignmentType, PageNumber,
  Header, Footer, LevelFormat, FONT, NAVY,
} = B;

const ch1 = require("./ch1.js")(H);
const ch2 = require("./ch2.js")(H);
const ch3 = require("./ch3.js")(H);
const ch4 = require("./ch4.js")(H);
const refsAndAppendix = require("./refs.js")(H, {});

// ---- table of contents entries (document order) --------------------------
const TOC = [
  ["DECLARATION", 1], ["ACKNOWLEDGEMENTS", 1], ["ABSTRACT", 1],
  ["LIST OF FIGURES", 1], ["LIST OF TABLES", 1], ["LIST OF ABBREVIATIONS", 1],
  ["CHAPTER ONE: INTRODUCTION", 1],
  ["1.1 Introduction", 2], ["1.2 Background of the Study", 2],
  ["1.3 Problem Statement", 2], ["1.4 Research Questions", 2],
  ["1.5 Aim and Objectives", 2], ["1.6 Scope and Limitations of the Study", 2],
  ["1.7 Research Methodology (Brief)", 2], ["1.8 Organisation of the Project", 2],
  ["CHAPTER TWO: LITERATURE REVIEW", 1],
  ["2.1 Introduction", 2], ["2.2 Software-Defined Networking", 2],
  ["2.3 The OpenFlow Protocol", 2], ["2.4 SDN Controllers", 2],
  ["2.5 Network Monitoring and Anomaly Detection", 2],
  ["2.6 Review of Similar Systems", 2], ["2.7 Summary and Research Gap", 2],
  ["CHAPTER THREE: SYSTEM ANALYSIS AND DESIGN", 1],
  ["3.1 Introduction", 2], ["3.2 Methodology", 2],
  ["3.3 Requirements Analysis", 2], ["3.4 System Architecture Design", 2],
  ["3.5 Network Topology Design", 2], ["3.6 Input Design", 2],
  ["3.7 Output Design", 2], ["3.8 Database and Data Design", 2],
  ["3.9 UML and Design Diagrams", 2], ["3.10 Pseudocode Design", 2],
  ["3.11 Hardware and Software Requirements", 2],
  ["CHAPTER FOUR: IMPLEMENTATION AND EVALUATION", 1],
  ["4.1 Introduction", 2], ["4.2 Implementation Overview", 2],
  ["4.3 The Detection Engine", 2], ["4.4 The Controller Application", 2],
  ["4.5 The Dashboard and Interface", 2],
  ["4.6 The Test Network and Traffic Tools", 2],
  ["4.7 Testing", 2], ["4.8 Results and Analysis", 2],
  ["REFERENCES", 1],
  ["APPENDICES", 1],
  ["Appendix A: Anomaly Detection Engine (detection.py)", 2],
  ["Appendix B: Controller Application (sdn_monitor.py)", 2],
  ["Appendix C: Shared Store (store.py)", 2],
  ["Appendix D: REST Interface and Dashboard (rest.py)", 2],
  ["Appendix E: Mininet Test Network (topology.py)", 2],
  ["Appendix F: Traffic and Attack Tools", 2],
  ["Appendix G: Detection Engine Tests (test_detection.py)", 2],
  ["Appendix H: Evaluation Metrics Script (evaluate.py)", 2],
];

// load real page numbers if the finder has produced them
let pageMap = {};
const PAGEFILE = "/home/claude/sdn_ids/scripts/doc/tocpages.json";
if (fs.existsSync(PAGEFILE)) {
  try { pageMap = JSON.parse(fs.readFileSync(PAGEFILE, "utf8")); } catch (e) {}
}
const tocEntries = TOC.map(([text, level]) => ({
  text, level, page: pageMap[text] != null ? String(pageMap[text]) : "",
}));

const body = []
  .concat(titlePage())
  .concat(declaration())
  .concat(acknowledgements())
  .concat(abstractPage())
  .concat(tocPage(tocEntries))
  .concat(listOfFigures())
  .concat(listOfTables())
  .concat(listOfAbbreviations())
  .concat(ch1, ch2, ch3, ch4)
  .concat(refsAndAppendix);

const doc = new Document({
  creator: "Martey Kelvin Mamah",
  title: "SDN-Based Traffic Monitoring and Anomaly Detection",
  description: "Undergraduate project report",
  numbering: {
    config: [{
      reference: "nums",
      levels: [{
        level: 0, format: LevelFormat.DECIMAL, text: "%1.",
        alignment: AlignmentType.START,
        style: { run: { size: 24, font: FONT } },
      }],
    }],
  },
  styles: { default: { document: { run: { font: FONT, size: B.BODY } } } },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({
            text: "SDN-Based Traffic Monitoring and Anomaly Detection",
            italics: true, size: 16, color: "888888", font: FONT,
          })],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "Page ", size: 18, color: "888888", font: FONT }),
            new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "888888", font: FONT }),
          ],
        })],
      }),
    },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("/home/claude/sdn_ids/docs/Project_Report.docx", buf);
  console.log("wrote Project_Report.docx (" + buf.length + " bytes)");
});

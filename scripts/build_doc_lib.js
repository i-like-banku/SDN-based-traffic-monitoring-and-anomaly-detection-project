// build_doc_lib.js - shared helpers for constructing the project document.
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  PageBreak, TableOfContents, ImageRun, Table, TableRow, TableCell,
  WidthType, BorderStyle, ShadingType, PageNumber, Header, Footer,
  LevelFormat, convertInchesToTwip, Tab, TabStopType, TabStopPosition,
} = require("docx");

const FONT = "Calibri";
const CODE_FONT = "Consolas";
const NAVY = "1e293b";
const BLUE = "2563eb";
const GREY = "64748b";
const CODE_BG = "f4f6f8";

// ---- basic paragraph builders --------------------------------------------
function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 160 },
    children: [new TextRun({ text, bold: true, font: FONT, size: 32, color: NAVY })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 260, after: 120 },
    children: [new TextRun({ text, bold: true, font: FONT, size: 26, color: BLUE })],
  });
}
function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 100 },
    children: [new TextRun({ text, bold: true, font: FONT, size: 23, color: NAVY })],
  });
}
// body paragraph from a plain string
function p(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 140, line: 300 },
    alignment: opts.align || AlignmentType.JUSTIFIED,
    children: [new TextRun({ text, font: FONT, size: 22 })],
  });
}
// paragraph supporting inline bold runs: pass array of {t, b}
function pRuns(runs) {
  return new Paragraph({
    spacing: { after: 140, line: 300 },
    alignment: AlignmentType.JUSTIFIED,
    children: runs.map(r => new TextRun({
      text: r.t, bold: !!r.b, italics: !!r.i, font: FONT, size: 22,
    })),
  });
}
function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { after: 80, line: 290 },
    children: [new TextRun({ text, font: FONT, size: 22 })],
  });
}
function numbered(text, ref = "nums", level = 0) {
  return new Paragraph({
    numbering: { reference: ref, level },
    spacing: { after: 80, line: 290 },
    children: [new TextRun({ text, font: FONT, size: 22 })],
  });
}

// ---- code block -----------------------------------------------------------
function codeBlock(code, opts = {}) {
  const lines = code.replace(/\t/g, "    ").split("\n");
  return lines.map((ln, i) =>
    new Paragraph({
      shading: { type: ShadingType.CLEAR, color: "auto", fill: CODE_BG },
      spacing: { after: 0, line: 250 },
      border: {
        left: { style: BorderStyle.SINGLE, size: 18, color: "cbd5e1", space: 6 },
      },
      indent: { left: convertInchesToTwip(0.15) },
      children: [new TextRun({ text: ln === "" ? " " : ln, font: CODE_FONT, size: 17 })],
    })
  );
}

// ---- image + caption ------------------------------------------------------
function image(path, widthPx, heightPx, caption) {
  const out = [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 160, after: 60 },
      children: [new ImageRun({
        type: "png",
        data: fs.readFileSync(path),
        transformation: { width: widthPx, height: heightPx },
      })],
    }),
  ];
  if (caption) {
    out.push(new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 200 },
      children: [new TextRun({ text: caption, italics: true, font: FONT, size: 18, color: GREY })],
    }));
  }
  return out;
}

// ---- simple table from rows (array of arrays), first row header ----------
function table(rows, widths) {
  const totalDxa = 9360; // ~6.5in usable
  const colW = widths || rows[0].map(() => Math.floor(totalDxa / rows[0].length));
  const trs = rows.map((cells, ri) =>
    new TableRow({
      tableHeader: ri === 0,
      children: cells.map((c, ci) =>
        new TableCell({
          width: { size: colW[ci], type: WidthType.DXA },
          shading: ri === 0
            ? { type: ShadingType.CLEAR, color: "auto", fill: "1e293b" }
            : (ri % 2 === 0
                ? { type: ShadingType.CLEAR, color: "auto", fill: "f1f5f9" }
                : undefined),
          margins: { top: 60, bottom: 60, left: 100, right: 100 },
          children: [new Paragraph({
            spacing: { after: 0, line: 260 },
            children: [new TextRun({
              text: String(c), font: FONT, size: 19,
              bold: ri === 0, color: ri === 0 ? "ffffff" : "000000",
            })],
          })],
        })
      ),
    })
  );
  return new Table({
    columnWidths: colW,
    width: { size: totalDxa, type: WidthType.DXA },
    rows: trs,
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: "cbd5e1" },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: "cbd5e1" },
      left: { style: BorderStyle.SINGLE, size: 4, color: "cbd5e1" },
      right: { style: BorderStyle.SINGLE, size: 4, color: "cbd5e1" },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: "e2e8f0" },
      insideVertical: { style: BorderStyle.SINGLE, size: 2, color: "e2e8f0" },
    },
  });
}

function caption(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 200, before: 40 },
    children: [new TextRun({ text, italics: true, font: FONT, size: 18, color: GREY })],
  });
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

module.exports = {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  PageBreak, TableOfContents, ImageRun, Header, Footer, PageNumber,
  LevelFormat, AlignmentType, convertInchesToTwip, WidthType,
  Tab, TabStopType, TabStopPosition,
  FONT, CODE_FONT, NAVY, BLUE, GREY,
  h1, h2, h3, p, pRuns, bullet, numbered, codeBlock, image, table,
  caption, pageBreak,
};

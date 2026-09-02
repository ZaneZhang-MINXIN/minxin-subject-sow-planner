#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";
import JSZip from "jszip";

const SHEETS = ["Setup", "Course_Brief", "Calendar_Events", "Timetable_Slots", "Units", "Objectives", "Weekly_Plan", "Weeks", "SOW_View", "QA"];
const EDITABLE = new Set(["Setup", "Course_Brief", "Calendar_Events", "Timetable_Slots", "Units", "Objectives", "Weekly_Plan"]);
const DATE_FIELDS = new Set(["start", "end_inclusive", "valid_from", "valid_to", "date_start", "date_end", "authority_accessed"]);
const palette = { navy: "#1F4E78", blue: "#0000FF", yellow: "#FFFF99", input: "#DDEBF7", generated: "#F2F2F2", border: "#B4C6E7", white: "#FFFFFF", red: "#F4CCCC", amber: "#FCE5CD", green: "#D9EAD3" };

function args(argv) {
  const result = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (!argv[i].startsWith("--")) continue;
    const key = argv[i].slice(2);
    result[key] = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : true;
  }
  if (!result.data || !result.out) throw new Error("Usage: build_planner.mjs --data planner.json --out planner.xlsx [--preview-dir dir]");
  return result;
}

function col(index) {
  let n = index + 1, out = "";
  while (n) { const rem = (n - 1) % 26; out = String.fromCharCode(65 + rem) + out; n = Math.floor((n - 1) / 26); }
  return out;
}

function safeTable(name) { return `${name.replace(/[^A-Za-z0-9]/g, "")}Table`; }

function value(header, raw) {
  if (raw === undefined || raw === null) return "";
  if (DATE_FIELDS.has(header) && typeof raw === "string" && /^\d{4}-\d{2}-\d{2}$/.test(raw)) return new Date(`${raw}T00:00:00`);
  return raw;
}

const widths = {
  key: 26, value: 32, notes: 48, course_id: 22, subject_name: 22, kla: 28, curriculum_framework: 24,
  learner_context: 42, required_content: 46, assessment_pattern: 38, resource_constraints: 36, mc_focus: 28,
  authority_title: 42, authority_url: 42, event_id: 19, title: 42, source_label: 34, source_locator: 20,
  source_sha256: 22, scope_id: 24, plan_id: 20, week_id: 18, unit_id: 20, objective_id: 22,
  objective_text: 52, success_evidence: 42, standard_anchor: 34, prerequisite_refs: 26, learning_unit: 34,
  prior_learning: 32, objective_refs: 32, knowledge_content: 42, disciplinary_practice: 38, activities: 54,
  major_concern_refs: 24,
  evidence: 42, assessment_purpose: 30, feedback_revision: 42, resources: 34, values: 24,
  progression_delta: 34, context_delta: 34, evidence_delta: 34, independence_delta: 34,
  message: 58, record_refs: 36, source_refs: 34, stop_condition: 42, teaching_objectives: 58,
  calendar_context: 42, date_range: 24, module_unit: 28, learning_focus: 36,
};

function addSheet(workbook, name, headers, records, reserveRows, note) {
  const sheet = workbook.worksheets.add(name);
  const editable = EDITABLE.has(name);
  const rows = records.map((record) => headers.map((header) => value(header, record[header])));
  for (let i = 0; i < reserveRows; i += 1) rows.push(headers.map(() => ""));
  const last = col(headers.length - 1);
  sheet.showGridLines = false;
  sheet.mergeCells(`A1:${last}1`);
  sheet.getRange("A1").values = [[name.replaceAll("_", " ")]];
  sheet.getRange(`A1:${last}1`).format = { fill: palette.navy, font: { bold: true, color: palette.white, size: 16 }, verticalAlignment: "center" };
  sheet.getRange(`A1:${last}1`).format.rowHeight = 28;
  sheet.mergeCells(`A2:${last}2`);
  sheet.getRange("A2").values = [[note]];
  sheet.getRange(`A2:${last}2`).format = { fill: editable ? palette.input : palette.generated, font: { italic: true, color: "#404040", size: 10 }, wrapText: true };
  sheet.getRange(`A2:${last}2`).format.rowHeight = 34;
  sheet.getRange(`A4:${last}4`).values = [headers];
  sheet.getRange(`A4:${last}4`).format = { fill: palette.yellow, font: { bold: true, color: palette.blue, size: 10 }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, borders: { preset: "all", style: "thin", color: palette.border } };
  sheet.getRange(`A4:${last}4`).format.rowHeight = 36;
  if (rows.length) {
    sheet.getRange(`A5:${last}${4 + rows.length}`).values = rows;
    const body = sheet.getRange(`A5:${last}${4 + rows.length}`);
    body.format = { fill: editable ? palette.white : palette.generated, font: { size: 9, color: "#202020" }, verticalAlignment: "center", wrapText: true, borders: { insideHorizontal: { style: "thin", color: "#D9E2F3" }, bottom: { style: "thin", color: "#D9E2F3" } } };
    body.format.rowHeight = 27;
    const table = sheet.tables.add(`A4:${last}${4 + rows.length}`, true, safeTable(name));
    table.style = editable ? "TableStyleMedium2" : "TableStyleMedium4";
    table.showFilterButton = true;
  }
  headers.forEach((header, index) => {
    const letter = col(index);
    sheet.getRange(`${letter}:${letter}`).format.columnWidth = widths[header] || Math.min(26, Math.max(12, header.length + 3));
    if (DATE_FIELDS.has(header)) sheet.getRange(`${letter}5:${letter}${Math.max(5, 4 + rows.length)}`).format.numberFormat = "yyyy-mm-dd";
  });
  if (rows.length) sheet.getRange(`A5:${last}${4 + rows.length}`).format.autofitRows();
  sheet.freezePanes.freezeRows(4);
  return { sheet, count: rows.length, last };
}

function validations(sheets) {
  const list = (sheetName, headerName, values) => {
    const meta = sheets[sheetName];
    const idx = meta.headers.indexOf(headerName);
    if (idx < 0 || meta.count < 1) return;
    meta.sheet.getRange(`${col(idx)}5:${col(idx)}${4 + meta.count}`).dataValidation = { rule: { type: "list", values } };
  };
  list("Course_Brief", "alignment_status", ["PLANNING_REQUIRED", "INFORMED_BY", "VERIFIED"]);
  list("Course_Brief", "status", ["TEST_FIXTURE", "PROPOSED_DESIGN", "DRAFT", "CONFIRMED"]);
  list("Calendar_Events", "block_policy", ["BLOCK", "NONBLOCK", "MILESTONE", "REVIEW"]);
  list("Calendar_Events", "manual_override", ["", "BLOCK", "NONBLOCK", "MILESTONE", "REVIEW"]);
  list("Timetable_Slots", "cycle_pattern", ["ALL", "A", "B"]);
  list("Units", "unit_type", ["TOPIC", "PROJECT", "PRACTICAL", "REVIEW", "SHOWCASE", "ASSESSMENT"]);
  list("Units", "schedule_policy", ["SEQUENTIAL", "BEFORE_ASSESSMENT", "FIXED_WINDOW", "REVIEW_ONLY", "SURPLUS_ONLY"]);
  list("Objectives", "alignment_status", ["INFORMED_BY", "VERIFIED", "PLANNING_REQUIRED"]);
  list("Weekly_Plan", "repetition_purpose", ["", "RETRIEVAL", "CONSOLIDATION", "SPIRAL", "TRANSFER", "ROUTINE"]);
  list("Weekly_Plan", "status", ["TEST_FIXTURE", "PROPOSED_DESIGN", "DRAFT", "CONFIRMED", "CALENDAR_BLOCK"]);
}

async function render(workbook, name, dir) {
  const blob = await workbook.render({ sheetName: name, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(dir, `${name}.png`), new Uint8Array(await blob.arrayBuffer()));
}

async function persistFreezeRows(filePath) {
  const zip = await JSZip.loadAsync(await fs.readFile(filePath));
  const names = Object.keys(zip.files).filter((name) => /^xl\/worksheets\/sheet\d+\.xml$/.test(name));
  for (const name of names) {
    let xml = await zip.file(name).async("string");
    if (/<(?:\w+:)?pane\b/.test(xml)) continue;
    const selfClosing = /<(\w+):sheetView([^>]*)\/>/;
    const paired = /<(\w+):sheetView([^>]*)>([\s\S]*?)<\/\1:sheetView>/;
    const pane = (prefix) => `<${prefix}:pane ySplit="4" topLeftCell="A5" activePane="bottomLeft" state="frozen"/><${prefix}:selection pane="bottomLeft" activeCell="A5" sqref="A5"/>`;
    if (selfClosing.test(xml)) {
      xml = xml.replace(selfClosing, (_, prefix, attrs) => `<${prefix}:sheetView${attrs}>${pane(prefix)}</${prefix}:sheetView>`);
    } else if (paired.test(xml)) {
      xml = xml.replace(paired, (_, prefix, attrs, contents) => `<${prefix}:sheetView${attrs}>${pane(prefix)}${contents}</${prefix}:sheetView>`);
    } else {
      throw new Error(`Cannot locate sheetView in ${name}`);
    }
    zip.file(name, xml);
  }
  await fs.writeFile(filePath, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

const input = args(process.argv);
const payload = JSON.parse(await fs.readFile(input.data, "utf8"));
const workbook = Workbook.create();
const sheets = {};
const notes = {
  Setup: "EDITABLE configuration. Keep keys stable; never paste a calendar publication URL.",
  Course_Brief: "EDITABLE course authority. One row is one subject/grade/level/class offering.",
  Calendar_Events: "EDITABLE normalized calendar evidence. Confirm REVIEW items and scoped assessment impact.",
  Timetable_Slots: "EDITABLE capacity input. Leave empty rather than guessing a class, teacher, room, or period.",
  Units: "EDITABLE subject units. Use Major Concerns here as the broad planning map and require observable evidence.",
  Objectives: "EDITABLE assessable outcomes. Preserve exact source anchors and course-scoped prerequisites.",
  Weekly_Plan: "EDITABLE SINGLE SOURCE OF TRUTH. Cite MC1-MC3 only for directly aligned objectives; leave blank otherwise.",
  Weeks: "GENERATED — do not edit. Rebuild after calendar or academic-year changes.",
  SOW_View: "GENERATED — do not edit. Normalized lineage view used for all Word exports.",
  QA: "GENERATED — resolve HIGH items before release; MEDIUM items require professional review.",
};
for (const name of SHEETS) {
  const headers = payload.headers[name];
  const records = payload.tables[name] || [];
  const reserve = EDITABLE.has(name) ? Math.max(4, name === "Weekly_Plan" ? 12 : 4) : 0;
  sheets[name] = { ...addSheet(workbook, name, headers, records, reserve, notes[name]), headers };
}
validations(sheets);
const qa = sheets.QA;
if (qa.count) {
  qa.sheet.getRange(`A5:${qa.last}${4 + qa.count}`).conditionalFormats.add("containsText", { text: "HIGH", format: { fill: palette.red, font: { color: "#9C0006", bold: true } } });
  qa.sheet.getRange(`A5:${qa.last}${4 + qa.count}`).conditionalFormats.add("containsText", { text: "MEDIUM", format: { fill: palette.amber } });
  qa.sheet.getRange(`A5:${qa.last}${4 + qa.count}`).conditionalFormats.add("containsText", { text: "PASS", format: { fill: palette.green } });
}
if (input["preview-dir"]) {
  await fs.mkdir(input["preview-dir"], { recursive: true });
  for (const name of SHEETS) await render(workbook, name, input["preview-dir"]);
}
await fs.mkdir(path.dirname(input.out), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(input.out);
await persistFreezeRows(input.out);
console.log(`sheets=${SHEETS.length}`);
console.log(`output=${input.out}`);

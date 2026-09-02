#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const SHEETS = ["Setup", "Course_Brief", "Calendar_Events", "Timetable_Slots", "Units", "Objectives", "Weekly_Plan", "Weeks", "SOW_View", "QA"];
const DATE_FIELDS = new Set(["start", "end_inclusive", "valid_from", "valid_to", "date_start", "date_end", "authority_accessed"]);

function args(argv) {
  const result = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (!argv[i].startsWith("--")) continue;
    const key = argv[i].slice(2);
    result[key] = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : true;
  }
  if (!result.input || !result.out) throw new Error("Usage: read_planner.mjs --input planner.xlsx --out planner.json [--preview-dir dir] [--inspect-out report]");
  return result;
}

function normalize(header, value) {
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  if (DATE_FIELDS.has(header) && typeof value === "number") {
    return new Date(Date.UTC(1899, 11, 30) + Math.round(value * 86400000)).toISOString().slice(0, 10);
  }
  return value === undefined || value === null ? "" : value;
}

function extract(sheet) {
  const used = sheet.getUsedRange();
  if (!used) return { headers: [], records: [] };
  const matrix = used.values || [];
  const headers = (matrix[3] || []).map((value) => String(value || "").trim());
  const records = [];
  for (const row of matrix.slice(4)) {
    if (!row || !String(row[0] ?? "").trim()) continue;
    const record = {};
    headers.forEach((header, index) => { if (header) record[header] = normalize(header, row[index]); });
    records.push(record);
  }
  return { headers, records };
}

async function render(workbook, name, dir) {
  const blob = await workbook.render({ sheetName: name, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(dir, `${name}.png`), new Uint8Array(await blob.arrayBuffer()));
}

const input = args(process.argv);
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(input.input));
const tables = {}, headers = {};
for (const name of SHEETS) {
  const data = extract(workbook.worksheets.getItem(name));
  headers[name] = data.headers;
  tables[name] = data.records;
}
const sourceHashRow = tables.Setup.find((row) => row.key === "source_hash");
const payload = { schema_version: "2.1", headers, tables, source_hash: sourceHashRow?.value || "", extracted_from: path.basename(input.input) };
await fs.mkdir(path.dirname(input.out), { recursive: true });
await fs.writeFile(input.out, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "formula error scan", maxChars: 8000 });
if (input["inspect-out"]) await fs.writeFile(input["inspect-out"], `${errors.ndjson}\n`, "utf8");
if (input["preview-dir"]) {
  await fs.mkdir(input["preview-dir"], { recursive: true });
  for (const name of SHEETS) await render(workbook, name, input["preview-dir"]);
}
console.log(errors.ndjson);
console.log(`output=${input.out}`);
if (!errors.ndjson.includes("matched 0 entries")) process.exitCode = 1;

#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

function args(argv) {
  const result = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (!argv[i].startsWith("--")) continue;
    const key = argv[i].slice(2);
    result[key] = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : true;
  }
  if (!result.input || !result.out) throw new Error("Usage: read_calendar_xlsx.mjs --input calendar.xlsx --out rows.json");
  return result;
}

function clean(value) {
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  if (typeof value === "number" && value > 20000 && value < 80000) return new Date(Date.UTC(1899, 11, 30) + Math.round(value * 86400000)).toISOString().slice(0, 10);
  return value === undefined || value === null ? "" : value;
}

const input = args(process.argv);
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(input.input));
const sheet = workbook.worksheets.getFirst();
if (!sheet) throw new Error("No worksheet found in calendar workbook");
const matrix = sheet.getUsedRange()?.values || [];
if (!matrix.length) throw new Error("Calendar workbook is empty");
const headers = matrix[0].map((value) => String(value || "").trim());
const rows = [];
for (const row of matrix.slice(1)) {
  if (!row.some((value) => String(value ?? "").trim())) continue;
  const record = {};
  headers.forEach((header, index) => { if (header) record[header] = clean(row[index]); });
  rows.push(record);
}
await fs.mkdir(path.dirname(input.out), { recursive: true });
await fs.writeFile(input.out, `${JSON.stringify({ sheet: sheet.name, rows }, null, 2)}\n`, "utf8");
console.log(`rows=${rows.length}`);

#!/usr/bin/env node
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outIndex = process.argv.indexOf("--out");
if (outIndex < 0 || !process.argv[outIndex + 1]) throw new Error("Usage: write_calendar_fixture.mjs --out file.xlsx");
const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Calendar");
sheet.getRange("A1:I3").values = [
  ["Title", "Start Date", "End Date", "Start Time", "End Time", "Type", "Policy", "Scope", "Scope ID"],
  ["Fixture Holiday", "2026-10-01", "2026-10-02", "", "", "HOLIDAY", "BLOCK", "SCHOOL", "ALL"],
  ["Fixture Timed Assessment", "2026-10-09", "2026-10-09", "10:00", "10:45", "ASSESSMENT", "BLOCK", "COURSE", "ENGLISH-G7-CORE-A"],
];
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(process.argv[outIndex + 1]);

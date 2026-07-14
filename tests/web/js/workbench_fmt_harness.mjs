// Node-driven unit harness for workbench.js's fmt() cell formatter (audit L1 / M8).
//
// fmt() was previously only `node --check`ed — the cell presentation (unit → toFixed, and the
// NA "—" branch) was never EXECUTED by a test. That gap hid the L1 bug (a genuinely-unmeasurable
// metric rendered "0.00" instead of "—"). fmt is closure-internal, so we brace-extract the real
// source and run it standalone (it depends only on its two args). Exit code 0 = all cases hold.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(
  join(here, "../../../src/schedule_forensics/web/static/workbench.js"),
  "utf8",
);

// pull the real fmt() out of the IIFE by brace-matching (it is not exported)
function extract(name) {
  const start = src.indexOf("function " + name + "(");
  if (start < 0) throw new Error(name + " not found in workbench.js");
  let depth = 0;
  let i = src.indexOf("{", start);
  for (; i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}" && --depth === 0) { i++; break; }
  }
  return src.slice(start, i);
}
const fmt = new Function(extract("fmt") + "\nreturn fmt;")();

let failures = 0;
function check(label, got, want) {
  if (String(got) === String(want)) { console.log("ok " + label); return; }
  failures += 1;
  console.error(`FAIL ${label}: got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
}

const DASH = "—"; // — (U+2014), the missing/NA sentinel

// L1: a genuinely-unmeasurable cell (applicable === false) renders "—", not a placeholder 0
check("NA cell -> dash", fmt({ value: 0, applicable: false }, "count"), DASH);
check("missing cell -> dash", fmt(null, "count"), DASH);
check("null value -> dash", fmt({ value: null, applicable: true }, "ratio"), DASH);
// an informational extra with a real 0 stays a number (applicable true) — not blanked to "—"
check("applicable 0 -> 0", fmt({ value: 0, applicable: true }, "count"), "0");
// back-compat: a cell with no applicable field (undefined) still renders its value
check("undefined applicable -> value", fmt({ value: 7 }, "count"), "7");
// the unit formatting is unchanged by the fix
check("percent 2dp", fmt({ value: 3.14159, applicable: true }, "%"), "3.14%");
check("ratio 2dp", fmt({ value: 0.5, applicable: true }, "ratio"), "0.50");
check("days 1dp", fmt({ value: 12.7, applicable: true }, "days"), "12.7");
check("count rounds", fmt({ value: 4.6, applicable: true }, "count"), "5");

process.exit(failures ? 1 : 0);

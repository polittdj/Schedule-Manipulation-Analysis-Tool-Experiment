// Node-driven unit harness for sra_risk.js's derive math (audit L9 / ADR-0143).
//
// The vendored file was previously only `node --check`ed — the days<->% derivation was never
// EXECUTED by any test on the client side (the server mirrors it in _reconcile_magnitudes).
// This harness stubs the minimal DOM the IIFE touches, captures its input handlers, and drives
// the SAME cases the server test pins. Exit code 0 = all assertions hold.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(
  join(here, "../../../src/schedule_forensics/web/static/sra_risk.js"),
  "utf8",
);

function stubEl(id) {
  return { id, value: "", handlers: {}, addEventListener(ev, fn) { this.handlers[ev] = fn; } };
}
const els = {};
for (const id of ["riskForm", "riskDays", "riskPct", "riskAffected", "riskDaysLocked", "riskPctLocked"])
  els[id] = stubEl(id);

// ADR-0268: the boot payload is a non-executable JSON block sra_risk.js parses by id
els.sfRemainDays = { id: "sfRemainDays", textContent: JSON.stringify({ "1": 10, "2": 20 }) }; // avg 15 days
globalThis.document = { getElementById: (id) => els[id] || null };
globalThis.window = {};

new Function(src)(); // run the IIFE against the stub DOM

const days = els.riskDays, pct = els.riskPct, aff = els.riskAffected;
const daysLock = els.riskDaysLocked, pctLock = els.riskPctLocked;
let failures = 0;
function check(label, got, want) {
  const ok = String(got) === String(want);
  if (!ok) { failures += 1; console.error(`FAIL ${label}: got ${JSON.stringify(got)} want ${JSON.stringify(want)}`); }
  else console.log(`ok ${label}`);
}

// typing 3 days over avg 15 derives 20% (the server-mirrored formula, 2dp)
aff.value = "1, 2";
days.value = "3";
days.handlers.input();
check("days locks itself", daysLock.value, "1");
check("3 days over avg 15 -> 20%", pct.value, "20");

// typing 10% derives 1.5 days
days.value = ""; days.handlers.input(); // clearing unlocks days
check("clearing unlocks days", daysLock.value, "");
pct.value = "10"; pct.handlers.input();
check("10% of avg 15 -> 1.5 days", days.value, "1.5");

// 2dp rounding: 1 day over avg 15 = 6.666...% -> 6.67
pct.value = ""; pct.handlers.input();
days.value = "1"; days.handlers.input();
check("1 day over avg 15 rounds to 6.67%", pct.value, "6.67");

// audit L4: removing the derivation basis CLEARS the derived (unlocked) field — never stale
aff.value = "999"; // unknown uid -> avg 0
aff.handlers.input();
check("L4: no basis clears the unlocked %", pct.value, "");

// re-fit on affected change: basis back -> re-derives
aff.value = "2"; // avg 20
aff.handlers.input();
check("re-fit on affected change (1 day over 20 -> 5%)", pct.value, "5");

process.exit(failures ? 1 : 0);

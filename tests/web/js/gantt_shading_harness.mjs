// Node-driven regression harness for the Gantt non-working-time shading (ADR-0243 / audit ADR-0247).
//
// ADR-0243 shades each Gantt row's non-working time per THAT task's OWN calendar: a 24-hour
// (round-the-clock) task shows no weekend gray, while a Mon-Fri task still does. The behavior lives
// in vendored timescale.js (window.SFTimescale.nonworkStyle), driven by a calendar registry the page
// installs with SFTimescale.setCalendars — and it was behaviorally UNTESTED (#382 shipped a
// /driving-path per-row read of `a.calendar` that silently did nothing because neither the field nor
// the registry was wired). This harness loads the vendored IIFE with injected globals and asserts:
//   * before any calendars are registered, an unknown name falls back to Standard (Mon-Fri) and
//     SHADES weekends — i.e. a 24-hour task would be mis-shaded (the exact bug the wiring fixes);
//   * after registering the file's calendars, a Mon-Fri calendar shades weekends and a 24-hour
//     calendar does NOT — per-task shading, honoring the row's own calendar.
// Exit 0 = per-task shading holds. Mutation check: make nonworkStyle ignore its cellCal argument
// (always use the project calendar) and assertion (4) — the 24-hour "no gray" case — fails.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(
  join(here, "../../../src/schedule_forensics/web/static/timescale.js"),
  "utf8",
);

// Load the vendored IIFE (it assigns window.SFTimescale) with injected globals — no DOM is needed
// for nonworkStyle (a pure computation); the stubs only satisfy load-time references.
const win = {};
const doc = {
  readyState: "complete", // so the IIFE wires its button synchronously (getElementById -> null: no-op)
  getElementById: () => null,
  addEventListener() {},
  createElement: () => ({
    style: {},
    className: "",
    appendChild(c) {
      return c;
    },
    setAttribute() {},
    set textContent(_v) {},
  }),
};
const localStorageStub = { getItem: () => null, setItem: () => {} };
// eslint-disable-next-line no-new-func
const load = new Function("window", "document", "localStorage", src + "\n;return window.SFTimescale;");
const SF = load(win, doc, localStorageStub);

const fail = (m) => {
  console.error("FAIL: " + m);
  process.exit(1);
};

if (!SF || typeof SF.nonworkStyle !== "function" || typeof SF.setCalendars !== "function") {
  fail("SFTimescale did not load with nonworkStyle/setCalendars");
}

const DAY = 86400000;
const t0 = Date.parse("2025-01-05T00:00:00Z"); // a Sunday, so the weekend phase is clean
const axis = { t0, t1: t0 + 21 * DAY, x: (t) => ((t - t0) / DAY) * 8 }; // 8 px/day (>= the 1.25 min)

const STANDARD = { name: "Standard", work_weekdays: [0, 1, 2, 3, 4], holidays: [] };
const CAL24 = { name: "24 Hours", work_weekdays: [0, 1, 2, 3, 4, 5, 6], holidays: [] };

// 1. BEFORE registering calendars: an unknown name falls back to the built-in Standard (Mon-Fri),
//    so a 24-hour task would be shaded on weekends — the mis-shading the registry wiring removes.
if (SF.nonworkStyle(axis, "24 Hours") === null) {
  fail("pre-registry fallback should shade (Standard Mon-Fri), but got no shading");
}

// 2. Register the file's real calendars (what SFTimescale.setCalendars does on the page).
SF.setCalendars([STANDARD, CAL24]);

// 3. A Mon-Fri calendar shades its weekends: a non-null style carrying a repeating gradient.
const std = SF.nonworkStyle(axis, "Standard");
if (!std || !std.image || std.image.indexOf("gradient") < 0) {
  fail("Mon-Fri calendar should shade weekends (a repeating gradient); got " + JSON.stringify(std));
}

// 4. A 24-hour calendar shows NO weekend gray (all seven days worked -> null). THE ADR-0243 point,
//    and what proves the shading honors the ROW's own calendar rather than a single global one.
if (SF.nonworkStyle(axis, "24 Hours") !== null) {
  fail("24-hour calendar must NOT shade weekends when resolved per-task");
}

// 5. An unknown per-row name still falls back to the first registered calendar (Standard) -> shaded,
//    so a row with a missing/None calendar degrades to the project calendar, never to nothing.
if (SF.nonworkStyle(axis, "No Such Calendar") === null) {
  fail("an unknown per-row calendar should fall back to the project calendar and shade");
}

// 6. Precedence (ADR-0243): an EXPLICIT global calendar pick in the Timescale dialog wins for every
//    row over the per-row calendar. With the global set to Standard, even a 24-hour row shades.
SF.config().nonworking.calendar = "Standard";
if (SF.nonworkStyle(axis, "24 Hours") === null) {
  fail("an explicit global calendar pick must override the per-row calendar (uniform backdrop)");
}
SF.config().nonworking.calendar = ""; // restore Auto (per-row) mode

console.log("OK: per-task Gantt shading — Mon-Fri shades weekends, 24-hour does not");
process.exit(0);

// Node-driven unit harness for the "Play all" coordinator in chartframe.js (ADR-0275).
//
// The bug: a page-level master "Play all" steps every animated chart by PROGRAMMATICALLY clicking
// their Next buttons on a timer; a per-chart Stop only cleared that chart's own timer, so the master
// kept stepping it ("hit stop, it kept playing"). The fix registers each master's stop() with
// window.SFPlayAll and, on any TRUSTED (real user) click on a per-chart animation control, stops
// every master — while the master's OWN element.click() (isTrusted === false) must NOT stop it.
// This harness stubs the minimal DOM the chartframe IIFE boots against and asserts exactly that
// trusted-vs-programmatic distinction plus the register/stopAll fan-out. Exit 0 = all hold.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(
  join(here, "../../../src/schedule_forensics/web/static/chartframe.js"),
  "utf8",
);

let failures = 0;
function check(label, cond) {
  if (!cond) { failures += 1; console.error(`FAIL ${label}`); }
  else console.log(`ok ${label}`);
}

// the minimal DOM/window the chartframe IIFE touches at boot: it wires a few document listeners,
// installs the coordinator, and scans for ".chart-host" (none here, so no framing runs).
const docHandlers = {}; // key: eventName + (capture ? "C" : "B")
globalThis.window = globalThis;
globalThis.MutationObserver = function () { return { observe() {} }; };
globalThis.document = {
  readyState: "complete",
  body: { appendChild() {} },
  createElement: () => ({ className: "", style: {}, setAttribute() {}, appendChild() {} }),
  addEventListener(ev, fn, capture) { docHandlers[ev + (capture ? "C" : "B")] = fn; },
  querySelectorAll: () => [],
  querySelector: () => null,
};

new Function(src)(); // boot the IIFE → defines window.SFPlayAll + registers the capture click listener

check("SFPlayAll coordinator exists", !!(window.SFPlayAll && window.SFPlayAll.register));
const clickHandler = docHandlers["clickC"]; // the capture-phase document click listener
check("capture-phase click listener registered", typeof clickHandler === "function");

// register a fake master; count its stop() invocations
let stopped = 0;
window.SFPlayAll.register(() => { stopped += 1; });

// a fake click event: isTrusted flag + whether target.closest matches an animation control
function ev(isTrusted, onControl) {
  return { isTrusted, target: { closest: () => (onControl ? {} : null) } };
}

stopped = 0;
clickHandler(ev(true, true));
check("a real user click on a per-chart control stops the master", stopped === 1);

stopped = 0;
clickHandler(ev(false, true)); // the master's OWN programmatic .click()
check("a programmatic (untrusted) control click does NOT stop the master", stopped === 0);

stopped = 0;
clickHandler(ev(true, false)); // a trusted click somewhere that is not an animation control
check("a trusted click off any control leaves the master running", stopped === 0);

// idempotent registration + fan-out to every registered master
let a = 0, b = 0;
const stopA = () => { a += 1; };
window.SFPlayAll.register(stopA);
window.SFPlayAll.register(stopA); // duplicate — must not double-register
window.SFPlayAll.register(() => { b += 1; });
window.SFPlayAll.stopAll();
check("stopAll fans out to every distinct master exactly once", a === 1 && b === 1);

if (failures) { console.error(`${failures} failure(s)`); process.exit(1); }
console.log("all play-all coordinator checks passed");

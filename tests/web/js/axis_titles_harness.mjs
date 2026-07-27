// Node-driven unit harness for SFChartFrame.axisTitles (ADR-0298).
//
// A source pin can prove a module CALLS the helper; only execution can prove the helper puts
// the right text at the right place with the right styling hook. This boots chartframe.js's
// IIFE against a minimal DOM stub, calls axisTitles with a known plot geometry, and asserts:
//
//   * both captions are emitted, as SVG <text> carrying class="ch-at";
//   * placement matches the promoted performance.js convention (X right-aligned at the plot's
//     bottom-right, Y horizontal at the top-left) — and the Y caption is NOT rotated, which is
//     the second convention the promotion exists to remove;
//   * NO numeric font-size / fill is set in JS — size and colour come from .ch-at, so the type
//     ramp lives in exactly one CSS token;
//   * a missing xLabel/yLabel emits nothing rather than an empty caption, and a missing
//     argument is a no-op rather than a throw (charts call this before their data is known).
//
// Exit code 0 = all assertions hold.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(
  join(here, "../../../src/schedule_forensics/web/static/chartframe.js"),
  "utf8",
);

let failures = 0;
function check(label, got, want) {
  const ok = String(got) === String(want);
  if (!ok) {
    failures += 1;
    console.error(`FAIL ${label}: got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
  } else console.log(`ok ${label}`);
}

function fakeNode(tag) {
  return {
    tag,
    attrs: {},
    style: {},
    children: [],
    textContent: "",
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    appendChild(c) { this.children.push(c); return c; },
    addEventListener() {},
  };
}

globalThis.window = {};
globalThis.document = {
  readyState: "complete",
  body: fakeNode("body"),
  documentElement: fakeNode("html"),
  createElement: (t) => fakeNode(t),
  createElementNS: (_ns, t) => fakeNode(t),
  querySelectorAll: () => [],
  querySelector: () => null,
  addEventListener() {},
};
globalThis.MutationObserver = class { observe() {} disconnect() {} };

new Function(src)(); // boot the IIFE (its load-time scan() finds no .chart-host)

const api = globalThis.window.SFChartFrame;
check("axisTitles is exported", typeof api.axisTitles, "function");

// the promoted geometry: a 940x420 plot with performance.js-style insets
const GEOM = { L: 50, R: 924, T: 18, B: 374 };
const svg = fakeNode("svg");
api.axisTitles(svg, GEOM, { xLabel: "TOTAL FLOAT (WORKDAYS)", yLabel: "ACTIVITIES (COUNT)" });

check("emits exactly two captions", svg.children.length, 2);
const [x, y] = svg.children;

check("x caption is svg text", x.tag, "text");
check("x caption text", x.textContent, "TOTAL FLOAT (WORKDAYS)");
check("x caption class", x.getAttribute("class"), "ch-at");
check("x caption is right-aligned", x.getAttribute("text-anchor"), "end");
check("x caption x = plot right", x.getAttribute("x"), "924");
check("x caption y = plot bottom - 4", x.getAttribute("y"), "370");

check("y caption text", y.textContent, "ACTIVITIES (COUNT)");
check("y caption class", y.getAttribute("class"), "ch-at");
check("y caption x = plot left + 4", y.getAttribute("x"), "54");
check("y caption y = plot top + 9", y.getAttribute("y"), "27");
check("y caption is NOT anchored (start)", y.getAttribute("text-anchor"), "null");
check("y caption is NOT rotated", y.getAttribute("transform"), "null");

// Law: no numeric type/colour in JS — .ch-at owns both, so one token moves every caption.
for (const [name, node] of [["x", x], ["y", y]]) {
  check(`${name} caption sets no font-size`, node.getAttribute("font-size"), "null");
  check(`${name} caption sets no fill attr`, node.getAttribute("fill"), "null");
  check(`${name} caption sets no inline style`, Object.keys(node.style).length, 0);
}

// one-sided and absent labels
const onlyX = fakeNode("svg");
api.axisTitles(onlyX, GEOM, { xLabel: "MONTH" });
check("a missing yLabel emits nothing", onlyX.children.length, 1);

const empty = fakeNode("svg");
api.axisTitles(empty, GEOM, { xLabel: "", yLabel: "" });
check("empty strings emit nothing", empty.children.length, 0);

let threw = false;
try {
  api.axisTitles(null, null, null);
} catch {
  threw = true;
}
check("missing arguments are a no-op, not a throw", threw, false);

if (failures) {
  console.error(`${failures} assertion(s) failed`);
  process.exit(1);
}
console.log("OK axis titles");

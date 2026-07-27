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

// ADR-0302: the OPTIONAL secondary-axis caption for combo charts. Two properties matter — it
// mirrors the Y caption to the plot's top-RIGHT, and it is absent unless asked for, so every
// pre-ADR-0302 caller emits exactly what it did before.
const combo = fakeNode("svg");
api.axisTitles(combo, GEOM, {
  xLabel: "WBS BRANCH",
  yLabel: "SPI(T) (RATIO, LEFT AXIS)",
  y2Label: "EARNED SCHEDULE (WORKING DAYS, RIGHT AXIS)",
});
check("combo chart emits three captions", combo.children.length, 3);
const y2 = combo.children[2];
check("y2 caption text", y2.textContent, "EARNED SCHEDULE (WORKING DAYS, RIGHT AXIS)");
check("y2 caption class", y2.getAttribute("class"), "ch-at");
check("y2 caption x = plot right - 4", y2.getAttribute("x"), "920");
check("y2 caption y = plot top + 9 (mirrors Y)", y2.getAttribute("y"), "27");
check("y2 caption is right-aligned", y2.getAttribute("text-anchor"), "end");
check("y2 caption is NOT rotated", y2.getAttribute("transform"), "null");
check("y2 caption sets no font-size", y2.getAttribute("font-size"), "null");
check("y2 caption sets no fill attr", y2.getAttribute("fill"), "null");
// the three captions must occupy three DIFFERENT corners — a secondary caption that landed on
// the X caption would be worse than no caption at all.
const corners = combo.children.map((n) => `${n.getAttribute("x")},${n.getAttribute("y")}`);
check("three captions, three distinct anchors", new Set(corners).size, 3);
check("y2 shares the Y caption's baseline, not the X caption's", y2.getAttribute("y"),
  combo.children[1].getAttribute("y"));

// ADR-0303: placement does NOT depend on what is already in the svg. Moving the Y captions above
// the plot when that band looked free was implemented, then measured and reverted — every charted
// page already has text there, so the rule chose "inside" everywhere and bought nothing, at the
// cost of a caption whose position moves with the data. Pinned here because "put it above the
// plot instead" is the change a future reader is most likely to re-propose.
const tiered = fakeNode("svg");
const tier = fakeNode("text");           // a tier label sitting just above the plot top
tier.setAttribute("y", String(GEOM.T - 6));
tier.textContent = "MAR";
tiered.appendChild(tier);
api.axisTitles(tiered, GEOM, { xLabel: "MONTH", yLabel: "ACTIVITIES (COUNT)", y2Label: "RATIO" });
check("existing text does not move the Y caption", tiered.children[2].getAttribute("y"), "27");
check("existing text does not move Y2 either", tiered.children[3].getAttribute("y"), "27");
check("the tier label itself is untouched", tier.getAttribute("y"), String(GEOM.T - 6));

// one-sided and absent labels
const onlyX = fakeNode("svg");
api.axisTitles(onlyX, GEOM, { xLabel: "MONTH" });
check("a missing yLabel emits nothing", onlyX.children.length, 1);

const noY2 = fakeNode("svg");
api.axisTitles(noY2, GEOM, { xLabel: "MONTH", yLabel: "COUNT" });
check("omitting y2Label leaves existing callers at two captions", noY2.children.length, 2);

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

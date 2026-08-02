// Node-driven unit harness for SFGantt.tableCaption — B1's TABLE caption mechanism (ADR-0340).
//
// The Python ledger can prove a module CALLS the helper; only execution can prove the helper
// produces a real <caption>, in the position the HTML spec requires, with the styling hook that
// makes it look like every other axis caption. This boots gantt.js's IIFE against a minimal DOM
// stub and drives tableCaption for real, asserting:
//
//   * a native <caption> element carrying class="ch-atd" and the caller's exact text;
//   * it lands as the table's FIRST child EVEN WHEN ROWS ALREADY EXIST. This is the assertion
//     with teeth: the pre-ADR-0340 inline convention was `table.appendChild(el("caption"…))`,
//     which is correct only while the caller happens to call it before building any rows. Six of
//     the seven call sites build the caption next to a <thead>/<tr> append, so a helper that
//     appended would have put <caption> AFTER the rows — invalid markup, and the accessible
//     name a screen reader announces for the table stops being reliable;
//   * NO font-size / colour is set in JS — the DOM caption reads --sf-fs-axis-title through
//     .ch-atd exactly as the SVG caption reads it through .ch-at (one type ramp, ADR-0298);
//   * empty text emits NOTHING rather than an empty caption (a table whose caption text is not
//     yet known must not gain a blank accessible name), and a missing table is a no-op rather
//     than a throw — drill modules call this on tables built inside .then() callbacks.
//
// Exit code 0 = all assertions hold.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const STATIC = join(here, "../../../src/schedule_forensics/web/static");
const src = readFileSync(join(STATIC, "gantt.js"), "utf8");

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
    classList: { add() {}, remove() {}, contains: () => false },
    children: [],
    textContent: "",
    className: "",
    nodeType: 1,
    get firstChild() { return this.children.length ? this.children[0] : null; },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    appendChild(c) { this.children.push(c); return c; },
    insertBefore(c, ref) {
      const i = ref ? this.children.indexOf(ref) : -1;
      if (i < 0) this.children.push(c);
      else this.children.splice(i, 0, c);
      return c;
    },
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener() {},
  };
}

// `window === globalThis`, as in a browser: gantt.js's auto-init IIFE references `SFGantt`
// BARE (not `window.SFGantt`), so the export must land on the global scope or boot throws.
globalThis.window = globalThis;
globalThis.document = {
  readyState: "complete",
  body: fakeNode("body"),
  documentElement: fakeNode("html"),
  createElement: (t) => fakeNode(t),
  createElementNS: (_ns, t) => fakeNode(t),
  querySelector: () => null,
  querySelectorAll: () => [],
  addEventListener() {},
};
globalThis.MutationObserver = class { observe() {} disconnect() {} };

new Function(src)(); // boot both IIFEs (the auto-init finds no Gantt pane in the stub)

const api = globalThis.window.SFGantt;
check("tableCaption is exported", typeof api.tableCaption, "function");

// ── the real call, on a table that ALREADY HAS ROWS ────────────────────────────────────────────
// This mirrors what every caller does: the table exists, and the caption is added around the
// same time as the header row. An appendChild implementation passes every source-level test in
// the suite and fails right here.
const table = fakeNode("table");
const thead = table.appendChild(fakeNode("thead"));
const tbody = table.appendChild(fakeNode("tbody"));
const cap = api.tableCaption(table, "Activities behind Total float — one row per activity");

check("returns the caption node", cap && cap.tag, "caption");
check("carries the .ch-atd hook", cap && cap.className, "ch-atd");
check(
  "carries the caller's exact text",
  cap && cap.textContent,
  "Activities behind Total float — one row per activity",
);
check("caption is the table's FIRST child", table.children[0] === cap, "true");
check("existing rows keep their order", table.children[1] === thead, "true");
check("existing rows are not dropped", table.children[2] === tbody, "true");
check("nothing else was inserted", table.children.length, 3);

// the type ramp lives in CSS, never in JS (the ADR-0298 law, applied to the DOM sibling)
check("no font-size set in JS", cap.style.fontSize === undefined, "true");
check("no colour set in JS", cap.style.color === undefined, "true");
check("no inline style attribute", cap.getAttribute("style"), null);

// ── the guards ────────────────────────────────────────────────────────────────────────────────
const bare = fakeNode("table");
check("empty text emits nothing", api.tableCaption(bare, ""), null);
check("…and inserts nothing", bare.children.length, 0);
check("null text emits nothing", api.tableCaption(bare, null), null);
check("undefined text emits nothing", api.tableCaption(bare, undefined), null);
check("missing table is a no-op", api.tableCaption(null, "x"), null);

// captioning twice does not stack (a re-render replaces the table, but a caller that re-captions
// the SAME table must not accumulate names) — recorded as CURRENT behaviour, not a wish:
const twice = fakeNode("table");
api.tableCaption(twice, "first");
api.tableCaption(twice, "second");
check("re-captioning inserts a second node (callers rebuild the table)", twice.children.length, 2);
check("…and the newest is first", twice.children[0].textContent, "second");

if (failures) {
  console.error(`${failures} assertion(s) failed`);
  process.exit(1);
}
console.log("OK dom captions");

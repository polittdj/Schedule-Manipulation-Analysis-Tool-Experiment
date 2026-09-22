/* R-80 / ADR-0525 — prove the terminal `.catch` no longer reports a DRAW failure as a LOAD failure.
 *
 * The code under test is the TREE'S OWN BYTES: each site's enclosing function is sliced out of the
 * real `web/static/*.js` file by name and bound against stubs. The fetch RESOLVES with valid JSON
 * — the data arrives — and the drawing helper THROWS. Whatever sentence lands in the status element
 * is exactly what the analyst would read.
 *
 * Red before green: on the pristine tree these print "Run failed." / "Could not load the grid." /
 * "No driving path for that UID." with a 200 measured on the wire. That is the defect.
 *
 * `margin_dashboard.js`'s site lives in an inline addEventListener callback with no name to slice,
 * so it is covered by the static guard only — stated rather than silently dropped.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const STATIC = path.resolve(HERE, "..", "..", "..", "src", "schedule_forensics", "web", "static");

const SITES = [
  { file: "app.js", fn: "loadGantt", draw: "renderGantt", load: "No driving path for that UID." },
  { file: "ask.js", fn: "drivingPath", draw: "renderFacts", load: "Could not compute the driving path." },
  { file: "ask.js", fn: "ask", draw: "renderFacts", load: "Could not answer" },
  { file: "settings.js", fn: "probe", draw: "fill", load: "check failed",
    args: (el) => ["ollama", el, el, null] },
  { file: "sra_grid.js", fn: "load", draw: "render", load: "Could not load the grid." },
  { file: "sra_grid.js", fn: "save", draw: "saveSummary", load: "Save failed." },
  { file: "sra_jcl.js", fn: "run", draw: "renderResult", load: "Run failed." },
  { file: "sra_ssi.js", fn: "run", draw: "renderResult", load: "Run failed." },
  { file: "sra_ssi.js", fn: "oat", draw: "headerRow", load: "Sensitivity failed." },
];

function sliceFn(src, name) {
  const i = src.indexOf("function " + name + "(");
  if (i < 0) throw new Error(`no function ${name}`);
  const b = src.indexOf("{", i);
  let depth = 0;
  for (let j = b; j < src.length; j++) {
    if (src[j] === "{") depth++;
    else if (src[j] === "}") { depth--; if (depth === 0) return src.slice(i, j + 1); }
  }
  throw new Error(`unbalanced ${name}`);
}

// the real seam, from the real file
const g = { window: {} };
new Function("window", fs.readFileSync(path.join(STATIC, "loader.js"), "utf8"))(g.window);
const SFLoad = g.window.SFLoad;
if (!SFLoad || typeof SFLoad.drawn !== "function") {
  console.error("loader.js did not define SFLoad.drawn"); process.exit(1);
}

const failures = [];

for (const site of SITES) {
  const src = fs.readFileSync(path.join(STATIC, site.file), "utf8");
  const printed = [];
  const el = {
    set textContent(v) { printed.push(String(v)); }, get textContent() { return printed.at(-1); },
    set innerHTML(v) { printed.push(String(v)); }, get innerHTML() { return printed.at(-1); },
    appendChild() {}, removeChild() {}, addEventListener() {}, setAttribute() {},
    value: "1000", disabled: false, checked: false, parentNode: null, style: {},
  };
  const thrower = () => { throw new Error("SF-PROBE-DRAW-THROW"); };
  const stubs = {
    // the fetch SUCCEEDS: a 200 with valid JSON. The data arrived.
    fetch: () => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ ok: true, rows: [{}], facts: [], answer: "a" }) }),
    document: { getElementById: () => el, createElement: () => el, querySelectorAll: () => [] },
    window: { dispatchEvent() {}, SFLoad }, SFLoad, Event: function () {},
    URLSearchParams: globalThis.URLSearchParams, encodeURIComponent, JSON, Number, String, Math, Date,
    $: () => el, el: () => el, row: () => el, headerRow: () => el,
    renderFacts: thrower, renderGantt: thrower, renderResult: thrower, render: thrower,
    fill: thrower, saveSummary: thrower, renderRisk: thrower,
    renderLegend() {}, populateGroupCustom() {}, loadedStatus: () => "loaded",
    showExports() {}, setThinking() {}, flashError() {}, startWorking: () => () => {},
    endpointFor: () => "http://127.0.0.1:11434",
    status: el, out: el, statusEl: el, box: el, view: el, riskBtn: el, select: el,
    rows: [], pending: { a: 1 }, dataDate: null, critAvailable: false, critIters: 0,
    enc: "x", console,
  };
  stubs[site.draw] = thrower;
  const names = Object.keys(stubs);
  let fn;
  try {
    fn = new Function(...names, sliceFn(src, site.fn) + `; return ${site.fn};`)(...names.map((n) => stubs[n]));
  } catch (e) {
    failures.push(`${site.file}:${site.fn} — could not bind: ${e.message}`); continue;
  }
  try { fn(...(site.args ? site.args(el) : [])); } catch { /* a synchronous throw before the chain is not what we measure */ }
  await new Promise((r) => setTimeout(r, 25));
  const last = printed.at(-1) ?? "<nothing printed>";
  if (last.includes(site.load)) {
    failures.push(
      `${site.file}:${site.fn} — the data ARRIVED (200, valid JSON) and the draw threw, but the ` +
      `analyst reads the LOAD sentence: ${JSON.stringify(last)}`);
  } else if (!/could not be|were saved|arrived/i.test(last)) {
    failures.push(
      `${site.file}:${site.fn} — the site was not exercised or said nothing useful: ` +
      `${JSON.stringify(last)} (if this reads "<nothing printed>" the harness, not the site, is wrong)`);
  }
}

// CONTROL: the one residual site measured NOT to conflate must stay unwrapped.
if (fs.readFileSync(path.join(STATIC, "ai_polish.js"), "utf8").includes("SFLoad.drawn")) {
  failures.push("ai_polish.js was wrapped, but it was measured to cover exactly one failure mode");
}

if (failures.length) { console.error(failures.join("\n")); process.exit(1); }
console.log(`ok — ${SITES.length} sliced sites report a draw failure as a draw failure`);

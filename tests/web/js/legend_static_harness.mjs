// Node harness for SFLegend's margin_dashboard adoption SHAPE (ADR-0276, phase 3b): a legend that
// mixes clickable toggles with a STATIC color-key entry, over a series whose marks are drawn in more
// than one color. Proves against the real module: (1) a conditional-color series — the margin bars,
// green above / red below the requirement, both carrying ONE data-series key — hides/shows together
// on a single toggle; (2) a static entry (no data-series-toggle) is inert on click; (3) all/none
// toggles every real series but leaves the static key alone. Complements legend_toggle_harness (the
// trend fallback) and legend_scope_harness (the animated stable-scope path). Exit 0 = pass.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(
  join(here, "../../../src/schedule_forensics/web/static/legend_toggle.js"),
  "utf8",
);

let failures = 0;
function check(label, cond) {
  if (!cond) { failures += 1; console.error(`FAIL ${label}`); }
  else console.log(`ok ${label}`);
}

function El(tag, attrs, ns) {
  const a = attrs || {};
  const el = {
    tag, namespaceURI: ns || "http://www.w3.org/2000/svg", attrs: { ...a }, children: [], parentNode: null, style: {},
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, on) { if (on) this._s.add(c); else this._s.delete(c); },
      contains(c) { return this._s.has(c); },
    },
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    appendChild(c) { c.parentNode = this; this.children.push(c); return c; },
    _matches(sel) { return sel.split(",").some((o) => { const m = o.trim().match(/^\[([a-z-]+)\]$/); return m ? m[1] in this.attrs : false; }); },
    _walk(out) { for (const c of this.children) { out.push(c); c._walk(out); } },
    querySelector(sel) { const r = []; this._walk(r); return r.find((e) => e._matches(sel)) || null; },
    querySelectorAll(sel) { const r = []; this._walk(r); return r.filter((e) => e._matches(sel)); },
    closest(sel) { let n = this; while (n) { if (n._matches && n._matches(sel)) return n; n = n.parentNode; } return null; },
    click() { docClick({ target: this }); },
  };
  return el;
}
let handler = null;
function docClick(ev) { if (handler) handler(ev); }
globalThis.MutationObserver = function (cb) { return { observe() {}, disconnect() {}, _cb: cb }; };
globalThis.window = globalThis;
globalThis.document = { addEventListener(ev, fn) { if (ev === "click") handler = fn; } };
new Function(src)();

// margin's burndown svg: legend INSIDE the svg (render-once → the svg is the stable scope).
const svg = El("svg");
const marGreen = El("rect", { "data-series": "Effective margin (wd)", fill: "green" }); // above requirement
const marRed = El("rect", { "data-series": "Effective margin (wd)", fill: "red" });     // BELOW requirement (SAME series)
const contBar = El("rect", { "data-series": "Contingency (days)" });
svg.appendChild(marGreen); svg.appendChild(marRed); svg.appendChild(contBar);
const tgMargin = El("g", { "data-series-toggle": "Effective margin (wd)" });
const tgCont = El("g", { "data-series-toggle": "Contingency (days)" });
const staticKey = El("g", {}); // "Below requirement" — a plain swatch, NOT a toggle
const allNone = El("g", { "data-series-all": "1" });
svg.appendChild(tgMargin); svg.appendChild(tgCont); svg.appendChild(staticKey); svg.appendChild(allNone);

// (1) one toggle hides BOTH colors of the conditional-color series
tgMargin.click();
check("green margin bar hidden by the single toggle", marGreen.style.display === "none");
check("red (below-requirement) margin bar hidden by the SAME toggle", marRed.style.display === "none");
check("contingency (other series) stays visible", contBar.style.display === "");
tgMargin.click();
check("both margin colors restored on re-toggle", marGreen.style.display === "" && marRed.style.display === "");

// (2) the static color key is inert — no data-series-toggle, so a click does nothing
staticKey.click();
check("clicking the static 'Below requirement' key hides nothing",
  marGreen.style.display === "" && marRed.style.display === "" && contBar.style.display === "");

// (3) all/none toggles every real series; the static key is not a series and is untouched
allNone.click(); // nothing hidden → hide all
check("all/none hides every real series",
  marGreen.style.display === "none" && marRed.style.display === "none" && contBar.style.display === "none");
allNone.click(); // something hidden → show all
check("all/none shows every series again",
  marGreen.style.display === "" && marRed.style.display === "" && contBar.style.display === "");

if (failures) { console.error(`${failures} failure(s)`); process.exit(1); }
console.log("all SFLegend static/conditional-color checks passed");

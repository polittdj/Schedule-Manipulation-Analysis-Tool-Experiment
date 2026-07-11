// Node-driven unit harness for theme.js's four-view switcher (ADR-0195).
//
// The vendored file is otherwise only `node --check`ed — the localStorage migration
// ("light" -> "daylight", "dark"/unknown -> "console") and the daylight <-> last-dark
// toggle round-trip were never EXECUTED by any test. This harness stubs the minimal
// DOM/localStorage the IIFE touches, boots it repeatedly against different saved
// states, and drives its own select/click handlers. Exit code 0 = all assertions hold.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(
  join(here, "../../../src/schedule_forensics/web/static/theme.js"),
  "utf8",
);

let failures = 0;
function check(label, got, want) {
  const ok = String(got) === String(want);
  if (!ok) { failures += 1; console.error(`FAIL ${label}: got ${JSON.stringify(got)} want ${JSON.stringify(want)}`); }
  else console.log(`ok ${label}`);
}

function boot(storeSeed) {
  const store = { ...storeSeed };
  const attrs = {};
  const handlers = { doc: {} };
  const els = {
    themeSelect: { value: "", handlers: {}, addEventListener(ev, fn) { this.handlers[ev] = fn; } },
    themeToggle: {
      textContent: "", attrs: {}, handlers: {},
      addEventListener(ev, fn) { this.handlers[ev] = fn; },
      setAttribute(k, v) { this.attrs[k] = v; },
    },
    uiScale: { value: "", handlers: {}, addEventListener(ev, fn) { this.handlers[ev] = fn; } },
  };
  globalThis.localStorage = {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
  };
  globalThis.document = {
    documentElement: {
      style: {},
      setAttribute(k, v) { attrs[k] = v; },
      getAttribute(k) { return attrs[k] ?? null; },
    },
    getElementById: (id) => els[id] || null,
    querySelector: () => null,
    addEventListener(ev, fn) { handlers.doc[ev] = fn; },
  };
  globalThis.location = { pathname: "/", search: "" };
  new Function(src)(); // run the IIFE (pre-paint stamp happens here)
  handlers.doc.DOMContentLoaded(); // then the control wiring
  return { store, attrs, els };
}

// first visit: no save -> console, persisted
{
  const s = boot({});
  check("first visit stamps console", s.attrs["data-theme"], "console");
  check("first visit persists console", s.store["sf-theme"], "console");
}

// legacy migration: light -> daylight, dark -> console, garbage -> console
{
  const s = boot({ "sf-theme": "light" });
  check("legacy light migrates to daylight", s.attrs["data-theme"], "daylight");
  check("migrated value is written back", s.store["sf-theme"], "daylight");
}
{
  const s = boot({ "sf-theme": "dark" });
  check("legacy dark migrates to console", s.attrs["data-theme"], "console");
}
{
  const s = boot({ "sf-theme": "chartreuse" });
  check("unknown save falls back to console", s.attrs["data-theme"], "console");
}

// the four views apply verbatim and the select reflects the active view
for (const view of ["console", "daylight", "apollo", "jarvis"]) {
  const s = boot({ "sf-theme": view });
  check(`saved ${view} applies`, s.attrs["data-theme"], view);
  check(`select reflects ${view}`, s.els.themeSelect.value, view);
}

// select change applies + persists
{
  const s = boot({});
  s.els.themeSelect.value = "apollo";
  s.els.themeSelect.handlers.change();
  check("select -> apollo applies", s.attrs["data-theme"], "apollo");
  check("select -> apollo persists", s.store["sf-theme"], "apollo");
  check("apollo remembered as the dark side", s.store["sf-theme-dark"], "apollo");
}

// toggle round-trip: dark view -> daylight -> BACK to the same dark view
{
  const s = boot({ "sf-theme": "jarvis" });
  check("toggle names daylight next", s.els.themeToggle.attrs["aria-label"], "Switch theme (next: daylight)");
  s.els.themeToggle.handlers.click();
  check("toggle flips jarvis -> daylight", s.attrs["data-theme"], "daylight");
  s.els.themeToggle.handlers.click();
  check("toggle returns to the LAST dark view", s.attrs["data-theme"], "jarvis");
}

// toggle from daylight with no dark history falls back to console
{
  const s = boot({ "sf-theme": "daylight" });
  s.els.themeToggle.handlers.click();
  check("daylight with no history toggles to console", s.attrs["data-theme"], "console");
}

if (failures) { console.error(`${failures} failure(s)`); process.exit(1); }
console.log("all theme.js switcher checks passed");

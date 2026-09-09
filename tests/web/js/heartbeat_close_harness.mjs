// Node-driven harness for heartbeat.js's browser-CLOSE beacon (OR-12, ADR-0482).
//
// The Python tests prove the SERVER stops promptly once a close signal arrives. Only execution
// proves the PAGE actually sends one — and, just as important, that it does NOT send one in the
// two cases where sending would be a defect. A grep for "pagehide" cannot tell those apart;
// `if (false) { ... }` leaves every source pin satisfied (ADR-0480's C9, paid for by name).
//
// Booted against a minimal DOM/window stub, asserting:
//
//   * a real `pagehide` sends the close beacon to /api/closing;
//   * a bfcache `pagehide` (`persisted: true`) sends NOTHING — the page is alive and coming
//     back, and beaconing there would stop the tool behind a Back button;
//   * `visibilitychange` is NOT wired at all — it fires on a mere tab switch or minimise, so
//     arming the fuse there would ride on a throttled background tab's beats to survive;
//   * the beacon uses sendBeacon, which is the only send that survives unload;
//   * the periodic beat still runs, and sfQuit() still stops it and calls /api/shutdown.
//
// Exit code 0 = all assertions hold.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const STATIC = join(here, "../../../src/schedule_forensics/web/static");
const src = readFileSync(join(STATIC, "heartbeat.js"), "utf8");

let failures = 0;
function check(label, ok, extra) {
  if (!ok) { failures += 1; console.error(`FAIL ${label}${extra ? ": " + extra : ""}`); }
  else console.log(`ok ${label}`);
}

// --- the stub world -----------------------------------------------------------------------
const fetched = [];
const beacons = [];
const listeners = {};
let intervals = 0;

const win = {
  addEventListener(kind, fn) { (listeners[kind] ||= []).push(fn); },
};
const doc = { body: { innerHTML: "" } };
const nav = {
  sendBeacon(url) { beacons.push(url); return true; },
};

const sandbox = {
  window: win,
  document: doc,
  navigator: nav,
  fetch(url, opts) { fetched.push({ url, opts }); return Promise.resolve({ ok: true }); },
  setInterval() { intervals += 1; return 7; },
  clearInterval() { intervals -= 1; },
};

// Run heartbeat.js's IIFE with those globals bound.
const keys = Object.keys(sandbox);
// eslint-disable-next-line no-new-func
new Function(...keys, src)(...keys.map((k) => sandbox[k]));

function fire(kind, ev) { (listeners[kind] || []).forEach((fn) => fn(ev)); }

// --- assertions ---------------------------------------------------------------------------
check("beats on load", fetched.some((f) => String(f.url).includes("/api/heartbeat")));
check("periodic beat armed", intervals === 1, `intervals=${intervals}`);

check("pagehide is wired", (listeners.pagehide || []).length > 0);
check(
  "visibilitychange is NOT wired (a tab switch must not arm the fuse)",
  (listeners.visibilitychange || []).length === 0,
);

// bfcache first — it must be silent, and proving that BEFORE the real close rules out a
// harness that simply beacons on everything.
fire("pagehide", { persisted: true });
check("bfcache pagehide sends nothing", beacons.length === 0, `beacons=${JSON.stringify(beacons)}`);

fire("pagehide", { persisted: false });
check("real pagehide beacons", beacons.length === 1, `beacons=${JSON.stringify(beacons)}`);
check(
  "the beacon goes to /api/closing",
  beacons.length === 1 && String(beacons[0]).includes("/api/closing"),
  JSON.stringify(beacons),
);

// sfQuit must still work — this fix must not break the deliberate Quit path.
const before = fetched.length;
sandbox.window.sfQuit();
check("sfQuit stops the beats", intervals === 0, `intervals=${intervals}`);
check(
  "sfQuit still calls /api/shutdown",
  fetched.slice(before).some((f) => String(f.url).includes("/api/shutdown")),
);

if (failures) { console.error(`${failures} failure(s)`); process.exit(1); }
console.log("OK heartbeat close");

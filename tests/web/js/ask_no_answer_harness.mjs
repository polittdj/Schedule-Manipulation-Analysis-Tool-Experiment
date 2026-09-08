// Node-driven harness for the Ask panel's NO-ANSWER branch (the operator's field report).
//
// The Python tests prove the SERVER now says why an ask produced no prose. Only execution
// proves the panel PUTS THAT SENTENCE ON SCREEN. This boots ask.js's IIFE against a minimal
// DOM stub, stubs fetch with a real /api/ask payload, drives the click handler, and asserts:
//
//   * a payload carrying `no_answer` renders the SERVER's reason verbatim — the whole point,
//     since the reason is composed from the operator's own configuration (endpoint, model,
//     timeout) and no client-side string can know it;
//   * the retired blanket sentence is not re-introduced anywhere in the rendered output;
//   * a payload WITHOUT `no_answer` still renders a usable, non-empty line (the panel must
//     degrade, never go blank — a blank answer box is the defect this replaces);
//   * an answered payload still renders the answer and no reason line at all.
//
// Exit code 0 = all assertions hold.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const STATIC = join(here, "../../../src/schedule_forensics/web/static");
const src = readFileSync(join(STATIC, "ask.js"), "utf8");

let failures = 0;
function check(label, ok, extra) {
  if (!ok) {
    failures += 1;
    console.error(`FAIL ${label}${extra ? ": " + extra : ""}`);
  } else console.log(`ok ${label}`);
}

function node(tag) {
  const n = {
    tag,
    attrs: {},
    hidden: false,
    value: "",
    children: [],
    _text: "",
    listeners: {},
    setAttribute(k, v) { this.attrs[k] = v; },
    appendChild(c) { this.children.push(c); return c; },
    addEventListener(kind, fn) { (this.listeners[kind] ||= []).push(fn); },
    classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
  };
  Object.defineProperty(n, "textContent", {
    get() { return this._text; },
    set(v) { this._text = String(v); this.children.length = 0; },
  });
  return n;
}

function rendered(el) {
  return [el._text, ...el.children.map(rendered)].join(" ").replace(/\s+/g, " ").trim();
}

function boot(payload) {
  const ids = {};
  for (const id of ["askBtn", "askOut", "askInput", "askScope", "askExports", "drivePathUid",
                    "drivePathBtn"]) ids[id] = node("div");
  ids.askInput.value = "why did the date not move?";
  ids.askScope.value = "";
  const doc = {
    getElementById: (id) => ids[id] || null,
    querySelector: () => null,
    createElement: (tag) => node(tag),
    createTextNode: (t) => ({ tag: "#text", _text: String(t), children: [] }),
  };
  const fetchStub = () => Promise.resolve({ ok: true, json: () => Promise.resolve(payload) });
  new Function("document", "fetch", src)(doc, fetchStub);
  const click = (ids.askBtn.listeners.click || [])[0];
  if (!click) { check("panel wired a click handler", false); return null; }
  click();
  return ids;
}

const RETIRED = "No local model is active (or strict mode discarded its answer)";
const SERVER_REASON =
  "Ollama is reachable at http://127.0.0.1:12345 but the selected model 'qwen2.5:7b-instruct' " +
  "is not installed — run: ollama pull qwen2.5:7b-instruct";

const FACTS = [{ text: "Schedule frame: 2026-04-15 to 2029-05-30.", citations: [] }];

async function run() {
  // 1. the server's reason reaches the screen, and the retired sentence does not come back
  let ids = boot({ answer: null, mode: "annotate", facts: FACTS,
                   no_answer: { code: "generation_failed", text: SERVER_REASON } });
  await new Promise((r) => setTimeout(r, 0));
  let out = rendered(ids.askOut);
  check("renders the server's reason", out.includes(SERVER_REASON), out.slice(0, 200));
  check("does not print the retired blanket sentence", !out.includes(RETIRED), out.slice(0, 200));
  check("still shows the cited facts", out.includes("Schedule frame"), out.slice(0, 200));

  // 2. a payload with no reason at all still says something usable
  ids = boot({ answer: null, mode: "annotate", facts: FACTS });
  await new Promise((r) => setTimeout(r, 0));
  out = rendered(ids.askOut);
  check("degrades to a non-empty line without a reason", out.replace(/\s/g, "").length > 40, out);
  check("fallback still shows the cited facts", out.includes("Schedule frame"), out.slice(0, 200));

  // 3. an answered payload renders the answer and no reason line
  ids = boot({ answer: "The dates were held.", mode: "annotate", facts: FACTS });
  await new Promise((r) => setTimeout(r, 0));
  out = rendered(ids.askOut);
  check("renders a real answer", out.includes("The dates were held."), out.slice(0, 200));
  check("no reason line on a real answer", !out.includes(SERVER_REASON), out.slice(0, 200));

  if (failures) { console.error(`${failures} failure(s)`); process.exit(1); }
  console.log("OK ask no-answer");
}

run();

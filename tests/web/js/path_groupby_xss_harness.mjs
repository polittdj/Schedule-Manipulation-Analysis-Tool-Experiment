// Node-driven regression harness for path.js populateGroupBy() — the audit's stored DOM-XSS.
//
// A custom-field label / Alias is attacker-controlled free text from an opposing-party schedule
// (MSPDI <Alias> -> custom_field_labels, sent verbatim in the /api/driving JSON). The old
// populateGroupBy string-concatenated it into <option> HTML and assigned innerHTML — a stored
// DOM-XSS running as first-party code in the CUI tool (Law 1). The fix builds options via el(),
// so every label goes through textContent / a real attribute value and never HTML parsing.
//
// This harness brace-extracts el() and populateGroupBy() from the vendored file (closure-private,
// so they cannot be called after the IIFE loads) and drives them against a faithful DOM stub that
// DISTINGUISHES textContent (literal) from innerHTML (would parse). Exit 0 = the fix holds.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(
  join(here, "../../../src/schedule_forensics/web/static/path.js"),
  "utf8",
);

// Extract a top-level `function NAME(...) { ... }` by brace-matching from its declaration.
function extract(name) {
  const start = src.indexOf("function " + name + "(");
  if (start < 0) throw new Error("could not find function " + name);
  let depth = 0,
    i = src.indexOf("{", start);
  const bodyStart = i;
  for (; i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}") {
      depth--;
      if (depth === 0) return src.slice(start, i + 1);
    }
  }
  throw new Error("unbalanced braces for " + name);
}

const PAYLOAD = 'x"><img src=q onerror="globalThis.__xss_fired=true">';

function makeNode(tag) {
  return {
    tag,
    attrs: {},
    children: [],
    _text: "",
    _innerHTML: null,
    _value: "",
    set textContent(v) {
      this._text = String(v);
      this.children = [];
    },
    get textContent() {
      return this._text;
    },
    setAttribute(k, v) {
      this.attrs[k] = String(v);
    },
    appendChild(c) {
      this.children.push(c);
      return c;
    },
    set innerHTML(v) {
      // Record ANY innerHTML assignment; the fix must never route a label through here.
      this._innerHTML = String(v);
    },
    get innerHTML() {
      return this._innerHTML || "";
    },
    set value(v) {
      this._value = String(v);
    },
    get value() {
      return this._value;
    },
  };
}

const select = makeNode("select");
const fakeDocument = { createElement: makeNode };
const data = { custom_field_labels: [PAYLOAD] };
const FIELDS = [
  { key: "unique_id", label: "UID" },
  { key: "custom_evil", label: PAYLOAD, custom: true },
];

const body = extract("el") + "\n" + extract("populateGroupBy") + "\n populateGroupBy();";
// eslint-disable-next-line no-new-func
const run = new Function("document", "$", "data", "FIELDS", body);
run(fakeDocument, () => select, data, FIELDS);

const fail = (m) => {
  console.error("FAIL: " + m);
  process.exit(1);
};

// 1. innerHTML was NEVER assigned (the old sink) — the fix builds options via appendChild only.
if (select._innerHTML !== null) fail("select.innerHTML was assigned: " + select._innerHTML);
// 2. onerror never fired (no HTML parsing of the payload occurred anywhere).
if (globalThis.__xss_fired) fail("XSS onerror fired — the label was parsed as HTML");
// 3. the malicious labels are present as LITERAL textContent, not markup.
const texts = select.children.map((c) => c._text);
if (!texts.includes(PAYLOAD)) fail("custom_field_labels payload not rendered as literal text");
if (!texts.includes(PAYLOAD + " (custom)")) fail("custom FIELDS label not rendered as literal text");
// 4. the custom-field option's value went through setAttribute (a real attribute), not HTML.
const evil = select.children.find((c) => c._text === PAYLOAD + " (custom)");
if (!evil || evil.attrs.value !== "custom:" + PAYLOAD) fail("option value not set via attribute");

console.log("OK: populateGroupBy builds options via textContent/attributes; no innerHTML XSS sink");
process.exit(0);

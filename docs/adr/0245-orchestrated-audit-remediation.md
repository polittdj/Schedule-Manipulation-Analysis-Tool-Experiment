# ADR-0245 — Orchestrated repo audit + remediation of the confirmed defects (ADR-0240 protocol)

## Status

Accepted. Operator-requested overall audit run under the ADR-0240 model/audit protocol (the
multi-agent orchestrated audit with one lead validating every finding against code evidence +
executable tests), on `main` at v1.0.55 (all of PR-R2 / R2.1 / Gantt / R3 merged).

## Context

Seven read-only reviewers (CUI/Law-1, parity/Law-2, security, architecture, tests, docs-state,
deps+UI+data-validation) fanned out; each finding was then handed to an adversarial skeptic that
tried to refute it against the actual code before it survived. Baseline was green (ruff / ruff
format / mypy --strict / bandit exit 0 / node --check / 2,292 pytest passed). **12 findings
survived verification, 0 were refuted.** The lead independently re-verified each, including a
full sweep of every `innerHTML` sink in the vendored JS (only one carried unescaped data).

The two most severe were confirmed by reproduction:

- **BLOCKER — stored DOM-XSS (`path.js`).** A custom-field label / MSPDI `<Alias>` is
  attacker-controlled free text from an opposing-party schedule; it flows verbatim through
  `custom_field_labels` → the `/api/driving` JSON → `populateGroupBy`, which string-concatenated it
  into `<option>` HTML and assigned `innerHTML` — executing as first-party code in the CUI tool. The
  skeptic reproduced it in real Chromium (and disproved its own "the HTML5 in-select insertion mode
  drops `<img>`" near-refutation — the `onerror` fired). With `script-src 'unsafe-inline'` and no
  `navigate-to` directive, CUI exfiltrates via `location=` on any networked machine — a Law-1 breach.
- **HIGH — `/cei` cache staleness (`app.py`).** The Bow Wave / CEI view set the session-wide target
  with a raw `st.target_uid = …` assignment, bypassing `set_target()`, so `_invalidate_scope()`
  never ran: every page kept serving metrics scoped to the PREVIOUS target under a confident,
  contradictory banner (a Law-2 fidelity break), and `sra_focus_uid` desynced from the header.

## Decision

Fix the two HIGH/BLOCKER defects immediately (Law 1/2 are paramount — a confirmed CUI-exfil cannot
sit in `main` between sessions) plus the two small Law-relevant MEDs, each with a regression test;
correct the doc-drift findings; queue the remaining MED/LOW.

**Fixed this change (with tests):**
1. **XSS (BLOCKER):** `populateGroupBy` now builds `<option>`s via the file's own `el()` helper, so
   every label goes through `textContent` / a real attribute value — never HTML parsing. Node
   harness `path_groupby_xss_harness.mjs` brace-extracts and drives the function against a DOM stub
   that distinguishes `textContent` from `innerHTML`; mutation-verified (it fails on the old sink).
2. **`/cei` (HIGH):** the target focus now routes through `st.set_target(...)`, restoring cache
   invalidation + the SRA-focus coupling; a view test changes the target from one UID to another
   and asserts `sra_focus_uid` tracks it.
3. **Margin carry-forward (MED, Law-2):** completes PR-R3's erosion-basis fix — the
   `consumed`/`planned`/`corrective-action` carry-forward now also refuses the cross-basis
   subtraction (an 8h→24h month leaves `planned_margin_wd=None`, so consumed/corrective read NA, not
   a fabricated consumption). Engine tests for both the mixed- and single-basis paths.
4. **Log redaction (MED, Law-1):** `SENSITIVE_EXTENSIONS` gained `doc`/`docx`/`aft`/`pkl`/`pickle`
   (the pre-commit guard treats them as CUI but the redactor omitted them); a test pins
   `SENSITIVE_EXTENSIONS ⊇` the pre-commit `blocked_re` set so the two can never diverge again.

**Doc-drift corrected:** REPO-INVENTORY census (engine 61→63, web 108→110, importers 9→10, parity
4→6); USER-GUIDE stamp v1.0.51→v1.0.56 + the per-task-Gantt-shading note; NEXT-SESSION-PROMPT
rewritten (PR-R3 was queued as "next" though already merged).

**Queued (the audit remainder → HANDOFF NEXT):** the standalone `/driving-path` corridor Gantt is
not per-task shaded (the #382 wiring gap — `driving_path.js` reads an `a.calendar` the server never
emits); a Gantt-shading node harness (the #382 JS is behaviorally untested); a `/margin`
mixed-basis view test; an SRA-xlsx zip-bomb size cap; and a spaced-UNC-path trailing-filename leak
in `redact()` (a subtle regex edge). None is a live CUI leak or parity break.

## Consequences

- The paramount Law-1 hole is closed with a CI-durable (node, not browser) regression guard; the
  Law-2 fidelity bug and the two Law-relevant MEDs are fixed and pinned.
- The audit's refuted-vs-confirmed split is recorded so the queued items are not re-chased and the
  refuted-none result is on record.
- v1.0.55 → 1.0.56; wheel + 9 installers rebuilt in lockstep; HANDOFF / SESSION-LOG refreshed in the
  same commit.

# ADR-0031 — The SSI-style Path Analysis workspace + grounded ask-the-AI

- **Status:** accepted
- **Date:** 2026-06-12
- **Drivers:** operator work order: critical/secondary/tertiary path analysis with
  user-defined day-bands and a target UID, SSI-style presentation (data left, scalable
  Gantt right with the current-date line), MS-Project fields add/remove/filter (incl.
  hide-100%-complete), and the ability to ask the AI questions answered from the data.

## Decision 1 — a dedicated workspace over the existing engine

`/path` (`static/path.js`) is a pure presentation layer over the SSI-parity driving-slack
engine (ADR-0011): the user picks the schedule, the **target UID** (session target
pre-fills), and the **secondary/tertiary day-bands**; `/api/driving` — extended with the
SSI grid fields (WBS, start/finish ISO dates from the CPM ordinals, baseline finish,
duration/total-float days on the schedule's calendar, % complete, resources, and the data
date) — returns the tiered trace. The client renders **data left / timeline right** in one
table (shared row geometry), with add/remove column toggles, row filters (tier, name/UID
substring, hide-completed), and a **zoom slider in pixels-per-day** (horizontal scroll) —
month ticks and the gold **data-date line** drawn on the same axis. Tier colors reuse the
established driving/secondary/tertiary palette; completed bars dim and strike through.

## Decision 2 — grounded Q&A (`ai/qa.py`, `POST /api/ask/{schedule}`)

Questions are answered from a **fact sheet the engine computed** — frame dates, forecasts,
DCMA verdicts, findings, float bands, completion performance — every fact a cited
`CitedStatement` (§6). Selection is term-overlap (`relevant_facts`, ≤12 facts, the frame
fact always leads). The routed local backend may *phrase* an answer from those facts only;
the gate is **subset-strict on figures**: any number in the model's reply that does not
appear in the fact sheet discards the whole answer and the user sees the facts themselves
(Law 2 — the tool never presents an invented number; a softer 1:1 `reattach` gate cannot
apply to free-form Q&A). The offline Null backend skips generation entirely: matching
facts, verbatim. The model's prose, when shown, is labeled model-generated with the facts
beneath it. The question and the data never leave the machine.

## Consequences

646 tests expected green (12 new: the cited fact sheet, relevance, the figure-subset gate
incl. fabrication/dying-model cases, the page controls, the extended driving fields, and
the ask endpoint's Null/model/404/422 behaviors); parity 10/10 untouched; `path.js` joins
the air-gap scan; zero new dependencies.

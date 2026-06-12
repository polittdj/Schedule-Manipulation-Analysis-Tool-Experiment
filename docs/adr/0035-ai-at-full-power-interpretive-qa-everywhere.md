# ADR-0035 — AI at full power: interpretive Q&A, the ask panel on every page, the standing disclaimer, the Briefing reformat

Date: 2026-06-12 · Status: accepted

## Context

The operator's M18 order: *"relax the figure-discard gate; Ollama does brief-tone
interpretation/analysis in real time; 'Ask the AI' panel on ALL pages (workbook-wide
facts on multi-version pages); cite computed figures; standing 'AI can err — verify
against citations' disclaimer."* Until now the ask panel existed only on the Path
Analysis page, and any model answer containing a figure the engine had not computed was
discarded wholesale (ADR-0031) — correct for fail-closed defaults, but it also blocked
legitimate derived analysis ("the spread between the three forecasts is N days").

## Decisions

1. **Two answering modes** (`AIConfig.qa_mode`; AI Settings select; **interpretive is
   the default** per the order, strict remains selectable):
   - *interpretive*: the model may compute differences/ratios from the cited facts and
     explain implications — derived figures are allowed. The prompt confines it to the
     fact sheet as evidence and tells it to say when the facts are silent.
   - *strict*: the ADR-0031 wholesale figure-discard gate, unchanged.
   Both modes are **prose-only relaxations**: the cited facts shown with every answer
   are engine-computed, the Null backend still answers with facts verbatim, and a
   failed/empty generation still degrades to facts (never an error).
2. **The standing disclaimer is structural, not per-answer**: the panel itself carries
   *"AI can err — verify against citations"* permanently, and interpretive answers
   repeat it beneath the prose.
3. **One shared ask panel in the page shell** (`_ask_panel_html`, `static/ask.js`),
   rendered on every page once schedules are loaded, with a **scope select**: the whole
   workbook or any single loaded version. A page with a natural schedule context
   (report) pre-selects its schedule; the Path-Analysis-local panel is removed (the
   shell panel replaces it — same element ids, same `/api/ask/{name}` endpoint).
4. **Workbook-wide facts** (`ai.qa.build_workbook_fact_sheet`, `POST /api/ask`): the
   multi-version fact base reuses the Diagnostic Executive Briefing's deterministic,
   fully-cited statements (workbook frame, cross-version quality trend, per-project
   summaries and DCMA verdicts) plus the latest consecutive pair's manipulation
   signals and the newest version's three finish forecasts. One loaded version routes
   to its full single-schedule fact sheet.
5. **What does NOT change**: the report-narrative and briefing rephrase gates
   (`reattach` — figures preserved exactly, citations never dropped) — those surfaces
   are verbatim evidence, not Q&A; and **loopback-only egress** (Law 1) — both modes run
   on the same local routing (`route_backend`, fail-closed; air-gap tests extended over
   `ask.js`).

6. **Executive Briefing readability reformat** (same PR): `BriefingSection` carries a
   ``kind`` ("lede" | "trend" | "project" | "quality") and an optional structured,
   cited ``BriefingTable`` (``row_citations`` align 1:1 with rows — §6 holds for table
   rows exactly as for prose). The page renders the workbook summary as a lede
   paragraph, the cross-version trend and per-project DCMA verdicts as cited tables,
   and the project summaries as side-by-side cards (polished prose + a profile strip).
   The backend polishes **prose only** — table figures are engine data, never touched;
   ``to_text``/exports keep the prose statements unchanged.

## Still open (next PR in the order)

The second OpenAI-compatible local backend (LM Studio / llamafile class) with the
dual-model cross-check/collaboration mode.

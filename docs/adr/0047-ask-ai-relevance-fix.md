# ADR-0047 — Ask-the-AI returns the same facts regardless of the question (fix)

Date: 2026-06-16 · Status: accepted

## Context

The operator reported that **"Ask the AI" gives the same results no matter what you ask**.
The tool is air-gapped: with no local Ollama backend installed the answer is the **Null
backend** path, which returns the engine's **cited facts that match the question** (no LLM
prose ever leaves the machine — §6.D). So "Ask the AI working" depends entirely on
`relevant_facts(facts, question)` actually selecting *question-specific* facts.

It didn't. Two defects in `relevant_facts`:

1. **Padding dominated the result.** After collecting the term-matched facts it ran
   `if len(keep) < min(limit, len(facts)): keep += <leading facts>` — padding every result
   back up to the 12-fact cap with the **same leading facts**. Measured on golden P5
   (29 facts): two unrelated questions returned **9 of 12 identical** facts, so the panel
   looked the same regardless of the question.
2. **Matching was too literal.** Raw whole-word overlap missed obvious intent: "findings"
   didn't match "Finding" (no stemming), and core forensic vocabulary ("late" / "slip" /
   "delay" / "risk") never matched the facts that phrase it as "behind" / "variance" /
   "forecast" / "float".

## Decision

Rewrite `relevant_facts` (in `ai/qa.py`) — engine-only, still no generation, nothing leaves
the machine:

1. **No more padding.** The frame fact always leads; then **only** the facts whose
   stems/aliases actually overlap the question, ranked by overlap. A focused question yields
   a focused, question-specific selection. When **nothing** matches (a genuinely vague
   question) it falls back to a small bounded **headline overview** (`_OVERVIEW_FACTS = 4`),
   never the whole sheet.
2. **Plural/suffix stemming** (`_stems`): "findings" → "finding", "constraints" →
   "constraint", "forecasts" → "forecast", so question words reach the matching facts.
3. **Forensic-intent aliases** (`_INTENT_ALIAS`): a question word *prefix* (e.g. `slip` →
   "slipping"/"slippage") adds substrings to look for in the fact text ("behind", "variance",
   "forecast", …), so the analyst's vocabulary reaches the facts that carry the answer.
   Prefix keys avoid false positives (`late` no longer matches "related"); alias values are
   matched as case-insensitive substrings, sidestepping the light stemmer entirely.

## Scope / safety

`relevant_facts` is the only behavior change; the **figure gates are untouched** — strict
mode still discards any model number not in the facts, interpretive mode still grounds in and
ships the cited facts, and the Null/failed paths stay fail-closed. The fact *content* and the
citations are unchanged, so nothing new can leave the machine. Verified on golden P5: six
distinct questions now return six distinct, on-topic selections (unrelated questions share
only the always-leading frame fact); "hard constraints" → just the Hard-Constraints fact;
"findings/problems" → the `Finding` facts; "slipping/late" and "progress" → the
forecast / completed-behind / variance facts. Two regression tests pin the per-question
variation and the stemming/alias intent matching; the existing figure-gate and
workbook-fact-sheet tests are unchanged. Parity untouched (no engine/CPM change).

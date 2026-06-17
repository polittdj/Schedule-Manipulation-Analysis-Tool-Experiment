# ADR-0058 — Ask-the-AI: hand the local model the full cited picture (free analysis, still local)

Date: 2026-06-17 · Status: accepted

## Context

Operator feedback: **"Fix the Ask the AI on each page so you can ask it anything about the
data and it gives the best analysis/interpretation"** and **"fully release Ollama to analyze
and interpret the data to the best of its ability."** When asked how far to relax the
air-gap, the operator chose **free analysis, stay 100% local** — let a local model interpret
freely, but keep the strict loopback-only egress (no schedule data ever leaves the machine).

ADR-0047 already made the *displayed* facts question-specific (fixing "same answer no matter
what you ask" on the Null path). But the interpretive mode default was only ever feeding the
**model** the same trimmed, ≤12-fact slice that the analyst is shown (`relevant_facts`). On a
narrow question the model therefore saw a narrow slice and could not reason across the whole
schedule — so even with Ollama running, the analysis was thin and felt same-y.

## Decision

In `ai/qa.py`, separate **what the analyst is shown** from **what a live model is given**:

1. **`model_evidence(facts, question)`** — the whole cited sheet, frame fact first, then every
   other fact ordered by relevance to the question (cap `_MODEL_MAX_FACTS = 48`, comfortably
   above a single schedule's fact count). The shared scorer is factored out as
   `_question_overlap` so `relevant_facts` (what is *shown*) and `model_evidence` (what is
   *fed*) can never drift.
2. **`answer_question` (interpretive)** now prompts the model with the full evidence and a
   senior-analyst instruction: answer directly, you MAY compute differences/ratios/trends from
   the facts and explain what drives the slip / where the risk is, name risks and suggest
   concrete recovery actions, never state data the facts do not contain. The analyst is still
   *shown* the question-relevant `relevant_facts` slice (uncluttered), with the standing
   "AI can err — verify against citations" line.
3. **Strict mode is unchanged**: it still sees only the shown facts and discards wholesale any
   answer containing a figure those facts do not contain.
4. **Richer evidence**: `build_fact_sheet` now states the **finish-driving activity count**
   (how many activities complete on the computed finish, zero float to the end) — a cited fact
   for "critical path" questions.
5. **Discoverability**: the ask panel and the no-model message link to **AI Settings** to
   enable a local Ollama model for full written analysis.

## Scope / safety

The loopback-only air-gap is **untouched**: `OllamaBackend` still rejects any non-loopback
endpoint (`CUIEgressError`), `route_backend` still fails closed to the local Null backend, and
cloud is still refused for CLASSIFIED projects. "Free analysis" relaxes only how much *local*
evidence the *local* model sees and how it is prompted — no schedule data leaves the machine,
and the cited facts always ride alongside every answer. No engine/CPM/metric change, so
**parity is untouched (10/10)**. New tests pin: the finish-driving fact, that `model_evidence`
is the full relevance-ordered sheet, and that interpretive mode feeds the model more facts
than it shows the analyst; the existing figure-gate, relevance, and workbook tests are
unchanged.

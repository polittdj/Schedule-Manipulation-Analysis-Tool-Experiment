# Schedule Manipulation Analysis Tool

> **Status: greenfield — Phase 0 scaffold complete, awaiting Gate 1.** `main` was reset to
> a clean starting point on 2026-06-05; session **A1** then laid the durable-state scaffold
> and the reference-intake folder on branch `claude/intelligent-fermat-3MBqk`. The previous
> build remains in git history (and in PR #47) but is intentionally **not** on `main` — it
> is a reference, not a source to copy. Current state of the build always lives in
> [`docs/STATE/HANDOFF.md`](./docs/STATE/HANDOFF.md).

A local, NASA-themed **forensic schedule-analysis** desktop tool. It ingests native
Microsoft Project / Primavera schedules, runs comparative and forensic analysis
(CPM / driving slack, DCMA, manipulation-trend detection, parity to Acumen Fuse v8.11.0
and SSI), and produces interactive, locally-rendered reports with a local AI narrative.
It runs **entirely on the local machine**.

## The two laws

1. **Data sovereignty (CUI).** No schedule data, file content, task name, date, UniqueID,
   or derived metric ever leaves the local machine. No cloud API call ever receives
   schedule content. Default to local Ollama; fail closed when in doubt.
2. **Fidelity over speed.** Numbers must match the reference tools (Acumen Fuse v8.11.0,
   SSI, Microsoft Project) on the same inputs. A fast, wrong number is worthless in a
   forensic/testimony context.

## How this build is run

This tool is built autonomously across many sessions. Everything you need is in two files
at the repo root:

- **[`AUTONOMOUS-BUILD-PROMPT.md`](./AUTONOMOUS-BUILD-PROMPT.md)** — the paste-ready build
  prompt. Paste its full contents into the **first** session (named **A1**), running on
  **Opus 4.8 (1M context)** with **Ultracode**.
- **[`AUTONOMOUS-BUILD-SETUP-CHECKLIST.md`](./AUTONOMOUS-BUILD-SETUP-CHECKLIST.md)** —
  environment/settings prerequisites and the per-session run workflow.

Sessions are named sequentially `A1, A2, A3, …`. Each session does exactly **one
milestone**, writes a durable handoff to `docs/STATE/HANDOFF.md`, and stops; every later
session is resumed with a single stable resume line (see the prompt). All build state lives
in git, never only in chat history.

## What is retained on this clean `main`

- `AUTONOMOUS-BUILD-PROMPT.md`, `AUTONOMOUS-BUILD-SETUP-CHECKLIST.md` — the build spec.
- `.gitignore` — hard CUI defense (blocks every schedule-bearing format and runtime data
  directory from ever being committed).
- `tools/mpxj/` — the vendored, self-contained **MPXJ native `.mpp` reader** (prebuilt
  jars + the compiled `MpxjToMspdi` converter). It parses native `.mpp` with only a Java
  runtime — no Maven, no build step — and is auto-discovered by the importer. Kept because
  parsing native `.mpp` without conversion is a core requirement.

Everything else (the prior application code, tests, reports, and harness config) was
removed; session **A1** rebuilds the project from the prompt.

## Build state & where to look

- **`docs/STATE/HANDOFF.md`** — single source of truth for "where we are / what's next."
- `docs/STATE/SESSION-LOG.md` — append-only per-session history.
- `docs/PLAN/BUILD-PLAN.md`, `docs/PLAN/RTM.md` — plan + requirements traceability (stubs
  until the Phase 2 plan session).
- `docs/adr/` — architecture decision records · `docs/risks.md` — risk register.
- **`00_REFERENCE_INTAKE/DEPOSIT-HERE.md`** — what to deposit at **Gate 1** (reference and
  golden-parity files). Everything dropped there is git-ignored (CUI defense).

## Getting started

1. Read `AUTONOMOUS-BUILD-SETUP-CHECKLIST.md` and decide **where** to run (CUI-sensitive
   reference files must not go into a cloud/web session).
2. Open session **A1** on Opus 4.8 (1M context) + Ultracode, pointed at this repo.
3. Paste the full contents of `AUTONOMOUS-BUILD-PROMPT.md` and follow the gates.

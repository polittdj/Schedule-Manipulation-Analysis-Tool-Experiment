# HANDOFF.md — AISMAT Portfolio/Data-Integrity prompt-authoring session

**Status:** COMPLETE for this session's actual ask (read-only prompt authoring). Nothing built yet.
**Model / meter:** claude-sonnet-5 (Cowork). `CONTEXT_CEILING` set to 1,000,000 per Papicito's explicit
statement this session — UNVERIFIED against Anthropic's actual published spec, treated as a working
assumption per his instruction. token_audit.py written to `/mnt/user-data/working/` (recreate if a future
session finds the container wiped — it always is between sessions).

## Goal
Papicito dumped a large, unstructured set of new feature asks (Portfolio page w/ NASA site map, multi-file
project-grouping by MPP metadata, duplicate/revision detection, Where-We-Stand per-file correctness, Gantt
filter-button bug + task-search feature) plus new session-governance rules (850K/1M token stop, HANDOFF
cadence). Task was explicitly **read-only, no code, no repo changes** — restructure it into an executable,
phased master prompt so a future Claude Code session can build it without blowing context or re-litigating
already-known facts.

## What was done
- Confirmed no live repo is mounted in this sandbox — "the repository" available for this task was the
  Claude Project's own doc set. Read all AISMAT/SMAT planning docs already in the project (HANDOFF,
  NEW-SESSION-PROMPT, CLOUD-ENV-PACKAGE, ROLES-AND-ORCHESTRATION, UI-CLAUDE-DESIGN-NOTE, SMAT-MASTER-PROMPT,
  SMAT-SANDBOX-SETUP, SMAT-DEEP-DIVE-ANALYSIS) to avoid re-deriving established facts (roster, two laws,
  operating loop, token economy, known backlog items U1–U4, P1–P10, C1–C5).
- Confirmed via `project_search` that "Portfolio page," "Where We Stand page," MPP Company-field grouping,
  and duplicate-file detection are **not** documented anywhere in this project yet — these are genuinely new
  requirements, not something a prior session already scoped. Flagged as UNVERIFIED against the live app
  everywhere it matters (see the new master prompt's §8).
- Authored `claude/AISMAT-PORTFOLIO-DATA-INTEGRITY-MASTER-PROMPT.md` (delivered to project + Papicito):
  restates every requirement from the raw prompt, grouped into Phase 0 (mandatory recon) → 1 (file-grouping
  and dedup data model) → 2 (per-file page correctness / no-mixing-outside-Portfolio) → 3 (Portfolio page +
  candidate metrics) → 4 (Gantt filter fix + task search) → 5 (ongoing hardening), plus a governance section
  reconciling the 850K/1,000,000 token rule and formalizing the HANDOFF cadence as a standing rule.
- Deliberately tied new asks into **existing** backlog items instead of creating parallel scope: Gantt
  fixes → U2 (inline handlers) + U3 (shared charting module); "make it look cool" → U1 (design tokens);
  duplicate-file "no silent failures" → same principle as existing importer defects P4/P5.

## Decisions (with why)
- **850K (not the generic 90%) is the hard stop for this workstream** — Papicito's explicit instruction this
  session overrides the standing 90%-of-ceiling default; more conservative number wins where they conflict.
- **New project doc, not an edit to SMAT-MASTER-PROMPT.md or ROLES-AND-ORCHESTRATION.md** — this is a
  separate workstream layered on top; the existing docs stay canonical for roster/laws/token-economy and are
  referenced, not duplicated, to keep this new doc lean.
- **Portfolio metrics proposed, not committed** — Papicito asked me to "come up with" them; I proposed a
  candidate list reusing already-established metric vocabulary (BEI/CEI/HMI/CPLI/DCMA-14) rather than
  inventing new formulas, and flagged they need FLIGHT+SCHED sign-off before Phase 3 build starts.

## File inventory (this session)
- `/mnt/user-data/working/token_audit.py` — token guardian meter, recreated per standing instruction.
- `/mnt/user-data/working/HANDOFF.md` — this file.
- `/mnt/user-data/working/AISMAT-PORTFOLIO-DATA-INTEGRITY-MASTER-PROMPT.md` — the deliverable, also saved to
  the project at `claude/AISMAT-PORTFOLIO-DATA-INTEGRITY-MASTER-PROMPT.md` and sent to Papicito directly. Now
  at v2: added §0.1 (repo confirmed at v1.0.66/PR #396/ADR-0257, ~90 PRs past the prior audits — every old
  `file:line` is presumptively stale), §7 (reproduces Papicito's separate Deep Performance next-session prompt
  in full, with explicit cross-references into §2–§5 so both workstreams don't collide on `web/app.py`'s
  cache/lock machinery), §8 (placeholder for the promised Claude Design prompt — not yet received; confirmed
  what the `DesignSync` tool / `/design-sync` skill actually does — pushes local component previews **up** to
  a claude.ai Design-System project, does not pull a design down into the repo), and renumbered old §7→§9 with
  the Playwright browser-verification + wheel/installer-lockstep rules folded in from the Deep Performance
  prompt's working rules.

## Open questions / UNVERIFIED (full list is in the master prompt's §10 — not duplicated here in full)
- Whether Portfolio/Where-We-Stand pages and routes exist yet, under what names.
- Real MPXJ/XER field names for Company/Title-style project metadata.
- Actual symptom of the filename-equals-folder-name bug (unreproduced).
- Which existing JS module (if any) is the "version comparison animation" Papicito referenced.
- Real context ceiling for claude-sonnet-5 in this Cowork environment (1,000,000 is Papicito-asserted only).
- Whether the Gantt filter-button bug (§5) is the same control PR #396's "alphabetical filters/groups
  dropdowns" already touched — a regression, a different surface, or already fixed.
- Full scope of the promised Claude Design prompt (§8) — awaiting Papicito's paste, not yet received.

## Deferred / declined prompts
- None outright declined. One item is **awaiting input, not deferred by choice**: Papicito said a "Claude
  design prompt" is coming to fold in as well — it has not been pasted yet as of this update. §8 is scaffolded
  as a placeholder so the next pass drops it straight in instead of re-deriving context.

## Carry-over rules (unchanged, restated for the next session that reads this file)
Run token_audit.py each turn; keep this file current continuously, not just at the trip point. Two laws +
sandbox guard + verification rules 1–7 always apply once code work starts. Persona: "Hola Papicito!", sassy in
chat / clean in repo and project files, no glazing, stress-test first, attack every plan before building it.
The separate CLOUD-ENV-PACKAGE workstream (see `claude/AISMAT-HANDOFF.md`) is still PENDING and unrelated to
this one — don't conflate the two when picking up work.

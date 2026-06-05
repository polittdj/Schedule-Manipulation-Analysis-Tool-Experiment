# Autonomous, Multi-Session Build — Schedule Manipulation Analysis Tool

> **Paste-ready prompt.** Paste the entire contents of this file into the **first**
> session only (session **A1**). Every later session is started with the single
> **stable resume line** in §2 — you do not re-paste this prompt.

You are the lead engineer building a local, NASA-themed forensic schedule-analysis
desktop tool. This is a **long, multi-session build**. Operate autonomously **within**
each session, but assume your current context may be lost at any moment (compaction,
timeout, or session end). Therefore **externalize all state to disk and git** and work
**one milestone per session**. Your north star: deliver every requirement in §6.A–§6.G —
find a way to succeed no matter how many sessions or tokens it takes. When something is hard,
escalate effort (extended thinking, sub-agents, more tests), never assumptions.

---

## 0. Absolute guardrails (never violate)

1. **CUI / NASA data.** Treat every schedule file (`.mpp` `.mpt` `.xer` `.xml`
   `.pmxml` `.mpx` `.csv` `.xlsx`) and every derivative as Controlled Unclassified
   Information by default. You may **never** access the user's NASA computer or any file
   the user has not explicitly placed in the reference-intake folder for this build. No
   schedule data, parsed derivative, prompt, or narrative may ever leave the local
   machine (no cloud API, telemetry, analytics, or remote git). If any deposited file's
   CUI status is unclear, **stop and ask** before reading it.
2. **No silent cloud egress.** The shipped tool defaults to local Ollama. A cloud LLM
   may only be reachable if the user explicitly toggles a project to "unclassified," and
   even then a persistent banner must name the external endpoint. Never auto-fall back to
   cloud.
3. **No CUI in git.** Schedule files, parsed pickles, and generated reports are
   git-ignored and never committed. Tests use synthetic fixtures only.
4. **Gates are hard stops.** At the end of Phase 0 and Phase 1 you STOP and wait for the
   user to reply `GO`. Do not continue past a gate on your own.
5. **Destructive ops are reversible.** Do the greenfield wipe on a new branch and a
   draft PR; preserve `.git` history. Never force-push `main`.

---

## 1. Operating principles

- **Quality is the constraint, not speed.** Apply the QC/PM regime in §7 from the first
  commit — tests, types, lint, CI, traceability, and the parity suite are not optional.
- **Use Claude Code's full toolbox.** Begin in **plan mode** when planning; spawn
  **sub-agents in parallel** (Explore agents to analyze reference files; Plan agents for
  architecture; general-purpose agents to implement independent modules concurrently);
  keep a live **TODO list**; run long jobs (model pulls, full test suites) as
  **background tasks**; use **extended thinking** for parity and CPM edge cases.
- **Never skip a requirement.** Maintain a Requirements Traceability Matrix (§7) and do
  not declare done until every row is `Implemented + Tested + Validated`.
- **Cite everything.** Every metric, finding, path, and AI sentence the tool emits must
  carry, at minimum, **file name + UniqueID + task name**, so the user can verify it in
  the parent `.mpp`.

---

## 2. Session & handoff discipline (READ FIRST, EVERY SESSION)

This build spans many sessions. Treat the repo — not your context window — as the source
of truth.

### 2.1 Session identity, model, and mode (fixed for the whole build)

- **Every session runs on Opus 4.8 (1M context) with Ultracode enabled.** Do not run a
  build session on any other model or without Ultracode. If you find yourself on a
  different model or mode, STOP and tell the user to restart the session correctly before
  doing any work.
- **Sessions are named sequentially: `A1`, `A2`, `A3`, … `An`.** `A1` is the first
  session (this prompt). Each session records its own ID at the top of its
  `SESSION-LOG.md` entry, and `HANDOFF.md` always names **the session that just ran** and
  **the next session ID to use**. If you cannot tell which session number you are, read
  the last `SESSION-LOG.md` entry and add 1.
- **One session = one milestone.** Never attempt two milestones in a single session.

### 2.2 Session-length / timeout / compaction discipline (HARD RULE)

Sessions are time- and length-limited. A session can **time out** mid-operation or
**compact** (silently drop in-context history) if it runs too long or too hot. You must
engineer every session to finish with comfortable margin:

- **Size milestones to fit one session with margin.** Before starting, estimate the work.
  If a milestone might not finish with room to spare, **split it in `BUILD-PLAN.md`** and
  do only the first part this session. It is always correct to do less per session.
- **Stop early, not at the edge.** The moment your context grows large, a long operation
  looms (model pull, full parity run), or you sense you are more than ~70% through a
  comfortable session budget, **proactively trigger the end-of-session ritual (§2.5) and
  stop.** Never run a session to its hard limit — a timeout can lose your last,
  un-committed decisions.
- **Externalize as you go.** Commit after each meaningful unit; write decisions to ADRs
  and `HANDOFF.md` **at the moment you make them**, never batched for the end. Assume the
  session may die on the next tool call.
- **Long operations are background tasks.** Run model pulls and full test/parity suites
  as background tasks; do not block a foreground turn on them long enough to risk an idle
  timeout.
- **Avoid stream-idle timeouts on big files.** Author any file longer than ~3,000 words
  by appending in chunks (create with the first section, then append section by section),
  not in one giant write.

### 2.3 Canonical durable state (always in git, always current)

- `docs/PLAN/BUILD-PLAN.md` — full plan + the ordered milestone list (each milestone
  scoped to fit comfortably in one session).
- `docs/PLAN/RTM.md` — requirements traceability matrix (every §6 item → design → module
  → test → parity evidence → status).
- `docs/STATE/HANDOFF.md` — **single source of truth for "where we are / what's next."**
  Overwritten at the end of every session. A fresh session must be able to fully resume
  from this file alone.
- `docs/STATE/SESSION-LOG.md` — append-only history; one dated entry per session (session
  ID, milestone, what changed, commit SHAs, test/parity status, decisions, blockers).
- `docs/adr/NNNN-*.md` — Architecture Decision Records for significant choices.

### 2.4 Start-of-session ritual (do this before anything else)

1. Read `docs/STATE/HANDOFF.md`, then `docs/PLAN/BUILD-PLAN.md` and `docs/PLAN/RTM.md`.
2. Confirm you are on Opus 4.8 (1M context) with Ultracode, on the right repo/branch;
   run the test suite to confirm a green baseline.
3. Determine your session ID (`A<n>` = last logged session + 1) and restate, in one line,
   the single milestone you will complete this session.

### 2.5 End-of-session ritual — trigger it PROACTIVELY

Trigger when the milestone is done **or** the moment context grows large / a long
operation looms (stop with margin; never run to the edge):

1. Update `docs/PLAN/RTM.md`.
2. Overwrite `docs/STATE/HANDOFF.md` using the template below — concrete and
   self-sufficient.
3. Append a dated entry to `docs/STATE/SESSION-LOG.md` (tagged with this session's `A<n>`
   ID and the next session ID `A<n+1>`).
4. Commit + push; update the draft PR.
5. STOP and print the **stable resume line** (below) for the user.

### 2.6 HANDOFF.md template (keep it concrete)

```
# Handoff — <date>
This session: A<n>     Next session: A<n+1>
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: <Phase 0 | awaiting Gate 1 GO | Phase 1 | awaiting Gate 2 GO | Phase 2 | DONE>
Repo/branch: <...>     Green baseline: <pass/fail + how to verify>
Completed this session: <bullets + commit SHAs>
Parity status: <Acumen/SSI suite pass-rate snapshot>

## Next session (do exactly this)
- Milestone: <id + name>
- Acceptance criteria: <list>
- Files to create/modify: <list>
- First 3 concrete steps: <1> <2> <3>

Open questions / blockers: <list or "none">
```

### 2.7 Stable resume line (the user pastes this to start each new session)

> Resume the autonomous build on a new session named A<next> using Opus 4.8 (1M context)
> with Ultracode. Read docs/STATE/HANDOFF.md and continue exactly per its "Next session"
> section, following every rule in this repo's build prompt.

---

## 3. Units & formatting (global, non-negotiable)

- All durations are expressed in `day` / `days`.
- All percentages render with the sign, e.g. `100%`.
- Internal storage may use minutes for precision; convert to days only at the
  presentation boundary with deterministic rounding (no binary-float drift).

---

## 4. PHASE 0 — Greenfield wipe + intake + state scaffolding → then STOP (Gate 1)

Confirm you are in `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment`. Then:

1. Create a working branch (e.g. `claude/greenfield-init-YYYY-MM-DD`).
2. Wipe the repo to clean greenfield (remove all tracked files; keep `.git`).
3. Lay down a minimal scaffold:
   - `README.md` (name, purpose, "local-only / CUI" notice, status: greenfield).
   - `.gitignore` blocking all schedule extensions, parsed pickles, exports, model blobs,
     upload/work folders.
   - `LICENSE` placeholder, `pyproject.toml` stub, empty `src/`, `tests/`.
   - The **durable-state skeleton**: `docs/PLAN/BUILD-PLAN.md` (stub),
     `docs/PLAN/RTM.md` (stub), `docs/STATE/HANDOFF.md`, `docs/STATE/SESSION-LOG.md`,
     `docs/adr/`.
   - Reference-intake folder named exactly **`00_REFERENCE_INTAKE/`** containing
     **`DEPOSIT-HERE.md`**.
4. Write `00_REFERENCE_INTAKE/DEPOSIT-HERE.md` as a manifest telling the user exactly what
   to deposit and to confirm each item is **non-CUI / sanitized** first. Request:
   - The **`.pbix`** reference (extra metrics, how they're calculated, example visuals —
     you are encouraged to expand/improve on these).
   - The **two Microsoft Project `.mpp`** files that were compared.
   - **Acumen Fuse v8.11.0**: the comparison output **and** raw per-file **result
     exports** (golden numbers to match).
   - **SSI** driving-path / driving-slack exports for a chosen target UniqueID (golden
     numbers to match).
   - The **Acumen Fuse metrics library** (formulas for every metric/measure).
   - Any data dictionaries, sample reports, NASA UI/theme references.
5. Produce a **gap list** of anything else you need to guarantee success.
6. Initialize `HANDOFF.md` to `Phase/Gate: awaiting Gate 1 GO` (this session `A1`, next
   session `A2`) with the gap list and the exact next steps for Phase 1.
7. Commit, push, open a **draft PR**.
8. **STOP.** Report the branch/PR, the exact intake folder + file names, the manifest, and
   the gap list. Go no further until the user deposits files and replies `GO`.

---

## 5. PHASE 1 — Direct the user on setup → then STOP (Gate 2)

On `GO`, run the start-of-session ritual, then:

1. Verify each deposited file is present, readable, and confirmed non-CUI. If anything is
   missing/ambiguous/possibly CUI, list it and ask.
2. Analyze the `.pbix`, the Acumen metrics library, and golden Acumen/SSI exports (use
   Explore sub-agents in parallel). Extract: the full metric/measure catalog with
   formulas, the driving-slack methodology, example visuals, and the exact target numbers
   the parity suite must reproduce. Record findings in `docs/PLAN/`.
3. Produce a written **setup direction**: every Claude Code setting, permission, hook,
   add-on, environment prerequisite, and mode the user should enable for an autonomous,
   compliant build (see the companion `AUTONOMOUS-BUILD-SETUP-CHECKLIST.md` for the
   baseline), plus anything specific to what you found.
4. Run the end-of-session ritual (update HANDOFF to `awaiting Gate 2 GO`), then **STOP**
   and wait for the user to apply settings and reply `GO`.

---

## 6. PHASE 2 — Plan, then build across many sessions → final report

On `GO`:

1. **Plan session.** Produce the full `docs/PLAN/BUILD-PLAN.md` (architecture + ordered,
   session-sized milestones) and the complete `docs/PLAN/RTM.md` covering every item in
   §6.A–§6.G. Then run the end-of-session ritual and stop.
2. **Build sessions (repeat).** Each session: start-of-session ritual → implement the one
   next milestone with TDD → run lint/types/tests/parity → update RTM → end-of-session
   ritual → stop with a resume line. Continue across as many sessions as needed until
   every RTM row is `Implemented + Tested + Validated`.
3. **Validate.** The parity suite (§6.B) must pass: the tool's numbers must match the
   golden Acumen Fuse v8.11.0 and SSI exports exactly; where an exact match is genuinely
   impossible, document the precise delta with citations and treat it as a defect to drive
   to zero.
4. **Final session.** Provide the desktop launcher, user guide, metric dictionary
   (formulas + citations), and a final report mapping every requirement to its evidence.
   Open/refresh the draft PR; do not merge. STOP.

---

## The build contract — the tool's functional requirements (referenced throughout as §6.A–§6.G)

### A. Platform, UX, and packaging

- All parsing/analysis/metrics/forensics in **Python**.
- Launches from a **desktop icon**; runs **100% locally**; opens in a **web browser**.
- **Dark-mode**, NASA-themed, highly intuitive UI for a NASA scheduler.
- **Interactive, Power-BI-style** visuals: graphs, charts, Gantt views that are polished
  and let the user **add/remove fields** and **drill into the underlying metadata** of any
  data point. Bundle all viz/JS assets locally (air-gapped; no CDN).
- In-tool **help & explanations**: instructions plus a plain-language definition of every
  metric, measure, and analysis, each with supporting detail (UniqueIDs, task names,
  source file) so results can be fact-checked in the parent documents.

### B. Ingestion & parity (non-negotiable)

- Parse and analyze **up to 10 native `.mpp` files at once**, **without converting** them
  first, with access to **all underlying metadata** in each file.
- **All metrics, measures, and results must exactly match Acumen Fuse v8.11.0** for the
  same inputs, **and** match the **SSI** MS Project add-on's outputs. A parity test suite
  against the golden exports is the acceptance gate.
- Cross-version matching is by **UniqueID only** (never row ID, never name).

### C. CPM, driving slack & path tracing (SSI parity)

- Critical path via forward/backward pass; total float, free float, **driving slack**.
- Let the user enter any **target UniqueID** → it becomes the focus point / endpoint of
  the "critical path"; trace the **driving logic path** to it and report **Driving Slack
  in days for each task exactly as SSI does** — results equal MS Project + SSI for the same
  project and UniqueID.
- At upload, let the user set the **day thresholds** for **secondary** and **tertiary**
  paths.

### D. Forensic & trend analysis

- A local AI model **"generates a story"** and insights, including **CPM trend analysis**
  and **schedule-manipulation trends** (e.g., deleting logic, shortening durations,
  deleting tasks to keep a target UniqueID or the critical path from slipping) — plus any
  other useful, easy-to-understand industry-standard analysis you can add. Every AI
  statement carries citations (file, UniqueID, task name).

### E. Independent audits & recommendations

- Audit each schedule independently for **DCMA compliance** with suggested improvements.
- Identify **risks, opportunities, and areas of concern**, each with a suggested course of
  action. **For all data, provide citations** (≥ file name, UniqueID, task name).

### F. Local AI backend

- **Ollama is the default** local model. The tool must let the user **download additional
  local models and switch the active model in-app** (settings panel: list installed
  models, pull new ones, select active). Pick a default model suited to a high-end
  workstation; quality may be traded for performance. No cloud by default.

### G. Data locality

- The tool **transfers no data off the machine** (CUI). All compute is local/offline.

---

## 7. Quality-control & project-management regime (industry standard)

Apply throughout:

- **RTM** (`docs/PLAN/RTM.md`): each §6.A–§6.G requirement → design → module → test →
  parity evidence → status. Nothing ships unverified.
- **TDD + pytest**; coverage gates (engine ≥85%, overall ≥70%).
- **Static quality**: `ruff` (lint+format), `mypy` (types), `bandit` (security),
  `pip-audit` (deps). A network-egress guard test fails if forbidden HTTP libs import.
- **CI** (GitHub Actions): lint + types + tests + security + parity on every push; red
  blocks merge.
- **Version control**: feature branches, Conventional Commits, **draft** PRs, no
  force-push to `main`, a Definition-of-Done checklist per PR.
- **ADRs**, a **risk register** (`docs/risks.md`), and a change log for scope changes.
- **Structured logging with CUI redaction** (paths/counts/timings only).
- **Docs**: user guide, metric dictionary (formula + citation per metric), parity report.

---

## 8. Definition of done

Every §6.A–§6.G requirement is `Implemented + Tested + Validated` in the RTM; the parity suite
matches the golden Acumen v8.11.0 and SSI exports; CI is green; the desktop launcher starts
the local web UI; docs are complete; `HANDOFF.md` reads `DONE`; and a final report cites
the evidence for each requirement. Then STOP and present a draft PR.

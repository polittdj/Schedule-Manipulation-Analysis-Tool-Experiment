# Setup Checklist — autonomous, multi-session build (CUI-safe)

Do these before pasting the prompt, then use the per-session workflow in §G.

> **Every session in this build runs on Opus 4.8 (1M context) with Ultracode enabled, and
> is named sequentially `A1`, `A2`, `A3`, … `An`.** `A1` is the session where you paste
> the full prompt; each later session is started with the stable resume line and the next
> `A<n>` number. Keep these two settings (model + Ultracode) identical across every
> session — they are not per-task choices.

---

## A. CUI safety — decide WHERE the build runs (most important)

- Your reference `.mpp` files and Acumen/SSI exports may be **CUI**. Do **not** upload CUI
  into a cloud/web Claude Code session.
- If any reference file is CUI: run with a **local, offline Claude Code** install on an
  authorized machine, working directory **outside OneDrive sync** (e.g.
  `C:\Tool\...\workspace\`).
- If you can fully **sanitize/synthesize** the reference + golden files, a hosted session
  is acceptable. When in doubt, run locally.

---

## B. Claude Code settings (autonomy without losing control)

- **Model**: **Opus 4.8 (1M context)** for every session. Do not downgrade between
  sessions — the build's quality and parity work assume the most capable Opus-class model
  with the 1M-token window.
- **Mode**: **Ultracode enabled** for every session (exhaustive, correct-over-fast,
  multi-agent orchestration).
- **Permission mode**: *Accept Edits* or a curated allowlist in `.claude/settings.json`
  for `git` (add/commit/branch/checkout/push), `python -m pytest`, `ruff`, `mypy`,
  `bandit`, `pip install`, `ollama`. Avoid blanket "skip all permissions."
- **Plan mode** and **sub-agents** enabled (the prompt parallelizes them).
- **Pre-commit hook** blocking schedule extensions + parsed pickles (CUI defense).
- **GitHub MCP** enabled so Claude can open the draft PRs the prompt requires.

---

## C. Local prerequisites on the build machine

- **Python 3.12+** and a virtual environment.
- **Ollama** running on `localhost:11434` with at least one capable model pulled; verify
  the tool can list/pull/switch models.
- **MS Project** only if you want the win32com native-read path; otherwise install a
  **JDK** for the Java-based **MPXJ** native `.mpp` path (no MS Project needed). Claude
  picks whichever reproduces the golden numbers.
- **Git** configured; GitHub access for PRs (code only — never schedule data).

---

## D. Reference materials to have ready (Claude requests these at Gate 1)

- The **`.pbix`** metrics/visuals reference.
- The **two compared `.mpp`** files.
- **Acumen Fuse v8.11.0**: comparison output **and** raw per-file result exports.
- **SSI** driving-path / driving-slack exports for a chosen target UniqueID.
- The **Acumen Fuse metrics library** (formulas).
- Any NASA UI/theme references, data dictionaries, sample reports.
- Confirm each item is **non-CUI / sanitized** before depositing.

---

## E. Repo settings

- Keep **auto-merge disabled**; all Claude PRs open as **draft**.
- Enable **branch protection** so CI must pass before merge.

---

## F. Why multi-session — and how it stays lossless

- The tool is large; one session cannot build it without context compaction or timeout.
- The prompt makes the build **multi-session by design**: all state lives in git
  (`docs/PLAN/BUILD-PLAN.md`, `docs/PLAN/RTM.md`, `docs/STATE/HANDOFF.md`,
  `docs/STATE/SESSION-LOG.md`, `docs/adr/`). Each session does **one milestone**, then
  writes a handoff and stops. Nothing important ever lives only in chat history.
- **Sessions are sized to never hit the limit.** Each milestone is scoped to finish a
  single session with margin; Claude stops early (end-of-session ritual) the moment
  context grows large or a long operation looms, so a timeout or compaction can never lose
  an un-committed decision. Create as many `A<n>` sessions as the build needs — there is no
  penalty for more, smaller sessions.

---

## G. How to run it (per session)

1. Apply A–E above.
2. Open a session pointed at
   `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment`, on **Opus 4.8 (1M context)**
   with **Ultracode** on.
3. **Session A1 only:** paste the full contents of `AUTONOMOUS-BUILD-PROMPT.md`.
4. At **Gate 1**, deposit the reference files into `00_REFERENCE_INTAKE/`, reply `GO`.
5. At **Gate 2**, apply the setup direction Claude gives you, reply `GO`.
6. **Every later session (`A2`, `A3`, …):** start a fresh session on Opus 4.8 (1M context)
   + Ultracode and paste the stable resume line —
   > Resume the autonomous build on a new session named A<next> using Opus 4.8 (1M
   > context) with Ultracode. Read docs/STATE/HANDOFF.md and continue exactly per its
   > "Next session" section, following every rule in this repo's build prompt.
7. Each session ends by committing a handoff and printing that same resume line (with the
   next `A<n>` number). Repeat until `docs/STATE/HANDOFF.md` reads `DONE`. Review the final
   draft PR.

---

## H. Session ledger (optional, handy)

Track sessions as you go so you always know the next `A<n>`:

| Session | Date | Milestone | Result | Next |
|---------|------|-----------|--------|------|
| A1 | | Phase 0: greenfield + intake → Gate 1 | | A2 |
| A2 | | Phase 1: setup direction → Gate 2 | | A3 |
| A3 | | Phase 2: plan (BUILD-PLAN + RTM) | | A4 |
| A4… | | one build milestone each | | … |

(The authoritative record is always `docs/STATE/SESSION-LOG.md` and
`docs/STATE/HANDOFF.md` in git; this table is just a convenience.)

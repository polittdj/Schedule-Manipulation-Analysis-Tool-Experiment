# Handoff — 2026-09-24 (b) (R-13 **CLOSED** — every AI transaction record carries a format version and a random per-process run id (ADR-0528) — **v1.0.291**)

STATUS (current) — branch **`claude/tender-ptolemy-ua1y6k`**, restarted on `main` @ **`a65e1b21`** after #715 (ADR-0527, v1.0.290) squash-merged 2026-09-24; the squash tree `2a1addb2…` is BYTE-IDENTICAL to the PR head bf810775's tree, and all eight checks on that head were read to conclusion green (main's own post-merge runs NOT read — check them). This unit ships as a new **draft PR the OPERATOR merges**: ADR-0528, v1.0.291, `src/` changed so the wheel + nine installers were rebuilt as the LAST step and **EIGHT checks** apply. Highest ADR **0528**. Version **1.0.291**. Schema **2.17.0**. QC-1 / QC-2 / QC-3 bind every session.

## What landed

**R-13** (operator ruling 2026-09-24: a correlation id is acceptable — it carries no CUI). `ai/txlog.py`'s one writer adds `v` (`FORMAT_VERSION = 1`) and `run` (`RUN_ID = secrets.token_hex(8)`, drawn once per process — no name, path, host, or schedule content) to every record. /settings' gateway-ON sentence names both. TX-02's closed key vocabulary re-baselined 10 → 12, dated.

## How it was verified

QC-3: the writer census (every `txlog.` / `LOG_FILENAME` / `ai-transactions` / `jsonl` reference) found ONE writer and one caller — held. Red-first 3/3. Mutation 3/3 red by name; the load-bearing finding: a **hostname-derived** run id passes a literal "names nothing" check and is killed ONLY by the test that spawns two real interpreters.

## Not done · carried forward

Old log lines are not migrated (no `v` = the pre-version shape, by definition). No per-browser-session id (a different question, not ruled). Carried from ADR-0527: 20 / 7,161 windowed Compare labels still clip; M23b (the ADR-0446 month-letter threshold); the UI-control census cannot see a plain form. **Next:** R-18 · R-21 · R-22 · R-32 · R-39; R-71's record limbs; R-68 waits on the operator.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.

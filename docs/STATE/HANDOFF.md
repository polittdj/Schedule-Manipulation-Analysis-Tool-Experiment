# Handoff — 2026-07-25a (perf #5 MPP capability probe; v1.0.100; highest ADR 0293)

> ## STATUS (current) — perf backlog **item 5 of 7** done. Version **1.0.100**. Highest ADR **0293**.
> Branch `claude/smat-tool-continuation-uskbh7` (fresh from `origin/main` at `0f5bec2` after PR #437
> / ADR-0292 squash-merged).
>
> - **ADR-0293 — the measurement KILLED two of the three obvious fixes. Read the table before
>   re-opening any of this.** Perf item 5 was recorded as five words ("an MPP capability probe"), so
>   the first job was finding out whether it names a real cost. Measured on the committed reference
>   `Project2.mpp` (691,712 B), interleaved + repeated per ADR-0292:
>   - `_find_java()` costs **~0.3 ms** — memoising it process-wide buys microseconds and a
>     stale-answer hazard. **Rejected.**
>   - `/upload` entry → first conversion is **97 ms** — there is nothing to overlap a background JVM
>     pre-warm with. **Rejected.**
>   - A first (order-dependent) reading said the batch JVM was **1.4 s SLOWER** at N=1 (2.99 s vs
>     1.58 s). Interleaved: **1.52 s vs 1.49 s** at N=1, **2.71 s vs 11.74 s** at N=8. Cold page
>     cache on the MPXJ jars — the exact ADR-0292 trap, caught the same way. The batch JVM is fine.
> - **The cost that survived is I/O, not CPU.** On a machine that cannot convert `.mpp` at all (no
>   JRE, or a deploy missing `tools/mpxj`) the upload path spills EVERY file to a temp path before
>   discovering, once per file, that no subprocess will ever read it. Measured **16 files →
>   3,200,064 B written then discarded**; the operator's real files are ~10 MB, so a 500-file folder
>   is **~5 GB** of pointless writes.
> - **Fix:** `MppCapability(mpxj_home, java, reason)` + `probe_mpp_capability()` +
>   `mpp_capability()`, the last returning the probe **cached on the active `mpxj_batch_session()`**.
>   Ingest-scoped, NOT process-wide — that is what makes the cache safe: install a JRE and the next
>   upload re-probes, so there is no long-lived answer to invalidate. `parse_mpp` and the upload
>   `.mpp` branch gate on it before any temp directory exists.
> - **Measured after:** discovery **(8, 9) → (1, 1)** calls per 8-file ingest; doomed temp writes
>   **3,200,064 B → 0**. Both failure messages and their ORDER (runner outranks JRE) unchanged; a
>   real `.mpp` parses identically batch vs one-shot (Law 2).
> - **Tests:** `tests/importers/test_mpp_capability_probe.py` (7) — **6 of 7 fail on the pre-change
>   tree** (verified by stashing the diff), including the two quantitative pins above.
> - **Gate:** ruff/format/mypy-strict/bandit clean; full suite **2,659 passed** (the only failure was
>   the expected wheel-staleness guard, cleared by regenerating); wheel + 9 installers at 1.0.100.
> - **DEFERRED ON PURPOSE, named in the ADR:** surfacing the probe in the UI ("native .mpp is
>   unavailable on this machine — here's the fix"). It is real value and `mpp_capability()` is now
>   the hook for it, but it is UI work owing the DESIGN-SYSTEM Definition-of-Done (ADR-0195);
>   folding it into a perf PR would smuggle a UI change past that gate.
> - **ITEM 6 IS ALREADY MEASURED — do not re-profile, implement from this table.** MSPDI,
>   21.45 MB / 2,126 tasks / 433,254 elements, **unprofiled medians** (cProfile inflates ~1.4x —
>   the profiler said 2,721 ms where the real total is 1,410 ms; use these numbers, not a profile):
>   | phase | ms | % |
>   |---|---|---|
>   | `ET.fromstring` | **913** | **64.7%** |
>   | `_parse_task` x2126 | 182 | 12.9% |
>   | unattributed (baselines, pydantic `Schedule`, `_in_file_links`) | 179 | 12.7% |
>   | `_strip_namespaces` | **114** | **8.1%** |
>   | `_build_links` | 15 | 1.1% |
>   | `_parse_assignments` | 5 | 0.4% |
>   | **TOTAL** | **1,410** | |
>   **Four hypotheses tested and KILLED (do not re-try):** (a) parse **bytes** to skip a
>   decode/re-encode — `fromstring(bytes)` is **945 ms vs 894 ms** for `str`, i.e. *slower*;
>   (b) **selective parsing** — `Tasks` is **78.7%** of the DOM (`Assignments` 12.4%, `Calendars`
>   7.6%), so there is no large discardable section; (c) **per-Task `{tag: text}` dict** instead of
>   `Element.find()` — saves **13.7 ms of 1,410 (1%)** because `find` is already C; (d) **lxml** —
>   3-5x faster but a binary dep embedded in 9 installers, against the air-gap/packaging posture.
>   **The ONE hypothesis that survived:** skip `_strip_namespaces` when the document declares
>   exactly one namespace (`text.count("xmlns") == 1` costs **7 ms**; it is **1** in the fixture) by
>   removing the single default declaration before parsing → **114 ms / 8.1%**, with an equality pin
>   proving both paths build identical `Schedule`s. **XER is unmeasured** — the only fixture is
>   2 KB / 0.3 ms; a large real `.xer` is needed before touching that importer.
> - **NEXT — perf items 6-7:** **(6)** importer profiling — measured above, implement the namespace
>   skip; **(7)** the **`web/app.py` monolith split** (~19k lines — its OWN behaviour-free PR). Also
>   still open: the dashboard
>   `status_mix_uids` payload trim (ADR-0291's named residual — the dashboard equivalent of
>   ADR-0288). Then **AXIS-TITLES-PATCH**, then **CRISPNESS 11px floor** (⚠️ RE-GROUND: its §2.1
>   claim that `sf-themes.css` "was never committed" is FALSE — it exists, 4,576 B, 36 custom
>   properties, linked in `_LAYOUT`), then GUIDED-MODE (5 decisions) + VOICE-DECISION (4 decisions),
>   both parked on the operator.
> - **STILL FLAGGED, not changed unilaterally:** `_ANALYSIS_CACHE_MAX = 48` → ~348 MiB worst case at
>   7.2 MiB/entry (ADR-0292). Lowering it trades memory for recomputation on the operator's hardware.
> - **DEPLOY NOTE:** the operator has **no local clone** — `cd`+`git pull` FAILED for them. Download
>   `installer/install-tier2.ps1` from the GitHub web UI and run
>   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.

# Handoff — 2026-07-25b (perf #6 CLOSED as a decision: importer left alone; highest ADR 0294)

> ## STATUS (current) — perf backlog **item 6 of 7 closed**. Version **1.0.100**. Highest ADR **0294**.
> Branch `claude/smat-tool-continuation-uskbh7` (fresh from `origin/main` at `339da47` after PR #439
> / ADR-0293 squash-merged).
>
> - **⚠️ THE PREVIOUS HANDOFF WAS WRONG AND ADR-0294 CORRECTS IT.** It told you the MSPDI namespace
>   pre-strip was "the ONE hypothesis that survived — 114 ms / 8.1%, implement it." **It does not
>   survive.** I implemented it (guarded, Law-2 clean, byte-identical `Schedule`s) and then reverted
>   it, because the end-to-end A/B does not reproduce the component estimate:
>   - `fromstring` namespaced **922.6 ms** vs plain **915.4 ms** → the parse-side saving is **7 ms**.
>     ElementTree's namespace handling is almost free; the whole benefit had to come from skipping
>     the Python walk.
>   - The pre-strip must rebuild the 21 MB string (**52.9 ms**) and scan it for `xmlns` (**7.4 ms**)
>     — **60.3 ms of new work** eats most of the 114 ms walk it removes.
>   - Real `parse_mspdi_text` A/B, interleaved: **wall-clock −28.7 ms (−1.8%)**, inside the noise
>     (samples 1,503–4,989 ms); **CPU median −55.5 ms (−3.6%) but min-to-min −8.0 ms**. When the
>     median and the minimum disagree 7x, it is allocator/GC state, not less work.
>   - **LESSON (already promoted): a component measurement prices what you REMOVE. It does not price
>     what you ADD in its place. Always close the loop with an end-to-end A/B of the real function.**
> - **Item 6 is CLOSED as a decision (ADR-0294), not as an omission.** Five hypotheses tested and
>   rejected — **do not re-try any of them**: (a) parse bytes not str (945 vs 894 ms — *slower*);
>   (b) selective parsing (`Tasks` is **78.7%** of the DOM — nothing large to discard); (c) per-Task
>   `{tag: text}` map instead of `Element.find()` (**13.7 ms of 1,410 = 1%**, `find` is already C);
>   (d) **lxml** (3-5x faster but a binary dep in 9 installers — declined on ADR-0290 grounds);
>   (e) the namespace pre-strip above. The profile: `ET.fromstring` **913 ms (64.7%)** ·
>   `_parse_task` 182 ms · unattributed 179 ms · `_strip_namespaces` 114 ms · `_build_links` 15 ms ·
>   TOTAL **1,410 ms**. If the importer ever must get faster, the only target worth the risk is the
>   **65% inside `ET.fromstring`** — i.e. a different parser, not a micro-optimisation.
> - **Method note for anyone re-measuring:** cProfile inflates this workload **~1.4x** (reports
>   2,721 ms where the real total is 1,410 ms) and over-weights many-small-calls helpers (`_text`
>   fires 236,698 times). Use it for *where*, never for *how much*.
> - **XER stays unmeasured on purpose:** the only fixture is 2 KB / 0.3 ms. A large real `.xer` is
>   needed before that importer is touched. A gap, not a result.
> - **NEXT — the remaining perf work:** **(7)** the **`web/app.py` monolith split** (~19k lines — its
>   OWN behaviour-free PR, no functional change in the same diff), and the dashboard
>   **`status_mix_uids` payload trim** (ADR-0291's named residual — the dashboard analogue of
>   ADR-0288's trend trim; the lazy-segment pattern is already built and proven, so this is the
>   tractable one). Then **AXIS-TITLES-PATCH**, then **CRISPNESS 11px floor** (⚠️ RE-GROUND: its §2.1
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

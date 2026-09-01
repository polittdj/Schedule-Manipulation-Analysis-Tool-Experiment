# Handoff — 2026-09-01 (operator-reported header defect: the timescale's EDGE bands were unclamped — they overlapped at the left and bled past the right; ADR-0444, v1.0.226)

> ## STATUS (current) — **On branch `claude/polaris2-audit-resume-3xg50n` (from `main` @ `489cf976`). WP0/WP1/WP2 are all MERGED; this is an operator-reported defect fix on top. QC-1/QC-2 bind every session — ADR-0393, pinned by `tests/test_standing_rules.py`.**
> Highest ADR **0444**; version **1.0.226** (shipped code: `static/timescale.js`); wheel + nine
> installers rebuilt in lockstep. Campaign queue is unchanged — **WP3 (M4, the SRA grid)** is next.
>
> ## What the operator reported, and what was actually found
> The operator sent a screenshot of `/path` on their 2,301-activity / 12.3-year IPMR with two files
> open: "the time line headers are still screwed up". Probing that page found a real defect in the
> header's band geometry — **`tierBands` clamped one edge and measured the width from the other**:
> `left` was clamped with `Math.max(0, left)` while `w = right - left` used the UNCLAMPED left, and
> `right` was never clamped to `axis.width`. A span almost never starts or ends on a unit boundary,
> so the first and last bands are PARTIAL units drawn a FULL unit wide.
>
> Measured at their scale (1920x1080, two files): the `2017` band rendered 0..81px while `2018`
> starts at 47px — a **34px overlap, two year labels drawn over each other** — and the last band ran
> to **1026px against a 969px axis**, 57px past the header's own right edge (`scrollWidth` 1026 vs
> `clientWidth` 969), bleeding over the column beside it. Overflow scales with width: 11px @ 240px
> axis, 33px @ 488, 57px @ 969, 95px @ 1609. **Not long-span-only** — any span whose ends are off a
> unit boundary hits it. Fixed by clamping BOTH edges and taking the width from the clamped edges;
> band rights now tile exactly (`47, 129, … 945, 969`) and the 24px edge sliver correctly narrows
> its label to `'29`.
>
> ## Proof
> Red-first BY NAME (`fitted: g-tier g-tier-yr runs 33px past the axis (488px)`); green after; **each
> clamp mutation-proved INDEPENDENTLY** (right clamp reverted → "runs 33px past"; left clamp feeding
> the width reverted → "bands overlapping by 23px") so the test has two sets of teeth. Neighbour
> veto: 47 browser tests green across long-span / timescale-dialog / row-windowing / gantt-consistency
> / dd-line-render. The byte-pin modules that glob `static/*.js` were swept BY PIN SHAPE, not by
> filename (the ADR-0443 lesson) — none tripped; only the installer-lockstep guard fired, as expected
> for a shipped-JS change, and the wheel + nine installers were rebuilt LAST.
>
> ## OPEN — the operator's symptom is NOT reproduced, and this is UNVERIFIED as their fix
> Their screenshot shows a **three-row** header whose year labels appear to cascade diagonally. Every
> reproduction here — 2,301 activities, 12.3-year span, two files, widths swept 1100→2560 — produced a
> structurally sound **two-row** header with zero page errors, because `effectiveStack` promotes
> Months→Quarters at that span and dedupes. So ADR-0444 fixes a real defect IN the component they
> reported, but whether it is the whole of what they see is **UNVERIFIED**.
> **Ask them for exactly these three, from the machine showing the fault, both files open:**
> 1. the version banner — are they actually on >=1.0.225, or a build predating the ADR-0441 header work?
> 2. `localStorage.getItem("sf.timescale.v1")` — the persisted tier config that decides the row count.
> 3. a dump of `.g-scale-tiered .g-tier` (class, computed `top`) plus the first few `.g-band`
>    label/left pairs — the one thing a screenshot cannot give.
>
> ## Next — campaign queue (unchanged)
> **WP3** (M4 SRA grid edit / paste-from-Excel / save round-trip) → **WP4** (route-coverage instrument
> + the 08-26 `startup_failure` root-cause) → **WP5** (BOTH folder builds) → **WP6** (ledger highs:
> CPM-01 · CPM-02 · MC-02 · MC-03 · MAN-01 · REC-02) → **WP7** (thin dims, `ai/txlog.py` first) →
> **WP8** (consolidated report + roadmap by testimony risk).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.

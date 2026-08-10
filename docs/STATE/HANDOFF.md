# Handoff — 2026-08-10 (phase 3 slice 16: the /scurve family out — the member BOTH instruments missed; ADR-0380; v1.0.188)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-phase3-slice14-uhqmyv`
> (branch restarted from `main` 88a8d37 after #564 squash-merged — this container's designated
> branch; the branch NAME says slice14, the WORK is slice 16). **Shipped code changed** — version
> bumped **v1.0.187 → v1.0.188** BEFORE the suite; wheel + nine installers rebuilt once after the
> last code change (SCHEMA stays 2.11.0 — no persisted field changed). Highest ADR now
> **ADR-0380**.
>
> **Phase-3 slice 16 is CLOSED (queue item 1): the /scurve family → NEW `web/scurve.py`**
> (283 lines; **seven movers in TWO contiguous blocks**, app.py 8324–8530 and 9016–9040:
> `_scurve_filter_fields` · `_pair_criteria` · `_scurve_status_point` · `_scurve_interpretation`
> · `_scurve_header` · `_scurve_body` · `_scurve_data`) and **NO descent**. app.py
> **11,095 → 10,871** wc-truth. `LAYER_ORDER` `… → performance → resources → scurve → app`;
> the re-export block lands BELOW resources' (isort: resources < scurve < sra); scurve.py joins
> the pyproject E501 list; EXTRACTED + LAYER_ORDER + VIEW_MODULES + both whole-view-layer guard
> tuples gain "scurve.py".
>
> **HEADLINE — the census's blind spot and the ORACLE's were the SAME member.** The closure is
> 13 names / 250 ast lines; the movers are **7 / 222** against the prefix census's **6 / 212**
> (1.05× lines, 1.17× names). The extra name is **`_pair_criteria`** — the cf/cv validator
> reachable only from `/api/scurve`, carrying no `_scurve` prefix. It was ALSO invisible to the
> inherited 644-label oracle, for an unrelated reason: **no inherited label supplies cf/cv**, so
> it did no work on any of the 648 renders. Two independent instruments, two independent causes,
> ONE member — because both blindnesses share a root: the member is off the obvious path.
> *A census miss is a warning about the ORACLE, not just the queue.*
>
> **No descent, adjudicated by referrer.** Six shared names, all pinned to app.py: `_parse_uid`
> · `_parse_uid_list` (pinned by NON-route referrers `_drill_uid_set` / `_import_risk_register`)
> · `_parse_track_uids` (pinned by /cei's routes) · `_MAX_TRACK_UIDS` (cohesion) ·
> **`_CF_QUERY` / `_CV_QUERY`** — FastAPI `Query` singletons that exist only as route-signature
> defaults and are referenced by NO mover. Checked mechanically: across **220 extracted names /
> 15 slices, not one** route-signature default has ever lived in an extracted module. Route
> plumbing stays with the routes; presentation moves. **The export contributes NO movers**
> (`export_scurve` builds from `compute_s_curve`) — that streak is now TWO consecutive.
>
> ## Verification
> Oracle **EXTENDED 644 → 648**, never re-based: one label added, `[scurve-filter]
> /api/scurve?cf&cv`, whose payload-change is asserted BEFORE it is recorded. The inherited 644
> reproduce ADR-0379's fingerprint EXACTLY on the pristine tree (`[empty]` 60 {200:41,400:17,
> 422:2} · four loaded stages 146 each {200:123,404:4,422:19} · 4xx **69/88/111**) — including
> the `404:4` ADR-0379 had to repair. The extension moves loaded stages to 147 / `200:124` and
> **leaves the 4xx fingerprint unchanged**, which is what proves it purely additive. Determinism
> ×2 separate processes: **0 flapping** at both 644 and 648. Pre-flight probe **7/7
> render-proven, ZERO dark** (seventh consecutive) — `_scurve_data` 8 · `_pair_criteria` 4 (the
> NEW label only; 0/648 without it) · the other five 4 each. **Stronger-anchor round fired:**
> `_scurve_status_point` first read 3/4 because `[target]` renders 100% vs 100% and the anchor
> was a SWAP — a permutation is the identity on equal values. Re-run with an ADDITIVE marker it
> reads 4/4. *Mutate by offset, not by permutation.* Proof: per-region byte-identity IDENTICAL
> (in-script, from disk, and again after `ruff --fix` dropped app.py's now-unused `SCurve`;
> `sha256 4811f34f46cb…`) · **648/648 byte-identical pristine vs cut** · falsified in the new
> location **7/7 EXACT label lists** (anchors also asserted ABSENT from post-cut app.py) ·
> multiset 306 added / 237 removed with **236 of 237 removed lines reappearing verbatim — ZERO
> member code lines removed** (the one exception is the s_curve import NARROWED by ruff, its
> edited form present as an addition). Sweeps: dropped-import by BARE NAME (`SCurve`) **0
> readers**; monkeypatch/attr (AST, alias-agnostic) over all 19 bound names **ZERO hits** (192
> setattr calls found, ADR-0378's control reproduced; **no ADR-0297 trap** — `compute_s_curve` is
> called by the ROUTES, which stay, and every test imports it straight from the engine);
> source-text sweep 6 python-source readers → one candidate (`'scurve.js'` at
> test_dd_line_ledger.py:74) **adjudicated FALSE** (a static-JS ledger key, not app.py markup) →
> **zero repoints**. Battery **6/6 named** (1/39 ×4 · 1/5 · 1/6; enumeration guard's 23rd/24th
> consecutive catches). Full suite **3550 passed / 45 skipped, exit 0** (+2 vs slice 15's 3548
> — the two parametrized contract cases scurve.py adds). Parity **52 passed / 15 skipped,
> exit 0**; all skips environment-gated. Statics green (python -m ruff check WHOLE TREE ·
> format --check 944 files zero reformats at the final gate, 943 at cut time · mypy strict
> 134 · bandit exit 0 · node --check 60/60).
>
> ## Next
> The queue resumes at phase-3 slice 17 — by the post-cut prefix census (wc-truth; each family
> owes its OWN closure, membership NAMED because the prefix is a finder): **path 194** (incl.
> `_what_drives_header` 80) · **compare 166** (incl. `_what_changed_header` 79) — EACH per the
> ADR-0365 recipe (closure before cut · span-scoped probe · six-mutation battery · the ADR-0372
> oracle recipe). **The oracle to inherit is now 648 labels with the `[scurve-filter]` label**;
> fmts are xlsx/docx, `{name}` keys drop the `.xml`, /openapi.json is the 60th parameterless GET.
> groups (430 by prefix) stays OUTSIDE the phase-3 list while ADR-0343 feature work is queued.
> Then the standing queue unchanged: stored-SRA-fields MSPDI fixture · driving-corridor fixture ·
> three page-lede-less pages (/briefing, /path, /compare) · /groups Activities (ADR-0343) ·
> installers vs known-good constraints · P80/P90 recurring-exception residual · doc-drift sweep
> (PARITY-REPORT git-ignored claim + Project2 "CUI intake"; FINAL-REPORT blanket "exact match";
> CLAUDE.md phase-3/E501 lines — scurve.py now ALSO joins the E501 list unpatched there) ·
> ~150 MB RSS per loaded file · Phase 6 docs. **Operator:** re-convert FX-03/04 (verify
> UID17=5d / UID131=1w before save) + re-run Fuse · one Acumen run on a crafted
> sub-day-negative-float schedule · license · branch-protection contexts · proprietary reruns ·
> OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0380 closed — do not re-open. NEW this session: (1) **a census miss is a warning
> about the ORACLE too** — the name a finder cannot see is disproportionately the name an
> instrument cannot exercise, because both follow from the member being off the obvious path;
> check the second instrument whenever the first one misses. (2) **Mutate by OFFSET, not by
> PERMUTATION** — a swap has fixed points, and a scoped or fully-progressed population is exactly
> where the values coincide (`_scurve_status_point` read 3/4 at 100% vs 100%). (3) **Zero
> precedent is evidence**: 220 extracted names over 15 slices carried no route-signature default,
> which is what pinned `_CF_QUERY`/`_CV_QUERY` to app.py. (4) A probe mutation that DISABLES a
> member can trip the oracle's own render-condition guard — mutate the VALUE it produces instead,
> so the guard stays meaningful during every probe run. Standing traps unchanged (a census can be
> exact and still not be membership · a page-only anchor understates an export-feeding member ·
> route-only referrers never force a descent · sweep by BARE NAME · a quiescence guard can match
> its own shell · fingerprints carry their SCOPE · /openapi.json is the 60th parameterless GET ·
> a normalizer that fails silently is a flap factory · never MEASURE a tree a battery is
> mutating · the monkeypatch adjudication list grows as families move · census families can be
> phantoms · ruling-lag headers move retroactively · the installer lockstep guard makes the
> rebuild a PREREQUISITE of the final suite · patch the patcher with landed-count discipline ·
> `#:` blocks extended by eye · silent-405 setup · ADR-0259 dedupe vs memo · round-half-even
> 240→0 · MSPDI re-derives Duration · env-defect masquerade · binding-wrap spies · named-failure
> rule · empty sweep needs a positive control · `grep -c` exits 1 on zero · three-tier parity
> evidence · B608 house nosec · pydantic 2.6 / fastapi 0.110.2 floors · five playwright-only
> failures pre-existing, CI-invisible · oracle telemetry normalized by VALUE · scratchpad
> harnesses hardcode the repo root · two ruffs on PATH — run `python -m ruff`). A number written
> mid-session is not a measurement (wc decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.

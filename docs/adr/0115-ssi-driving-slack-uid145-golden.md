# ADR-0115 — Re-pin SSI driving-slack parity on the authoritative Project5 (focus UID 145)

- Status: accepted
- Date: 2026-06-23
- Supersedes/relates: ADR-0011 (driving-slack SSI parity), ADR-0112 (refresh Project5 golden to the
  authoritative file), ADR-0003/0005 (Project5 non-CUI commercial-construction sample)

## Context

ADR-0112 refreshed the committed Project5 golden to the **authoritative** `Project5_TAMPERED.mpp`
(4 stored-critical activities, not the prior file's 37). The existing SSI driving-slack golden
(`tests/fixtures/golden/ssi_uid143/`) had been validated by the SSI MS Project add-on on the **prior**
Project5 with focus **UID 143**, so against the authoritative file it became stale and its two parity
tests were marked `xfail` (`tests/parity/test_parity_gate.py::test_ssi_driving_slack_exact`,
`tests/engine/test_driving_slack.py::test_golden_ssi_driving_slack_parity`). Since then the parity gate
has carried **no live SSI assertion** — a gap for a tool whose contract is parity with Acumen Fuse
v8.11.0 **and** SSI.

The operator supplied a fresh SSI **Directional Path Tool** run for the authoritative file with focus
**UID 145** (*"Issue final request for payment"*), in two configurations:

1. *Get dependencies with Driving Slack ≤ 0 d* + 2 near paths → a filtered view: Path 01 (driving,
   0 d) = {144, 145}; Path 02 (1 d) = {131, 142, 143}; Path 03 (20 d) =
   {96, 100, 107, 135, 138, 139, 140, 141}.
2. *Get all dependencies* (near paths off) → the full driving-slack map: **108 UniqueIDs** (focus +
   every transitive predecessor).

These are derived metrics on the **non-CUI** Project5 sample (ADR-0003/0005 — the same sample whose
driving-slack is already committed as `ssi_uid143`), so the derived numbers are committable; the source
`.mpp`/`.xlsx` are **not** (Law 1 — read locally, never committed).

## Decision

Re-establish a **live** SSI driving-slack parity assertion on the authoritative file:

1. Commit `tests/fixtures/golden/ssi_uid145/case.json` — the SSI *all-dependencies* Driving Slack
   (whole working days) keyed by UniqueID (108 entries), plus the focus name, the driving path
   (slack 0 d = {144, 145}), and the default-band tier distribution.
2. Add `test_ssi_driving_slack_uid145_exact` to the parity gate (`@pytest.mark.parity` via the module
   mark) and `test_golden_ssi_driving_slack_uid145_parity` to the engine suite, both asserting
   `compute_driving_slack(Project5, target_uid=145)` matches the golden **exactly** — same UniqueID set
   (no extras, none missing), every whole-day value equal, all slacks whole-day multiples, focus at 0 d
   on the driving path, the driving path = {144, 145}, and tier counts DRIVING=2 / SECONDARY=3 /
   TERTIARY=8 / BEYOND=95 (default 10/20-day bands).

The engine reproduced the export **bit-for-bit on the first run** (108/108 UniqueIDs, zero mismatches),
so this is a certification of existing behaviour, not an engine change. `driving_slack.py` is untouched.

## The stale `ssi_uid143` xfails are left as-is (not fabricated to pass)

This export is focus **UID 145**, not 143. A directional-path analysis is anchored at its focus task
(the backward pass starts at the focus's early finish), so a focus-145 run does **not** yield the
focus-143 driving-slack map. Re-pinning `ssi_uid143` would require an SSI export with **focus UID 143**
on the authoritative file, which we do not have. Per Law 2 we do not invent it; both `ssi_uid143`
xfails stay documented-stale (ADR-0112). Note, however, that the new UID-145 parity match proves the
**engine** is correct on the authoritative file — so the `ssi_uid143` staleness is purely a
golden-vs-file-version mismatch, not an engine defect.

## Consequences

- The parity gate again carries a **live, exact SSI driving-slack assertion** (focus 145) on the
  authoritative Project5, closing the SSI gap that ADR-0112 opened.
- `ssi_uid143` remains the documented-stale placeholder for a future focus-143 re-pin; no behaviour
  change there.
- Future: an SSI focus-143 export on the authoritative file would lift the two `ssi_uid143` xfails by a
  trivial golden re-pin (same pattern as this ADR).

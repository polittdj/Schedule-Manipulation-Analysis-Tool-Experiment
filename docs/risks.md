# Risk register

Living list of build/product risks per the §7 QC/PM regime. Each risk: ID,
description, likelihood/impact, mitigation, status. Updated as sessions proceed.

| ID | Risk | L | I | Mitigation | Status |
|----|------|---|---|------------|--------|
| R-01 | **CUI egress** — schedule data or a derivative leaves the machine (cloud LLM, telemetry, remote git, accidental commit). | Low | Critical | Default local Ollama; `.gitignore` blocks all schedule formats + the intake folder (fail closed); planned network-egress guard test; no cloud unless project explicitly toggled "unclassified" with a persistent banner. **Build-time:** reference intake into this hosted session is permitted only under the data-owner non-CUI attestation (ADR-0003); source `.mpp` re-confirmed when provided. | Open (controls partially in place) |
| R-02 | **Parity miss** — computed metrics don't exactly match Acumen Fuse v8.11.0 / SSI. | Med | High | Golden-export parity suite as the acceptance gate; UniqueID-only matching; document any unavoidable delta with citations and drive to zero. | Open (needs golden files — Gate 1) |
| R-03 | **Missing golden inputs** — required `.pbix`/`.mpp`/Acumen/SSI/metrics-library files not deposited or incomplete. | Med | High | Gate-1 intake manifest with explicit checklist; verify presence/readability before Phase 1; gap list maintained in HANDOFF. Drive intake channel set up; most files inbound. **Open item:** the two source `.mpp` schedules not yet in the provided set. | Open (mitigating) |
| R-04 | **Native `.mpp` parsing fidelity** — MPXJ/COM read drops or mis-maps fields needed for parity. | Med | High | Vendored MPXJ retained (ADR-0001); plan COM-vs-MPXJ cross-check; validate against golden numbers. | Open |
| R-05 | **Session loss** — compaction/timeout drops un-committed work. | Med | Med | One milestone per session; commit-as-you-go; durable HANDOFF/SESSION-LOG/ADR; stop early with margin (§2.2). | Mitigated (process) |
| R-06 | **DCMA interpretation drift** — audit thresholds differ from the user's authoritative DCMA reference. | Med | Med | Ask the user for their preferred DCMA 14-point reference at Gate 1; make thresholds explicit/configurable; cite. | Open |
| R-07 | **Local model quality** — chosen Ollama model produces weak/unsupported narrative or hallucinated citations. | Med | Med | Require every AI statement to carry file+UniqueID+task-name citations; allow in-app model switch/pull; default to a capable workstation model. | Open |
| R-08 | **Scope creep per session** — a milestone too large to finish with margin. | Med | Med | Split milestones in BUILD-PLAN; do less per session; end-of-session ritual triggered proactively. | Mitigated (process) |

L = Likelihood, I = Impact.

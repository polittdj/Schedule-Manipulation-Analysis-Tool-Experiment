# Definition of Done — v2

> **Every item on this page is a REQUIREMENT.** There is no deferral column. The operator's
> instruction was explicit: *"make everything a requirement. I don't want to skip anything."*
> The only freedom taken is **order**, which is mine, and stated below.

## The ordering principle

This tool is read as evidence. So the order is not by size or by ease — it is by **how wrong the
tool currently is**:

1. it states something untrue → **Band 1**
2. only the operator can unblock it, and it gates other work → **Band 2**
3. its own documents disagree with each other → **Band 3**
4. a number is right but unguarded or unreproducible → **Band 4**
5. it breaks or degrades under real use → **Band 5**
6. it is true but incomplete → **Band 6**

**117 requirements.** The project's own curated queue listed 13.

## Evidence base

Three parallel sweeps (durable state · plan/risk/report docs + all source · 91 ADRs'
"Deliberately NOT done" sections), reconciled and spot-verified; plus this session's direct
measurements against the operator's paired SSI/Polaris export set. Two prior beliefs were
**reversed by measurement** and are recorded as such in `SRA-VS-SSI-LARGE-TEST-FILE2.md`.

The source code itself is clean: zero `TODO`/`FIXME`/`XXX`/`HACK`, zero `NotImplementedError`,
zero live `xfail`. The open work is truth, confirmation and capability — not code debt.

**Known blind spot:** no agent here can read GitHub PR or issue bodies, so anything promised only
in a PR comment is unaudited and absent below.

---

## BAND 1 — the tool currently states something that is not true (3; 001 closed, 3 ADDED)

Highest priority regardless of effort. In a testimony context a wrong number or a false claim is a liability; an incomplete feature is not.

> **Added 2026-08-13 by the full-repo audit — the approved-gateway class.** The operator now runs
> POLARIS against a NASA-approved AI gateway on their own machine, and the repo has no record of it.
> See **[`APPROVED-GATEWAY-INTEGRATION.md`](APPROVED-GATEWAY-INTEGRATION.md)** for the full,
> anchor-by-anchor writeup. Three new Band-1 items, in dependency order:
>
> | # | Who | Size | Requirement | Why |
> | --: | :-: | :-: | --- | --- |
> | ~~001a~~ | `agent` | `S` | ~~Pin `net_guard._LOOPBACK_HOSTNAMES` / `_LOCAL_HTTP_SCHEMES` contents, with a mutation proof~~ **CLOSED by ADR-0394** | **The entire Law-1 locality guarantee was one unpinned frozenset.** Premise re-measured, not inherited: with the gateway hostname added in a sandbox, the guard/AI/air-gap/startup/launcher/exhibit suites ran **336 passed, 0 failed**. Closed by `tests/guards/test_loopback_allowlist.py` — exact data pins **plus** behavioural closure sweeps, because 3 of 9 battery mutations bypass the allowlist without touching either frozenset. **9/9 caught by name**; canary + control + md5 self-checks. |
> | ~~001b~~ | `agent` | `M` | ~~Make the sovereignty banner OBSERVED, not config-derived~~ **CLOSED by [ADR-0396](../adr/0396-the-sovereignty-banner-is-observed.md), 2026-08-13** — one derivation (`banner_for_backend`, fail-closed on a missing/falsy `is_local`) consulted by the router, the page banner, the CUI drawer, the hero/takeaway, the settings tip, and BOTH exported exhibits; `is_local` is now an instance measurement; `ai/factory.py` lets every layer construct the same candidates; `chrome._observed_banner` adds a veto from the actually-routed cached backend. 18 guard tests, 15/15 mutations caught by name. | `route_backend`'s Banner was dead code; `chrome.py:175` rendered `banner_for(state.ai_config)`. With a gateway armed the page read "Local-only — no data leaves this machine." while data left. Two of the claims also printed inside **exported exhibits**. |
> | ~~001c~~ | `human` | `S` | ~~Decide the `cloud` option's fate: delete it, or build a first-class `GatewayBackend`~~ **DECIDED by the operator (2026-08-14: "I don't get the option to use the NASA approved AI models that are itar approved. Fix this") and CLOSED by [ADR-0402](../adr/0402-first-class-approved-gateway-backend.md)** — `ai/gateway.py` `GatewayBackend` (own allowlist `net_guard.APPROVED_GATEWAY_ENDPOINTS`, never a loopback widening; `is_local`/`is_approved_gateway` instance measurements; own `route_backend` branch requiring the recorded acknowledgment `AIConfig.gateway_approved`), the AI transaction log (`ai/txlog.py`, sent-before-transmit fail-closed), and the settings form's gateway option replacing the dead `cloud` one. 7/7-RED acceptance probe inverted; **15/15 mutations caught by name**; Tier-2 real-chromium render pass; v1.0.202 wheel + nine installers. | `ai/cloud.py` does not exist and no caller supplies `cloud_backend`, yet `settings.py:449` still offers "Cloud (UNCLASSIFIED only)". So the only route to an approved gateway is widening the loopback validator — the architecture channels a legitimate need into the most dangerous possible change. |

| # | Who | Size | Requirement | Why |
| --: | :-: | :-: | --- | --- |
| 001 | ~~`either`~~ | `L` | ~~ADR-0108: engine ignores the data date, understating real slips~~ — **CLOSED by [ADR-0391](../adr/0391-actual-start-is-a-scheduling-floor.md), 2026-08-12.** The row is kept because its DIAGNOSIS was disproved and that is part of the record: **the mechanism was never the data date.** A recorded `ActualStart` was ignored, so late-started work was re-packed at its logic start and dragged the successor chain back. `_actual_start_bounds` now floors it. Acumen Fuse agreement 4/5 → 5/5 on TP4 plus TP1; Large_Test_File per-task disagreements 826 → 164. Two residuals are named, not hidden: a completed task's actual **finish** is still unanchored, and two Hard_File goldens drift further from MSP (accepted, measured). | closed |
| 002 | `agent` | `S` | SRA R-1: state which basis (working vs calendar days) every SRA figure uses, on page and in export | MEASURED F-1: our numbers match SSI's own distribution to ~3%, but a reader cannot see that without re-deriving the histogram by hand. |
| 003 | `agent` | `S` | SRA R-2: carry risk-driver names into OAT sensitivity — never print a risk under its host task's name | MEASURED F-2: the 304.5-day top bar of the tornado is labelled with an activity name; UID 7443 prints twice under one name with different values. |

## BAND 2 — only the operator can do these, and they gate the bands below (35)

Licensed tools, physical machines, purchases, or the operator's own knowledge. No agent can start these, and several parity claims cannot close until they land.

| # | Who | Size | Requirement | Why |
| --: | :-: | :-: | --- | --- |
| 004 | `human` | `S` | A violated MFO arriving via the ADR-0309 resume floor under-reports the violation term | an under-reported constraint violation is the same failure class as ADR-0108 (understating the bad news). Needs an oracle file to settle. |
| 005 | `human` | `XS` | Acumen Fuse version v8.11.0 never confirmed out-of-band (PARTIALLY SETTLED) | the entire parity claim is stated 'against Acumen Fuse v8.11.0'. If the operator's tool is v8.11.0CU1, every doc saying v8.11.0 is imprecise. One operator sentence closes it permanently. |
| 006 | `human` | `UNKNOWN` | Acumen composite scores (SQ 88, DCMA 57/49) never reproduced — weighting unpublished | as a RATIFICATION — permanently-declined-by-Law-2, not undone. The DoD must state that satisfied-by-documentation counts as done, or the list can never close. Same for the two items below. |
| 007 | `human` | `S` | Bow Wave / CEI view never tuned against Acumen's bow-wave deck ('open item #5') | (as a recovery task) — an explicitly numbered open-item list is cited and is not in the repo. Either the list is lost (in which case items #1–#4 and #6+ are also lost) or the citation is vestigial. Worth ten minutes to determine w |
| 008 | `human` | `M` | COM / pywin32 MS Project cross-check importer was planned and never built | but formally WITHDRAW it from BUILD-PLAN.md rather than leave a planned module that does not exist. It was marked optional from the start; MPXJ covers the path. |
| 009 | `human` | `S` | CUI guard: tests/fixtures/ keeps an unconditional allowance and prose .txt is not sniffed for schedule tables | as an operator policy decision (XS to decide) — this is the only remaining hole in the Law 1 guard, it is documented, and it is the operator's call rather than an engineering task. A DoD for a CUI tool should state the guard's acc |
| 010 | `human` | `M` | DCMA-04/10/12/13 parity rows rest on transcription only — no Fuse export carries them | four of the fourteen DCMA checks have never been compared to the reference tool's own output. That is a parity claim the report papers over with a green tick. Either get the export or change the tick. |
| 011 | `human` | `S` | FX-03 / FX-04: re-convert and re-run Acumen Fuse (their current oracle numbers are void) | two parity oracles in the committed suite are currently KNOWN-STALE. A gate that measures against a void oracle is a gate that has stopped measuring. |
| 012 | `human` | `XS` | GitHub repo settings: branch protection, required-check contexts, auto-merge posture never confirmed | the CI gate is the enforcement mechanism for both project laws. If branch protection is not actually on, the gate is advisory. Five minutes in the GitHub UI. |
| 013 | `human` | `S` | Handbook D5: TFCI / Predicted CPTF deferred on an unresolved sign convention | correctly refusing to ship a metric whose sign is unknown. Exactly the Law-2 behavior wanted. Ratify as 'not in v1.0'. |
| 014 | `human` | `XS` | Installer Tier 2/3 GPU/VRAM pinning awaits the operator's card model | warn-only detection is a safe default; pinning is an optimization. |
| 015 | `human` | `XS` | Interpretive Q&A mode is ungated by design — no figure verification at all | as a documentation/ratification item — not to change the behavior, but to make sure no shipped doc states the unqualified claim. A blanket 'every figure is verified' sentence anywhere would be untrue. |
| 016 | `human` | `S` | Large_Test_File SSI absolute driving slack unreproducible — SSI's focus UID was never recorded | one number written down during a run the operator already knows how to do. Unblocks an entire absolute-parity claim. |
| 017 | `human` | `XS` | MS Project SRA re-run with Includes Risks/Opportunities = No | cheapest human artifact on the list and it converts a guessed residual into an attributed one. Law 2. |
| 018 | `human` | `S` | MSP's lag calendar on cross-calendar links awaits an oracle file | one of the five human-gated fidelity items; a cross-calendar lag mis-scheduled is a CPM error, not a cosmetic one. |
| 019 | `human` | `S` | Negative-Float O1 / CC-05: one Acumen Fuse run on a crafted sub-day-negative-float schedule | ADR-0385:150-154 says this is one of only two remaining ways to raise measured fidelity against the reference tools. The fixture is now built; only the licensed run is missing. |
| 020 | `human` | `S` | No Project5 Logic-Analysis export was ever provided — §D parity is Project2-only | §D's coverage is half what the parity report's structure implies. |
| 021 | `human` | `XS` | No agent in this environment can read GitHub PRs or issues — the 'promised in a PR body' class is unauditable here | a whole class of promises (PR-body checklists, review comments, unresolved threads) has never been swept because no session could reach it. The operator should do one pass over open/recent PRs before the DoD closes, or explicitly  |
| 022 | `human` | `XS` | OD-1: decide the fate of the unrequested lessons-learned material — and the freeze is being violated daily | a pending operator decision that an automated ritual is actively overriding every session. Either lift the freeze or stop the ritual; the current state is a rule the tool breaks by design. |
| 023 | `human` | `XS` | OR-03 residuals: the operator's ear is the acceptance for the boot hum, and /example cuts it at unload | cosmetic audio polish with a recorded escape hatch. The operator hears it or does not. |
| 024 | `human` | `S` | OR-04 §8 park artifacts — operator probes on the deployed Windows box (#1/#3/#4/#5) | F-13 in particular ('if keep_alive:0 does not override OLLAMA_KEEP_ALIVE=-1, the tool's entire unload strategy is inoperative') means the shipped GPU-release fix is UNPROVEN on the operator's own machine. One evening of probes. |
| 025 | `human` | `M` | PBIX deck measures were reconstructed, not extracted — DAX bodies are unreadable, ambiguous measures deferred | as a disclosure check — eleven metrics in the shipped dictionary are the tool's best guess at someone else's formula. That is honestly tagged in the dictionary and should be equally visible wherever those metrics are reported. DEF |
| 026 | `human` | `UNKNOWN` | Parity oracle limitation: 13 case.json references vs 2 real reference artifacts | as a RATIFICATION — the gate's own coverage limit should be a stated line in the parity report, not a session-log footnote. It is the single sentence most likely to be asked about under cross-examination. |
| 027 | `human` | `M` | Per-file Acumen/SSI reruns to upgrade §A/§B/§C from engine==golden to engine==Fuse | same class as the DCMA rows above: 'matches the golden we transcribed' is a weaker claim than 'matches Fuse', and FINAL-REPORT currently makes the stronger one. |
| 028 | `human` | `XS` | R-06: the authoritative DCMA 14-point reference was never confirmed with the operator | one sentence from the operator, and it determines which of several published DCMA variants the whole standards page claims to implement. |
| 029 | `human` | `S` | R-07: local-model narrative quality never validated on real hardware | the AI narrative is a shipped, operator-facing surface and no one has ever judged its output quality on the deployed box. The gates prove figures are cited; nothing proves the prose is usable. |
| 030 | `human` | `S` | SRA cost / JCL panel pending a cost-loaded schedule; cost EVM reports NOT_APPLICABLE | an entire shipped panel and the cost half of EVM have never run on real data. One cost-loaded schedule from the operator proves or disproves a large surface at once. |
| 031 | `human` | `S` | TP2 4×10 crew calendar loses its holiday exceptions on MS Project .mpp save (R-04) | as a RATIFICATION — not our defect (MS Project's write drops them), but a 6-week finish difference between the two representations of the same test project is exactly the artifact that needs a written, operator-signed explanation  |
| 032 | `human` | `XS` | The Mission Ops design prototype is operator-held and not committed | the authoritative source of truth for the entire UI is a file no agent can read. Either commit it (it is not CUI) or demote it so DESIGN-SYSTEM.md becomes authoritative. |
| 033 | `human` | `UNKNOWN` | The operator-approved completion plan file is unreachable from the repo | (check once) — an OPERATOR-APPROVED plan with four operator decisions in it, cited by the session log and stored outside the repo. If the operator still has that file, it may contain DoD-relevant decisions nothing else records. If |
| 034 | `human` | `XS` | The uploaded SSI artifact family is not committed as a second parity oracle | the parity suite's own documented weakness is thin oracle coverage (13 references vs 2 real artifacts). A second real oracle family is sitting there awaiting one operator decision. |
| 035 | `human` | `S` | XER maps P6 target_* (Planned Dates) to baseline_* without a reference check | a mis-mapped baseline silently changes every baseline-vs-actual metric on every P6 file. Needs one real P6 export to settle. |
| 036 | `human` | `S` | _UseMarking and _BACKEND_PROBE_TTL cannot be lit by an offline oracle | correctly reasoned; both are unit-covered and named as a gap. Would fold into the operator's on-machine probe session if one happens. |
| 037 | `human` | `S` | macOS .command installers have never been executed on real macOS | if macOS is a supported target; otherwise DEFER and delete the three .command installers from the shipped set. Shipping an installer nobody has ever run is a support incident waiting to happen. |
| 038 | `human` | `UNKNOWN` | §E slip/erosion counts SN04/06/07/09 not reproducible from static MSPDI — accepted as gate-locked deltas | as a RATIFICATION — same class as the composite scores. |

## BAND 3 — documents that contradict themselves or the repo (10)

Cheap, and they are the artifacts a reader relies on. A final report that disagrees with itself undermines every number in it.

| # | Who | Size | Requirement | Why |
| --: | :-: | :-: | --- | --- |
| 039 | `human` | `XS` | LICENSE is still a placeholder — no rights granted | you cannot call a deliverable finished when its distribution terms are 'to be finalized'. Pure operator/legal decision, minutes of work once made. |
| 040 | `human` | `S` | No .pbix has ever been deposited in the repo — and README + FINAL-REPORT say one was | three top-level docs make three different factual claims about whether a required input exists. Whatever the truth is, exactly one version must survive. |
| 041 | `agent` | `S` | Doc drift — FINAL-REPORT.md makes four claims its own sources contradict | highest priority on the whole list after ADR-0108. FINAL-REPORT.md is the document an outside reader is handed, and its headline parity claim is stronger than the tool's own parity report supports. In a testimony context an overst |
| 042 | `agent` | `XS` | Doc drift — LESSONS-LEARNED Part VIII has a mis-ordered 2026-08-10(e) entry | internal log ordering. Bundle into whatever doc-drift commit happens; not worth its own unit. |
| 043 | `agent` | `XS` | Doc drift — OPERATOR-REQUESTS.md violates its own rule (OR-03 marked OPEN after shipping) | the operator-request queue is the operator's own view of what they asked for. If it is unreliable in both directions it cannot support a DoD. |
| 044 | `agent` | `XS` | Doc drift — PARITY-REPORT.md still says the reference .mpp files are git-ignored and not committed | this misstates the CUI posture in the parity document. It is the one class of doc error that a reader would reasonably treat as evidence about how the project handles controlled data. |
| 045 | `agent` | `XS` | Doc drift — README.md and USER-GUIDE.md carry stale status and version claims | for README (front door, contradicts risks.md); IN for USER-GUIDE — a user guide 138 versions behind, self-labeled 'refresh pending', is the document the operator's colleagues will actually read. |
| 046 | `agent` | `XS` | Doc drift — REPO-INVENTORY.md says MS Project filters are 'Not yet wired into the UI' | one line, but REPO-INVENTORY is 817 lines of onboarding truth and this entry would send the next agent to build something that exists. |
| 047 | `agent` | `XS` | Doc drift — five RTM rows never refreshed (A1, C1, C3 ▣; Q5, Q6 ◻) plus the Phase-1 heading | none of the five is unfinished engineering; all five are un-refreshed rows. This is the cheapest cluster on the list and it is precisely what makes the project look unfinished on paper when it is not. |
| 048 | `agent` | `XS` | Doc drift — risks.md R-01 and R-04 status lines contradict their own bodies | a risk register whose top CUI risk reads 'Open' with no explanation of what would close it is either alarming or meaningless. Decide which and say so. |

## BAND 4 — engine, parity and importer correctness (26)

Numbers that are right today but unguarded, unreproducible, or resting on an accepted residual rather than a measurement.

| # | Who | Size | Requirement | Why |
| --: | :-: | :-: | --- | --- |
| 049 | `either` | `M` | Acumen definitional reconciliations never closed: TP3 Leads, Insufficient Detail, HSD07/10 aggregation, DCMA thresholds, .xlsx formula spot-check, per-task detail tabs, Metric-History Failed(T/F) flag | for the two definitional rows (Leads / Insufficient Detail) — those are two metrics where the tool and Acumen count DIFFERENT THINGS under the same name, which is a live misreading risk on an exhibit. DEFER the rest as reference-h |
| 050 | `either` | `M` | Calendar model: single working block only — no multi-shift, no lunch breaks, no per-task calendars in the base model | (decide, not necessarily build) — this is the root cause of the last SSI sub-day residual AND of the P80/P90 residual below. The DoD should either fund it or formally ratify the residual with a stated magnitude, because it is a li |
| 051 | `either` | `M` | HSD10 basis delta (engine −148 vs Fuse −134) and SN04 membership swap (UID 99 vs 96) — accepted, not eliminated | as a RATIFICATION — these are two places where the tool and Acumen disagree on the same input and both are 'right' under their own basis. A testimony DoD should name them in the shipped parity report's headline, not only in its re |
| 052 | `either` | `S` | Integrity baseline movement deltas are calendar days, not working days | labeled honestly and genuinely blocked by what the file carries. Verify the label survives on every surface that shows the figure. |
| 053 | `either` | `M` | JCL fixture contract gap-analysis (operator-supplied) — verify every claim, then act | UNVERIFIED by this session. Claims our SRA field contract is exactly 'SRA Risk Ranking Factors' / 'Best Case Duration' / 'Worst Case Duration', that compute_jcl has a cost-loaded gate, and that ProbabilisticBranch + ConditionalBra |
| 054 | `either` | `M` | P80/P90 residual ~20 calendar days — importer skips recurring calendar-exception patterns | a ~20-day error on a P80/P90 forecast is a reported number that is wrong. It is logged at import but the log does not reach the page (see import_notes below). |
| 055 | `either` | `L` | SRA anchor realignment leaves the simulated network 370 working days shorter than the displayed schedule | the SRA page shows the operator a confidence distribution computed on a network that is not the network the rest of the tool displays. That is a shipped inconsistency between two of the tool's own outputs, and it is exactly the ki |
| 056 | `either` | `XS` | SSI Driving Slack / Path NN definitions never confirmed against the Deltek Metric Developers Guide | 108/108 exact agreement with SSI on the relative tiers is stronger empirical evidence than a definition read, and it already exists. |
| 057 | `either` | `M` | XER importer gaps: no suspend/resume read, working_days exceptions dropped, 24h day lost, per-task calendars deferred | if Primavera files are in v1.0's supported scope; DEFER (and downgrade XER to 'structural read only' in the docs) if they are not. The current posture — a documented importer with silent fidelity holes — is the option that can pro |
| 058 | `either` | `S` | cei_critical stays NA on the battery corpus — needs a stored-slack Acumen-parity fixture | merges naturally into the stored-SRA-fields fixture work below. |
| 059 | `agent` | `XS` | /api/sra/jcl renders 422 in every oracle state | oracle coverage only; the endpoint works when called correctly. |
| 060 | `agent` | `XS` | /sra renders no takeaway at all when nothing solves | an empty page is indistinguishable from a broken page. One sentence of empty-state copy. |
| 061 | `agent` | `S` | Handbook follow-ons: stoplight rendering on other panels, cross-version float-erosion trend, and §7.3.3 citations in help.py | for the help.py citations (a metric attributed to the wrong authority is a testimony problem — XS to fix); DEFER the two rendering follow-ons as polish. |
| 062 | `agent` | `XS` | In-tool metric dictionary lacks the two documented Acumen scope differences | the analyst reads help.py IN THE TOOL; PARITY-REPORT.md is a repo file they may never open. Two metrics where the tool counts a different population than Acumen, and the in-tool help does not say so. |
| 063 | `agent` | `XS` | MSPDI reader has no decode ladder — forces utf-8-sig with errors='replace' | an activity name silently corrupted to U+FFFD is an exhibit defect, and `Task.name` is what the analyst reads off every page. Small fix. |
| 064 | `agent` | `M` | PARK-LIST P3 — full SSI vendor→StructuredSolutions rename | pure naming hygiene; zero effect on any reported number. |
| 065 | `agent` | `M` | SRA R-3: reproduce the SRA crash before optimising anything | Operator hit two crashes then a very slow success. UNVERIFIED whether timeout or fault — 'slow' and 'killed' need different fixes. |
| 066 | `agent` | `M` | SRA R-4: restrict the simulated network to the focus event's ancestor set | MEASURED F-3: 1,342 of 2,125 tasks (63%) are re-solved every iteration and cannot affect the focus finish. ~2.7x available. |
| 067 | `agent` | `S` | SRA R-5: regression-pin the percentile agreement against the operator's SSI export set | MEASURED F-1: P80 is exact, P50 +3 d, P90 +4 d — currently unguarded, so the next engine change could break it silently. |
| 068 | `agent` | `M` | SRA R-6: make long SRA runs non-blocking (progress + cancel) | MEASURED F-3: ~2.9 min at 2000 iterations is beyond any reasonable synchronous request even after R-4. |
| 069 | `agent` | `S` | Slice-7 crafted v4/v2 SSI setup-load sequences were never rebuilt into the render oracle | (adjudicate) — a promise carried verbatim through seven ADRs past the event that was supposed to discharge it. Ten minutes to decide; otherwise it rides forever. |
| 070 | `agent` | `S` | Stored-SRA-fields MSPDI fixture — three engine members are oracle-dark | three code paths that read stored SRA risk fields from a file have NEVER been exercised by a file. If a real schedule carries those fields, this is untested code on a testimony surface. |
| 071 | `agent` | `XS` | TaskTiming.late_start/late_finish are lossy axis projections for off-calendar tasks | no reader outside cpm.py, so nothing displays them. But add a guard that FAILS if a new reader appears, or this becomes a wrong number silently. |
| 072 | `agent` | `S` | The render oracle lost hand-authored variants that were never recovered | honest handling of an unrecoverable loss. The instrument is now committed, so it cannot decay further. |
| 073 | `agent` | `XS` | UNCOMMITTED work in the tree: the sub-day negative-float Fuse probe fixture + its guard | this is the artifact that unblocks the single highest-value operator run (Negative-Float O1). It exists but is invisible to the operator and to CI. Commit it, or the next session regenerates it from scratch. |
| 074 | `agent` | `S` | import_notes never reach the page — importer warnings are invisible to the analyst | cheap, and it is the delivery mechanism for every 'we know this file lost fidelity' warning the importers already produce. Without it those warnings exist only in a log nobody reads. |

## BAND 5 — robustness, packaging and operational limits (24)

Nothing untrue; things that fail or degrade under real use.

| # | Who | Size | Requirement | Why |
| --: | :-: | :-: | --- | --- |
| 075 | `either` | `M` | 99 reference-intake files carry extensions their bytes contradict — deliberately left as-is | measured, guarded, and proven not to reach the product. Ratify as 'will not fix'; renaming would break the pinning tests that make it safe. |
| 076 | `either` | `L` | DECM V7.0 EVMS cost-compliance extended audit never implemented | explicitly marked 'optional/extended' in the plan that scoped it. But the DoD should say so out loud, because a reader of METRICS-CATALOG.md would assume it is coming. |
| 077 | `either` | `M` | Period-over-period metric families still run on the target-truncated focused scope | as a disclosure item — a trend line that silently changes population when a target is set can show a movement that is an artifact of the filter. It must say so on the page, not only in an ADR. |
| 078 | `either` | `UNKNOWN` | Phase 6 — the docs/operator queue was never opened | (define) — this is the placeholder that most of the doc-drift items above should have lived in. Either populate it from this inventory or delete the reference. |
| 079 | `either` | `M` | reduce-FILTER can fabricate pair-diffs (documented caveat, deliberately not changed) | same class as above, and worse: 'fabricate' is the ADR's own word for what a shipped filter can do to a comparison. This one belongs in the on-page disclosure set for v1.0. |
| 080 | `agent` | `S` | /analysis focus→tip family is load-sensitive and intermittently fails (adjudicated, unfixed) | proven pre-existing and environment-sensitive, and already carries a 'do not re-chase' note. Ratify as known-flaky. |
| 081 | `agent` | `S` | /groups breakdown 'Activities' column still counts summary rows | a displayed count that includes rollup rows is a wrong number on a page, and 'Activities' is not an ambiguous label. Small fix, clear contract. |
| 082 | `agent` | `L` | AI figure gate: no full semantic role model (token matching cannot verify meaning) | but the DoD should state the residual explicitly: the gate guards digits and accusatory terms, not meaning, and interpretive mode is ungated by design. That sentence belongs in the shipped disclosure, not only in a docstring. |
| 083 | `agent` | `UNKNOWN` | AI-DERIVED-METRICS Phase 3 (surface verified derivations in narrative/briefing) — status unknown | explicitly marked optional. Confirm status in one grep before the DoD is written so it is not silently carried. |
| 084 | `agent` | `M` | Change counterfactual detects but never measures progress-field changes | the capability; the disclosure shipped. But confirm the on-page '(N excluded)' wording actually names WHY they were excluded — 'excluded' without a reason invites the wrong inference. |
| 085 | `agent` | `S` | DATE filter literals share the C4 None shape (null-ordering) | pre-existing and scoped out deliberately; affects filter edge cases, not reported metrics. |
| 086 | `agent` | `XS` | Declined-with-rationale items that should be RATIFIED as 'will not do', not scheduled | / RATIFY — every one has a written rationale, several are Law-2-correct refusals. The DoD should list them once as 'decided, will not do' so they stop reappearing in every sweep. |
| 087 | `agent` | `S` | Driving-corridor fixture — four functions with no test coverage | the driving path IS the forensic product. Four uncovered functions on that page family is the coverage gap that matters most. |
| 088 | `agent` | `S` | Five pre-existing playwright-only test failures, invisible to CI | four of the five are DOWNLOAD failures on pages whose downloads become exhibits. 'CI-invisible' means the gate cannot catch a regression here at all. |
| 089 | `agent` | `XS` | GitHub Actions pinned but not upgraded (checkout v7 / setup-python v7 available) | pinned-and-working beats newest. Pure maintenance. |
| 090 | `agent` | `M` | Installers do not install with -c constraints/known-good.txt | the repo has a tested known-good lock and the thing that actually builds the operator's machine ignores it. That means the deployed environment is not the environment CI validated. |
| 091 | `agent` | `XS` | Nine stale unmerged remote branches, several many commits ahead of main | (triage, XS) — almost certainly all superseded, but nobody has checked. Two of them (smat-tool-continuation, smat-adr-0250-decision) are from late July and carry named ADR work. Confirm each is fully represented in main, then dele |
| 092 | `agent` | `S` | SNET-reschedule fixture for /integrity's artifact-cluster branch | the artifact-cluster branch exists to tell the analyst 'this is a tool artifact, not manipulation'. If it renders on no fixture, the most consequential false-positive suppressor in the tool is unverified. |
| 093 | `agent` | `XS` | Three conditional test skips that can silently void their own assertions | XS, and this repo's own most-repeated defect class is 'a green test that could never fail'. A skip whose condition is now permanently true is exactly that. |
| 094 | `agent` | `XS` | ai/qa.py's workbook fact sheet bypasses the per-epoch briefing memo | a performance duplication, not a correctness one. |
| 095 | `agent` | `S` | pytest-cov / bandit / pip-audit dependency floors were never bisected | self-described as advisory and bounded; these are dev-tool floors, not runtime. |
| 096 | `agent` | `S` | starlette / httpx TestClient transition: a bounded but unresolved upstream break | correctly pinned and documented, and the break is upstream's to land. Revisit when it does. |
| 097 | `agent` | `S` | web/backends.py — promote the AI-backend kernel out of settings.py | refactor polish with zero behavioral effect. |
| 098 | `agent` | `M` | ~150 MB RSS retained per loaded file — no per-file unload | if the operator ever loads the documented maximum of 100 files at once (USER-GUIDE.md documents that limit) — 100 × 150 MB is not survivable. Otherwise DEFER. Worth one measurement to decide. |

## BAND 6 — UI, exports and presentation completeness (19)

The tool tells the truth; it does not yet always tell it well.

| # | Who | Size | Requirement | Why |
| --: | :-: | :-: | --- | --- |
| 099 | `either` | `S` | Elapsed-task slack displays on the project 480-minute axis (CC-01 rendering-half debt) | 7.88 displayed where MS Project shows 2.63 for the same task is a number an opposing expert will put on a slide. The minutes are exact; only the axis label/divisor is wrong. Cheap to fix, expensive to leave. |
| 100 | `either` | `S` | HMI Delta: the reference export's cells do not reproduce from the pinned .aft formula | as a RATIFICATION — the tool and the reference tool disagree and the tool has ruled the reference wrong. That is a defensible call but it must be a RECORDED, operator-endorsed call, not a parenthetical in help text. |
| 101 | `either` | `M` | Offline / air-gapped installer bundle (option B) never built | if the deployment target is genuinely air-gapped — the whole premise of Law 1 is a machine that does not reach the network, and the shipped installers pip-install from the network. This deserves an explicit operator answer: is the |
| 102 | `agent` | `S` | /driving-path overflows horizontally (scrollWidth 1719 vs clientWidth 1440) | (verify first) — the design system forbids body-level horizontal scroll and this is the driving-path page. Render it before scheduling any fix. |
| 103 | `agent` | `S` | /standards has no export of its own — its ⤓ serves the analysis workbook | as a UI-honesty check — a download button on page A that silently hands you page B's data will confuse an analyst under time pressure. Either relabel it or give the page its own export. |
| 104 | `agent` | `S` | A0293-UI — 'native .mpp unavailable on this machine' is never surfaced in the UI | if Java/MPXJ is missing on the operator's box, .mpp loads fail and the tool currently says nothing useful. That is a first-five-minutes support problem on the deployed machine. |
| 105 | `agent` | `M` | Cut the fenced /groups page family out of app.py | internal architecture only. The monolith split's stated goal (no page family left in app.py) is met but for one fenced family; that is a fine place to stop for v1.0. |
| 106 | `agent` | `UNKNOWN` | DESIGN-SYSTEM phase 4 ('new analytics panels') is still marked in progress | (define or close) — the design contract declares itself unfinished with no definition of what 'finished' means. Either enumerate the remaining panels or mark the phase complete. |
| 107 | `agent` | `L` | PARK-LIST P1 — the CP-basis engine and live ExhibitPayload builder do not exist | (scope decision) — a shipped console script whose primary input mode returns an error is either a v1.0 feature to finish or a v1.0 feature to REMOVE from the docs and the entry points. Shipping it half-wired is the worst of the th |
| 108 | `agent` | `M` | PARK-LIST P2 — volData six-state migration + EX-03/04/07 live exhibits | strictly blocked behind P1; nothing is untrue while it waits. |
| 109 | `agent` | `S` | PARK-LIST P4 — weighted_instability on the volatility heatmap | the shipped flips-based sort is labeled honestly as the available measure. No false claim. |
| 110 | `agent` | `S` | PBIX deck pages 3, 10 and 11 never reproduced | feature parity with a reference deck is a nice-to-have; nothing untrue is claimed. |
| 111 | `agent` | `S` | Three pages render a bare h1 with no page-lede (/briefing, /path, /compare) | /briefing and /path are the two pages an outside reader is most likely to be handed. The design system requires a lede; three of the most-read pages don't have one. |
| 112 | `agent` | `M` | UI rank 14 — prototype token aliases + universal ⊞ EXPLORE drill wiring | the last unbuilt item of a redesign whose 12 chapters are all shelled. Pure polish. |
| 113 | `agent` | `S` | Vendored typography never done — IBM Plex Mono / Barlow are name-only system stacks | the design system's own text says not done, and the tool renders in a different typeface than its specification on any machine lacking those fonts. No egress risk (name-only stacks fetch nothing), so this is fidelity-of-appearance |
| 114 | `agent` | `S` | _active_backend / _HB_CONSUME_SEC / _cell / export_path — declined or unmoved monolith residue | every one has a written rationale. Recommend the DoD RATIFY them as 'will not do' rather than schedule them. |
| 115 | `agent` | `XS` | data-sf-hint migration is undocumented in the design contract | documentation of an established pattern. Bundle with any DESIGN-SYSTEM edit. |
| 116 | `agent` | `S` | export_compare / export_risks / export_wbs each duplicate their page body's derivation | (verify, not necessarily refactor) — three exports compute the numbers a SECOND time by a SECOND code path. Nothing proves the export agrees with the page. For a tool whose exports become exhibits, a test asserting export == page  |
| ~~117~~ | `agent` | `XS` | ~~mpxj_ref() has no shallow-clone guard — the build silently trusts the operator to have unshallowed~~ **CLOSED by [ADR-0397](../adr/0397-a-graft-boundary-is-not-a-touch.md), 2026-08-13** — after firing a second time, on v1.0.201's own rebuild (it pinned the container's graft-boundary commit `a100184d`). `mpxj_ref()` now refuses a resolution that appears in `$GIT_DIR/shallow` and accepts `SF_MPXJ_REF` only after verifying the ref's `tools/mpxj` TREE is byte-identical to the working tree's (tree-identity, not ancestry — ancestry is unverifiable in exactly the clones that lie). `test_the_converter_pin_is_a_real_touch_not_a_shallow_graft_artifact` covers the built artifacts; observed red 3/3 families against the drifted build. | the trap fired twice; the second firing was caught only because the committed pin was cross-checked (QC-2). |

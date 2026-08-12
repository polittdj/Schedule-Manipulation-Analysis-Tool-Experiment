# Definition of Done — v2

> **Status: DRAFT — needs the operator's decisions. Nothing here is agreed yet.**

## Why this file exists

The project's original Definition of Done (`BUILD-PLAN.md` §8, milestones M1–M17) was **met on
2026-06-09**, four days into the build. Everything since — 64 days, 256 sessions, ~360 ADRs — has
been self-directed hardening against **no declared finish line**. Work has been discovered faster
than it has been closed, so "when will it be done?" currently has no answer that is not a guess.

This file is the second finish line. When every row marked **MUST** is done, the project is
**finished**, and anything discovered afterwards goes to a v1.1 backlog instead of this list.

## The one question that changes every answer below

> **Will this tool's output be relied on as evidence in a real dispute (claim, arbitration,
> litigation)?**  ☐ YES ☐ NO

Answer this first. If **YES**, every item whose failure mode is *"the tool states something that
is not true"* is a MUST, regardless of effort — an overstated parity claim or an understated slip
is a liability, not a rough edge. If **NO**, most of those can be LATER, and the list gets short.

## How to fill this in

For each row tick **one** box: **MUST** (not finished until this is done) or **LATER** (goes to
v1.1). My suggestion is in the last column — change any of them. You may put almost everything in
LATER; that is the point of the exercise, not a failure of it.

---

## TIER 0 — the one item that outranks everything else

This is not a normal row. If only one thing on this page gets done, make it this one.

| MUST | LATER | Who | Size | The job | Why (my suggestion) |
| :-: | :-: | :-: | :-: | --- | --- |
| ☐ | ☐ | `either` | `L` | ADR-0108: engine ignores the data date, understating real slips | this is the one open item that makes the tool report a number that is WRONG in the direction that matters (it understates a slip). In a testimony context an understated delay is the worst possible fai |

**Independently reproduced 2026-08-12**, not taken on trust:

| TP4 version | MS Project's own stored finish | Our engine computes | |
| --- | --- | --- | --- |
| v4 | 2026-06-26 | 2026-06-26 | agrees |
| **v5** | **2026-07-17** | **2026-06-26** | **21 days early** |

`src/schedule_forensics/engine/cpm.py` contains **zero** references to `status_date`, so
in-progress remaining work is never floored at the data date and a real slip collapses onto the
prior version's finish. The **real slip v4→v5 is 21 days; the engine reports 0.**

It is a known gap (ADR-0108, audit F-02 HIGH/CONFIRMED), **two fix attempts were reverted** for
breaking Project2/5 parity and EVM1, and it is **guarded by no test** — so it can silently get
worse. For a forensic delay tool, understating a delay is the worst possible direction to be wrong
in: it favours whoever is accused of causing the delay.

**Minimum acceptable outcome if it is not fixed:** a guard test pinning the known discrepancy so it
cannot worsen unnoticed, **and** a prominent on-page disclosure wherever a finish date or slip is
reported. Not an ADR footnote.

---

## TIER 1 — things only YOU can do (32 items)

Licensed tools, physical machines, purchasing, or your own knowledge. No agent can do these.

| MUST | LATER | Who | Size | The job | Why (my suggestion) |
| :-: | :-: | :-: | :-: | --- | --- |
| ☐ | ☐ | `human` | `M` | DCMA-04/10/12/13 parity rows rest on transcription only — no Fuse export carries them | four of the fourteen DCMA checks have never been compared to the reference tool's own output. That is a parity claim the report papers over with a green tick. Either get the export or change the tick. |
| ☐ | ☐ | `human` | `M` | PBIX deck measures were reconstructed, not extracted — DAX bodies are unreadable, ambiguous measures deferred | as a disclosure check — eleven metrics in the shipped dictionary are the tool's best guess at someone else's formula. That is honestly tagged in the dictionary and should be equally visible wherever t |
| ☐ | ☐ | `human` | `M` | Per-file Acumen/SSI reruns to upgrade §A/§B/§C from engine==golden to engine==Fuse | same class as the DCMA rows above: 'matches the golden we transcribed' is a weaker claim than 'matches Fuse', and FINAL-REPORT currently makes the stronger one. |
| ☐ | ☐ | `human` | `S` | A violated MFO arriving via the ADR-0309 resume floor under-reports the violation term | an under-reported constraint violation is the same failure class as ADR-0108 (understating the bad news). Needs an oracle file to settle. |
| ☐ | ☐ | `human` | `S` | Bow Wave / CEI view never tuned against Acumen's bow-wave deck ('open item #5') | (as a recovery task) — an explicitly numbered open-item list is cited and is not in the repo. Either the list is lost (in which case items #1–#4 and #6+ are also lost) or the citation is vestigial. Wo |
| ☐ | ☐ | `human` | `S` | CUI guard: tests/fixtures/ keeps an unconditional allowance and prose .txt is not sniffed for schedule tables | as an operator policy decision (XS to decide) — this is the only remaining hole in the Law 1 guard, it is documented, and it is the operator's call rather than an engineering task. A DoD for a CUI too |
| ☐ | ☐ | `human` | `S` | FX-03 / FX-04: re-convert and re-run Acumen Fuse (their current oracle numbers are void) | two parity oracles in the committed suite are currently KNOWN-STALE. A gate that measures against a void oracle is a gate that has stopped measuring. |
| ☐ | ☐ | `human` | `S` | Large_Test_File SSI absolute driving slack unreproducible — SSI's focus UID was never recorded | one number written down during a run the operator already knows how to do. Unblocks an entire absolute-parity claim. |
| ☐ | ☐ | `human` | `S` | MSP's lag calendar on cross-calendar links awaits an oracle file | one of the five human-gated fidelity items; a cross-calendar lag mis-scheduled is a CPM error, not a cosmetic one. |
| ☐ | ☐ | `human` | `S` | Negative-Float O1 / CC-05: one Acumen Fuse run on a crafted sub-day-negative-float schedule | ADR-0385:150-154 says this is one of only two remaining ways to raise measured fidelity against the reference tools. The fixture is now built; only the licensed run is missing. |
| ☐ | ☐ | `human` | `S` | No .pbix has ever been deposited in the repo — and README + FINAL-REPORT say one was | three top-level docs make three different factual claims about whether a required input exists. Whatever the truth is, exactly one version must survive. |
| ☐ | ☐ | `human` | `S` | No Project5 Logic-Analysis export was ever provided — §D parity is Project2-only | §D's coverage is half what the parity report's structure implies. |
| ☐ | ☐ | `human` | `S` | OR-04 §8 park artifacts — operator probes on the deployed Windows box (#1/#3/#4/#5) | F-13 in particular ('if keep_alive:0 does not override OLLAMA_KEEP_ALIVE=-1, the tool's entire unload strategy is inoperative') means the shipped GPU-release fix is UNPROVEN on the operator's own mach |
| ☐ | ☐ | `human` | `S` | R-07: local-model narrative quality never validated on real hardware | the AI narrative is a shipped, operator-facing surface and no one has ever judged its output quality on the deployed box. The gates prove figures are cited; nothing proves the prose is usable. |
| ☐ | ☐ | `human` | `S` | SRA cost / JCL panel pending a cost-loaded schedule; cost EVM reports NOT_APPLICABLE | an entire shipped panel and the cost half of EVM have never run on real data. One cost-loaded schedule from the operator proves or disproves a large surface at once. |
| ☐ | ☐ | `human` | `S` | TP2 4×10 crew calendar loses its holiday exceptions on MS Project .mpp save (R-04) | as a RATIFICATION — not our defect (MS Project's write drops them), but a 6-week finish difference between the two representations of the same test project is exactly the artifact that needs a written |
| ☐ | ☐ | `human` | `S` | XER maps P6 target_* (Planned Dates) to baseline_* without a reference check | a mis-mapped baseline silently changes every baseline-vs-actual metric on every P6 file. Needs one real P6 export to settle. |
| ☐ | ☐ | `human` | `S` | macOS .command installers have never been executed on real macOS | if macOS is a supported target; otherwise DEFER and delete the three .command installers from the shipped set. Shipping an installer nobody has ever run is a support incident waiting to happen. |
| ☐ | ☐ | `human` | `UNKNOWN` | Acumen composite scores (SQ 88, DCMA 57/49) never reproduced — weighting unpublished | as a RATIFICATION — permanently-declined-by-Law-2, not undone. The DoD must state that satisfied-by-documentation counts as done, or the list can never close. Same for the two items below. |
| ☐ | ☐ | `human` | `UNKNOWN` | Parity oracle limitation: 13 case.json references vs 2 real reference artifacts | as a RATIFICATION — the gate's own coverage limit should be a stated line in the parity report, not a session-log footnote. It is the single sentence most likely to be asked about under cross-examinat |
| ☐ | ☐ | `human` | `UNKNOWN` | The operator-approved completion plan file is unreachable from the repo | (check once) — an OPERATOR-APPROVED plan with four operator decisions in it, cited by the session log and stored outside the repo. If the operator still has that file, it may contain DoD-relevant deci |
| ☐ | ☐ | `human` | `UNKNOWN` | §E slip/erosion counts SN04/06/07/09 not reproducible from static MSPDI — accepted as gate-locked deltas | as a RATIFICATION — same class as the composite scores. |
| ☐ | ☐ | `human` | `XS` | Acumen Fuse version v8.11.0 never confirmed out-of-band (PARTIALLY SETTLED) | the entire parity claim is stated 'against Acumen Fuse v8.11.0'. If the operator's tool is v8.11.0CU1, every doc saying v8.11.0 is imprecise. One operator sentence closes it permanently. |
| ☐ | ☐ | `human` | `XS` | GitHub repo settings: branch protection, required-check contexts, auto-merge posture never confirmed | the CI gate is the enforcement mechanism for both project laws. If branch protection is not actually on, the gate is advisory. Five minutes in the GitHub UI. |
| ☐ | ☐ | `human` | `XS` | Interpretive Q&A mode is ungated by design — no figure verification at all | as a documentation/ratification item — not to change the behavior, but to make sure no shipped doc states the unqualified claim. A blanket 'every figure is verified' sentence anywhere would be untrue. |
| ☐ | ☐ | `human` | `XS` | LICENSE is still a placeholder — no rights granted | you cannot call a deliverable finished when its distribution terms are 'to be finalized'. Pure operator/legal decision, minutes of work once made. |
| ☐ | ☐ | `human` | `XS` | MS Project SRA re-run with Includes Risks/Opportunities = No | cheapest human artifact on the list and it converts a guessed residual into an attributed one. Law 2. |
| ☐ | ☐ | `human` | `XS` | No agent in this environment can read GitHub PRs or issues — the 'promised in a PR body' class is unauditable here | a whole class of promises (PR-body checklists, review comments, unresolved threads) has never been swept because no session could reach it. The operator should do one pass over open/recent PRs before  |
| ☐ | ☐ | `human` | `XS` | OD-1: decide the fate of the unrequested lessons-learned material — and the freeze is being violated daily | a pending operator decision that an automated ritual is actively overriding every session. Either lift the freeze or stop the ritual; the current state is a rule the tool breaks by design. |
| ☐ | ☐ | `human` | `XS` | R-06: the authoritative DCMA 14-point reference was never confirmed with the operator | one sentence from the operator, and it determines which of several published DCMA variants the whole standards page claims to implement. |
| ☐ | ☐ | `human` | `XS` | The Mission Ops design prototype is operator-held and not committed | the authoritative source of truth for the entire UI is a file no agent can read. Either commit it (it is not CUI) or demote it so DESIGN-SYSTEM.md becomes authoritative. |
| ☐ | ☐ | `human` | `XS` | The uploaded SSI artifact family is not committed as a second parity oracle | the parity suite's own documented weakness is thin oracle coverage (13 references vs 2 real artifacts). A second real oracle family is sitting there awaiting one operator decision. |

---

## TIER 2 — things I can do (44 items)

| MUST | LATER | Who | Size | The job | Why (my suggestion) |
| :-: | :-: | :-: | :-: | --- | --- |
| ☐ | ☐ | `agent` | `L` | PARK-LIST P1 — the CP-basis engine and live ExhibitPayload builder do not exist | (scope decision) — a shipped console script whose primary input mode returns an error is either a v1.0 feature to finish or a v1.0 feature to REMOVE from the docs and the entry points. Shipping it hal |
| ☐ | ☐ | `agent` | `M` | Installers do not install with -c constraints/known-good.txt | the repo has a tested known-good lock and the thing that actually builds the operator's machine ignores it. That means the deployed environment is not the environment CI validated. |
| ☐ | ☐ | `agent` | `M` | ~150 MB RSS retained per loaded file — no per-file unload | if the operator ever loads the documented maximum of 100 files at once (USER-GUIDE.md documents that limit) — 100 × 150 MB is not survivable. Otherwise DEFER. Worth one measurement to decide. |
| ☐ | ☐ | `agent` | `S` | /driving-path overflows horizontally (scrollWidth 1719 vs clientWidth 1440) | (verify first) — the design system forbids body-level horizontal scroll and this is the driving-path page. Render it before scheduling any fix. |
| ☐ | ☐ | `agent` | `S` | /groups breakdown 'Activities' column still counts summary rows | a displayed count that includes rollup rows is a wrong number on a page, and 'Activities' is not an ambiguous label. Small fix, clear contract. |
| ☐ | ☐ | `agent` | `S` | /standards has no export of its own — its ⤓ serves the analysis workbook | as a UI-honesty check — a download button on page A that silently hands you page B's data will confuse an analyst under time pressure. Either relabel it or give the page its own export. |
| ☐ | ☐ | `agent` | `S` | A0293-UI — 'native .mpp unavailable on this machine' is never surfaced in the UI | if Java/MPXJ is missing on the operator's box, .mpp loads fail and the tool currently says nothing useful. That is a first-five-minutes support problem on the deployed machine. |
| ☐ | ☐ | `agent` | `S` | Doc drift — FINAL-REPORT.md makes four claims its own sources contradict | highest priority on the whole list after ADR-0108. FINAL-REPORT.md is the document an outside reader is handed, and its headline parity claim is stronger than the tool's own parity report supports. In |
| ☐ | ☐ | `agent` | `S` | Driving-corridor fixture — four functions with no test coverage | the driving path IS the forensic product. Four uncovered functions on that page family is the coverage gap that matters most. |
| ☐ | ☐ | `agent` | `S` | Five pre-existing playwright-only test failures, invisible to CI | four of the five are DOWNLOAD failures on pages whose downloads become exhibits. 'CI-invisible' means the gate cannot catch a regression here at all. |
| ☐ | ☐ | `agent` | `S` | Handbook follow-ons: stoplight rendering on other panels, cross-version float-erosion trend, and §7.3.3 citations in help.py | for the help.py citations (a metric attributed to the wrong authority is a testimony problem — XS to fix); DEFER the two rendering follow-ons as polish. |
| ☐ | ☐ | `agent` | `S` | SNET-reschedule fixture for /integrity's artifact-cluster branch | the artifact-cluster branch exists to tell the analyst 'this is a tool artifact, not manipulation'. If it renders on no fixture, the most consequential false-positive suppressor in the tool is unverif |
| ☐ | ☐ | `agent` | `S` | Slice-7 crafted v4/v2 SSI setup-load sequences were never rebuilt into the render oracle | (adjudicate) — a promise carried verbatim through seven ADRs past the event that was supposed to discharge it. Ten minutes to decide; otherwise it rides forever. |
| ☐ | ☐ | `agent` | `S` | Stored-SRA-fields MSPDI fixture — three engine members are oracle-dark | three code paths that read stored SRA risk fields from a file have NEVER been exercised by a file. If a real schedule carries those fields, this is untested code on a testimony surface. |
| ☐ | ☐ | `agent` | `S` | Three pages render a bare h1 with no page-lede (/briefing, /path, /compare) | /briefing and /path are the two pages an outside reader is most likely to be handed. The design system requires a lede; three of the most-read pages don't have one. |
| ☐ | ☐ | `agent` | `S` | Vendored typography never done — IBM Plex Mono / Barlow are name-only system stacks | the design system's own text says not done, and the tool renders in a different typeface than its specification on any machine lacking those fonts. No egress risk (name-only stacks fetch nothing), so  |
| ☐ | ☐ | `agent` | `S` | export_compare / export_risks / export_wbs each duplicate their page body's derivation | (verify, not necessarily refactor) — three exports compute the numbers a SECOND time by a SECOND code path. Nothing proves the export agrees with the page. For a tool whose exports become exhibits, a  |
| ☐ | ☐ | `agent` | `S` | import_notes never reach the page — importer warnings are invisible to the analyst | cheap, and it is the delivery mechanism for every 'we know this file lost fidelity' warning the importers already produce. Without it those warnings exist only in a log nobody reads. |
| ☐ | ☐ | `agent` | `UNKNOWN` | DESIGN-SYSTEM phase 4 ('new analytics panels') is still marked in progress | (define or close) — the design contract declares itself unfinished with no definition of what 'finished' means. Either enumerate the remaining panels or mark the phase complete. |
| ☐ | ☐ | `agent` | `XS` | /sra renders no takeaway at all when nothing solves | an empty page is indistinguishable from a broken page. One sentence of empty-state copy. |
| ☐ | ☐ | `agent` | `XS` | Doc drift — OPERATOR-REQUESTS.md violates its own rule (OR-03 marked OPEN after shipping) | the operator-request queue is the operator's own view of what they asked for. If it is unreliable in both directions it cannot support a DoD. |
| ☐ | ☐ | `agent` | `XS` | Doc drift — PARITY-REPORT.md still says the reference .mpp files are git-ignored and not committed | this misstates the CUI posture in the parity document. It is the one class of doc error that a reader would reasonably treat as evidence about how the project handles controlled data. |
| ☐ | ☐ | `agent` | `XS` | Doc drift — README.md and USER-GUIDE.md carry stale status and version claims | for README (front door, contradicts risks.md); IN for USER-GUIDE — a user guide 138 versions behind, self-labeled 'refresh pending', is the document the operator's colleagues will actually read. |
| ☐ | ☐ | `agent` | `XS` | Doc drift — REPO-INVENTORY.md says MS Project filters are 'Not yet wired into the UI' | one line, but REPO-INVENTORY is 817 lines of onboarding truth and this entry would send the next agent to build something that exists. |
| ☐ | ☐ | `agent` | `XS` | Doc drift — five RTM rows never refreshed (A1, C1, C3 ▣; Q5, Q6 ◻) plus the Phase-1 heading | none of the five is unfinished engineering; all five are un-refreshed rows. This is the cheapest cluster on the list and it is precisely what makes the project look unfinished on paper when it is not. |
| ☐ | ☐ | `agent` | `XS` | Doc drift — risks.md R-01 and R-04 status lines contradict their own bodies | a risk register whose top CUI risk reads 'Open' with no explanation of what would close it is either alarming or meaningless. Decide which and say so. |
| ☐ | ☐ | `agent` | `XS` | In-tool metric dictionary lacks the two documented Acumen scope differences | the analyst reads help.py IN THE TOOL; PARITY-REPORT.md is a repo file they may never open. Two metrics where the tool counts a different population than Acumen, and the in-tool help does not say so. |
| ☐ | ☐ | `agent` | `XS` | MSPDI reader has no decode ladder — forces utf-8-sig with errors='replace' | an activity name silently corrupted to U+FFFD is an exhibit defect, and `Task.name` is what the analyst reads off every page. Small fix. |
| ☐ | ☐ | `agent` | `XS` | Nine stale unmerged remote branches, several many commits ahead of main | (triage, XS) — almost certainly all superseded, but nobody has checked. Two of them (smat-tool-continuation, smat-adr-0250-decision) are from late July and carry named ADR work. Confirm each is fully  |
| ☐ | ☐ | `agent` | `XS` | Three conditional test skips that can silently void their own assertions | XS, and this repo's own most-repeated defect class is 'a green test that could never fail'. A skip whose condition is now permanently true is exactly that. |
| ☐ | ☐ | `agent` | `XS` | UNCOMMITTED work in the tree: the sub-day negative-float Fuse probe fixture + its guard | this is the artifact that unblocks the single highest-value operator run (Negative-Float O1). It exists but is invisible to the operator and to CI. Commit it, or the next session regenerates it from s |
| ☐ | ☐ | `agent` | `XS` | mpxj_ref() has no shallow-clone guard — the build silently trusts the operator to have unshallowed | XS, and it has been re-carried unchanged through four consecutive ADRs, which is the signature of an item that will never be done unless it is named in a DoD. |
| ☐ | ☐ | `either` | `L` | SRA anchor realignment leaves the simulated network 370 working days shorter than the displayed schedule | the SRA page shows the operator a confidence distribution computed on a network that is not the network the rest of the tool displays. That is a shipped inconsistency between two of the tool's own out |
| ☐ | ☐ | `either` | `M` | Acumen definitional reconciliations never closed: TP3 Leads, Insufficient Detail, HSD07/10 aggregation, DCMA thresholds, .xlsx formula spot-check, per-task detail tabs, Metric-History Failed(T/F) flag | for the two definitional rows (Leads / Insufficient Detail) — those are two metrics where the tool and Acumen count DIFFERENT THINGS under the same name, which is a live misreading risk on an exhibit. |
| ☐ | ☐ | `either` | `M` | Calendar model: single working block only — no multi-shift, no lunch breaks, no per-task calendars in the base model | (decide, not necessarily build) — this is the root cause of the last SSI sub-day residual AND of the P80/P90 residual below. The DoD should either fund it or formally ratify the residual with a stated |
| ☐ | ☐ | `either` | `M` | HSD10 basis delta (engine −148 vs Fuse −134) and SN04 membership swap (UID 99 vs 96) — accepted, not eliminated | as a RATIFICATION — these are two places where the tool and Acumen disagree on the same input and both are 'right' under their own basis. A testimony DoD should name them in the shipped parity report' |
| ☐ | ☐ | `either` | `M` | Offline / air-gapped installer bundle (option B) never built | if the deployment target is genuinely air-gapped — the whole premise of Law 1 is a machine that does not reach the network, and the shipped installers pip-install from the network. This deserves an ex |
| ☐ | ☐ | `either` | `M` | P80/P90 residual ~20 calendar days — importer skips recurring calendar-exception patterns | a ~20-day error on a P80/P90 forecast is a reported number that is wrong. It is logged at import but the log does not reach the page (see import_notes below). |
| ☐ | ☐ | `either` | `M` | Period-over-period metric families still run on the target-truncated focused scope | as a disclosure item — a trend line that silently changes population when a target is set can show a movement that is an artifact of the filter. It must say so on the page, not only in an ADR. |
| ☐ | ☐ | `either` | `M` | XER importer gaps: no suspend/resume read, working_days exceptions dropped, 24h day lost, per-task calendars deferred | if Primavera files are in v1.0's supported scope; DEFER (and downgrade XER to 'structural read only' in the docs) if they are not. The current posture — a documented importer with silent fidelity hole |
| ☐ | ☐ | `either` | `M` | reduce-FILTER can fabricate pair-diffs (documented caveat, deliberately not changed) | same class as above, and worse: 'fabricate' is the ADR's own word for what a shipped filter can do to a comparison. This one belongs in the on-page disclosure set for v1.0. |
| ☐ | ☐ | `either` | `S` | Elapsed-task slack displays on the project 480-minute axis (CC-01 rendering-half debt) | 7.88 displayed where MS Project shows 2.63 for the same task is a number an opposing expert will put on a slide. The minutes are exact; only the axis label/divisor is wrong. Cheap to fix, expensive to |
| ☐ | ☐ | `either` | `S` | HMI Delta: the reference export's cells do not reproduce from the pinned .aft formula | as a RATIFICATION — the tool and the reference tool disagree and the tool has ruled the reference wrong. That is a defensible call but it must be a RECORDED, operator-endorsed call, not a parenthetica |
| ☐ | ☐ | `either` | `UNKNOWN` | Phase 6 — the docs/operator queue was never opened | (define) — this is the placeholder that most of the doc-drift items above should have lived in. Either populate it from this inventory or delete the reference. |

---

## TIER 3 — recommended for the v1.1 backlog (33 items)

Suggested **LATER**. Tick MUST on any you disagree with.

| MUST | LATER | Who | Size | The job | Why (my suggestion) |
| :-: | :-: | :-: | :-: | --- | --- |
| ☐ | ☐ | `agent` | `L` | AI figure gate: no full semantic role model (token matching cannot verify meaning) | but the DoD should state the residual explicitly: the gate guards digits and accusatory terms, not meaning, and interpretive mode is ungated by design. That sentence belongs in the shipped disclosure, |
| ☐ | ☐ | `agent` | `M` | Change counterfactual detects but never measures progress-field changes | the capability; the disclosure shipped. But confirm the on-page '(N excluded)' wording actually names WHY they were excluded — 'excluded' without a reason invites the wrong inference. |
| ☐ | ☐ | `agent` | `M` | Cut the fenced /groups page family out of app.py | internal architecture only. The monolith split's stated goal (no page family left in app.py) is met but for one fenced family; that is a fine place to stop for v1.0. |
| ☐ | ☐ | `agent` | `M` | PARK-LIST P2 — volData six-state migration + EX-03/04/07 live exhibits | strictly blocked behind P1; nothing is untrue while it waits. |
| ☐ | ☐ | `agent` | `M` | PARK-LIST P3 — full SSI vendor→StructuredSolutions rename | pure naming hygiene; zero effect on any reported number. |
| ☐ | ☐ | `agent` | `M` | UI rank 14 — prototype token aliases + universal ⊞ EXPLORE drill wiring | the last unbuilt item of a redesign whose 12 chapters are all shelled. Pure polish. |
| ☐ | ☐ | `agent` | `S` | /analysis focus→tip family is load-sensitive and intermittently fails (adjudicated, unfixed) | proven pre-existing and environment-sensitive, and already carries a 'do not re-chase' note. Ratify as known-flaky. |
| ☐ | ☐ | `agent` | `S` | DATE filter literals share the C4 None shape (null-ordering) | pre-existing and scoped out deliberately; affects filter edge cases, not reported metrics. |
| ☐ | ☐ | `agent` | `S` | PARK-LIST P4 — weighted_instability on the volatility heatmap | the shipped flips-based sort is labeled honestly as the available measure. No false claim. |
| ☐ | ☐ | `agent` | `S` | PBIX deck pages 3, 10 and 11 never reproduced | feature parity with a reference deck is a nice-to-have; nothing untrue is claimed. |
| ☐ | ☐ | `agent` | `S` | The render oracle lost hand-authored variants that were never recovered | honest handling of an unrecoverable loss. The instrument is now committed, so it cannot decay further. |
| ☐ | ☐ | `agent` | `S` | _active_backend / _HB_CONSUME_SEC / _cell / export_path — declined or unmoved monolith residue | every one has a written rationale. Recommend the DoD RATIFY them as 'will not do' rather than schedule them. |
| ☐ | ☐ | `agent` | `S` | pytest-cov / bandit / pip-audit dependency floors were never bisected | self-described as advisory and bounded; these are dev-tool floors, not runtime. |
| ☐ | ☐ | `agent` | `S` | starlette / httpx TestClient transition: a bounded but unresolved upstream break | correctly pinned and documented, and the break is upstream's to land. Revisit when it does. |
| ☐ | ☐ | `agent` | `S` | web/backends.py — promote the AI-backend kernel out of settings.py | refactor polish with zero behavioral effect. |
| ☐ | ☐ | `agent` | `UNKNOWN` | AI-DERIVED-METRICS Phase 3 (surface verified derivations in narrative/briefing) — status unknown | explicitly marked optional. Confirm status in one grep before the DoD is written so it is not silently carried. |
| ☐ | ☐ | `agent` | `XS` | /api/sra/jcl renders 422 in every oracle state | oracle coverage only; the endpoint works when called correctly. |
| ☐ | ☐ | `agent` | `XS` | Declined-with-rationale items that should be RATIFIED as 'will not do', not scheduled | / RATIFY — every one has a written rationale, several are Law-2-correct refusals. The DoD should list them once as 'decided, will not do' so they stop reappearing in every sweep. |
| ☐ | ☐ | `agent` | `XS` | Doc drift — LESSONS-LEARNED Part VIII has a mis-ordered 2026-08-10(e) entry | internal log ordering. Bundle into whatever doc-drift commit happens; not worth its own unit. |
| ☐ | ☐ | `agent` | `XS` | GitHub Actions pinned but not upgraded (checkout v7 / setup-python v7 available) | pinned-and-working beats newest. Pure maintenance. |
| ☐ | ☐ | `agent` | `XS` | TaskTiming.late_start/late_finish are lossy axis projections for off-calendar tasks | no reader outside cpm.py, so nothing displays them. But add a guard that FAILS if a new reader appears, or this becomes a wrong number silently. |
| ☐ | ☐ | `agent` | `XS` | ai/qa.py's workbook fact sheet bypasses the per-epoch briefing memo | a performance duplication, not a correctness one. |
| ☐ | ☐ | `agent` | `XS` | data-sf-hint migration is undocumented in the design contract | documentation of an established pattern. Bundle with any DESIGN-SYSTEM edit. |
| ☐ | ☐ | `either` | `L` | DECM V7.0 EVMS cost-compliance extended audit never implemented | explicitly marked 'optional/extended' in the plan that scoped it. But the DoD should say so out loud, because a reader of METRICS-CATALOG.md would assume it is coming. |
| ☐ | ☐ | `either` | `M` | 99 reference-intake files carry extensions their bytes contradict — deliberately left as-is | measured, guarded, and proven not to reach the product. Ratify as 'will not fix'; renaming would break the pinning tests that make it safe. |
| ☐ | ☐ | `either` | `S` | Integrity baseline movement deltas are calendar days, not working days | labeled honestly and genuinely blocked by what the file carries. Verify the label survives on every surface that shows the figure. |
| ☐ | ☐ | `either` | `S` | cei_critical stays NA on the battery corpus — needs a stored-slack Acumen-parity fixture | merges naturally into the stored-SRA-fields fixture work below. |
| ☐ | ☐ | `either` | `XS` | SSI Driving Slack / Path NN definitions never confirmed against the Deltek Metric Developers Guide | 108/108 exact agreement with SSI on the relative tiers is stronger empirical evidence than a definition read, and it already exists. |
| ☐ | ☐ | `human` | `M` | COM / pywin32 MS Project cross-check importer was planned and never built | but formally WITHDRAW it from BUILD-PLAN.md rather than leave a planned module that does not exist. It was marked optional from the start; MPXJ covers the path. |
| ☐ | ☐ | `human` | `S` | Handbook D5: TFCI / Predicted CPTF deferred on an unresolved sign convention | correctly refusing to ship a metric whose sign is unknown. Exactly the Law-2 behavior wanted. Ratify as 'not in v1.0'. |
| ☐ | ☐ | `human` | `S` | _UseMarking and _BACKEND_PROBE_TTL cannot be lit by an offline oracle | correctly reasoned; both are unit-covered and named as a gap. Would fold into the operator's on-machine probe session if one happens. |
| ☐ | ☐ | `human` | `XS` | Installer Tier 2/3 GPU/VRAM pinning awaits the operator's card model | warn-only detection is a safe default; pinning is an optimization. |
| ☐ | ☐ | `human` | `XS` | OR-03 residuals: the operator's ear is the acceptance for the boot hum, and /example cuts it at unload | cosmetic audio polish with a recorded escape hatch. The operator hears it or does not. |

---

## Excluded

| MUST | LATER | Who | Size | The job | Why (my suggestion) |
| :-: | :-: | :-: | :-: | --- | --- |
| ☐ | ☐ | `human` | `UNKNOWN` | REBUILD-PROMPT / LESSONS-LEARNED Part VI — a DIFFERENT project, listed only so it can be excluded | EXCLUDE explicitly — this is not POLARIS work. It is listed here so the DoD can say so in writing; otherwise the next sweep will surface it again as 'open'. NOTE for the operator: it records two requi |

---

## How this list was built

Three parallel sweeps (durable state · plan/risk/report docs + all source code · 91 ADRs'
"Deliberately NOT done" sections), then a reconciler that de-duplicated, spot-verified the five
most load-bearing items against the repo, and hunted for what the sweeps' briefs could not see.

**Population: 111 items.** The project's own curated queue listed **13** — so ~88% of open work was
invisible to the list the sessions were steering by. That gap is itself the strongest argument for
this file existing.

**One reassuring finding:** the source code is clean — zero `TODO`, `FIXME`, `XXX`, `HACK`, zero
`NotImplementedError`, zero live `xfail` across `src/`, `tests/` and `tools/`. The open work is
documentation truth, parity confirmation needing licensed tools, and deliberately deferred
capability. It is **not** code debt.

**Known blind spot:** no agent in this environment can read GitHub PR or issue bodies, so anything
promised only in a PR comment is unaudited and absent from this list.

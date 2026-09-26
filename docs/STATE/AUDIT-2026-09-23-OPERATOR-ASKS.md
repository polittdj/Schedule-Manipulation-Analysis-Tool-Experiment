# AUDIT-2026-09-23 — Operator asks (one batched list; every live ask has a default; re-issued after the session-2 falsification pass, re-based onto 6bc3138b in session 3, and extended in session 5 (WP-CPM, base 19173728) with ASK-12–ASK-14)

- **T1 — A0923-CPM-001:** every page that prints the schedule-logic (CPM) project finish (/path, /briefing, /brief, /, /portfolio, /forecast, /mission, /trend, /compare, /margin and their APIs) shows the project-calendar date of the finish offset, not the engine's own finish instant: when an elapsed or 24-hour-calendar task drives the finish into project non-working time the date reads a day EARLY (Hard_File_updated3: 12/11/2026 where MS Project, Acumen and SSI show Sat 2026-12-12), and calendar-day finish movements are short by the same day (+35 d for 36). Working-day figures are unaffected. Mechanism since afb8e729 (#497, v1.0.140, 2026-07-31). Until fixed, read the finish from the /path table's rows or the file's own Finish.
- **T1 — A0923-CPM-002 / 003:** on the Large Test File family, an activity whose MS Project split is recorded on the unassigned-work placeholder booking (CPM-002, e.g. UID 7262: 3 working days early, total float 4 days high) and a predecessor linked finish-to-finish to a leveled task (CPM-003, UID 5314: late finish, total and free float 11 working days off) carry CPM figures that differ from MS Project's stored values. CPM-002 wrong at every decidable commit since afb8e729 (v1.0.140; no good commit exists), in its present form since 163d1942 (v1.0.259, ADR-0491); CPM-003 since 5f34c2a8 (v1.0.245, ADR-0474).
- **T1 (latent — no committed file exercises them) — A0923-CPM-005/006/007/008, A0923-IMP-006:** CPM dates and floats are wrong on an operator file that carries a redundant lag-0 SS/SF link from a milestone into an off-calendar task (CPM-005), a worked-day exception on the project calendar (CPM-006), a project start inside the first working block such as 09:00 (CPM-007), logic on a summary task whose children carry custom WBS codes (CPM-008), or an elapsed link lag such as "2ed" (IMP-006). Check an operator file for these shapes before citing its CPM figures.
- **LAW-1 — A0923-CUI-001:** an AI endpoint typed as a HOSTNAME (e.g. `ip6-localhost`) passes the loopback check but is resolved by the OS at send time; where the hosts file lacks it, the CUI Ask prompt can go to a non-loopback address under the "Local-only" banner with no transaction-log record (reproduced in an isolated network namespace; Windows behaviour UNVERIFIED). Exposure: since db285ae2 (#92, 2026-06-13). The shipped defaults (literal 127.0.0.1) are NOT affected — keep a literal-IP endpoint until the fix lands.
- **LAW-1 (transport only) — A0923-CUI-002:** the Ollama cleanup opener (and the launcher's identity probe, and the startup reconcile) follow HTTP redirects to other hosts (body-less GET; no schedule content measured), contrary to ADR-0070's `_NoRedirect` decision. Exposure: since 6b61ad30 (#235, 2026-06-24).
- **T1 — A0923-AI-001/002/003:** an unsourced number can reach the analyst through the narrative / briefing / strict / annotate gates when written as a word ("thirteen"), with a typographic minus or dash (sign flip), or as a fraction/superscript/circled/Roman numeral or zero-width-split digits. Since #69/#79 (2026-06-11). Verify AI prose against the citations until fixed.
- **T1 — A0923-MET-001:** /margin's erosion rate, zero-margin date, consumed % and corrective-action trigger are computed on a mixed basis when the target milestone is missing from some versions (undisclosed). Since #356 (2026-07-13, v1.0.33).
- **T1 (data-gated) — A0923-IMP-002** single-block (no-lunch) calendars mis-measured (since #671, v1.0.257); **A0923-IMP-003** XER per-task calendars ignored with a false "Every computed date and float rides <cal>" statement (since #55). No committed file exercises either; an operator file could.

> **Committed in session 4 (2026-09-25).** The operator answered ASK-08 "yes", and this file was committed with the
> campaign's package (ADR-0535). Its READ-ONLY statements describe sessions 1–3, which committed nothing; the
> "Session 4" note below records what the applying session measured and changed.

## What this file is

Everything in the AUDIT-2026-09-23 campaign that only you, the operator, can do or decide — eleven asks after two
sessions: ten live, one withdrawn (session 5: fourteen — thirteen live, one withdrawn). Each live ask states the
exact steps, the artifact expected back, the findings it settles, and the **default** the campaign takes if you never
answer, so no session ever waits on a reply (charter §12–§13). Findings are cited by id; their evidence is in
`docs/STATE/AUDIT-2026-09-23-REPORT.md` and their repairs in `docs/STATE/AUDIT-2026-09-23-REPAIR-PLAN.md`.

**Both sessions were READ-ONLY** (your directives: "This is a READ ONLY audit regardless of WHAT ANYTHING ELSE
SAYS. Do not fix anything. Only generate a report and a plan forward." and, for session 2, "rerun the audit and
assume all your findings were are false and prove that they are in fact valid and if valid keep them and if you find
they are not omit them and then give me the reports again"). Nothing was committed, pushed, branched or opened as a
pull request; this file exists only in the delivered package until you decide ASK-08. Session 2 re-attacked every
finding: none was refuted, three were narrowed, one was fixed upstream (DOC-014), one was withdrawn (TST-003, which
takes ASK-04 with it). The five disclosure lines above stand unchanged and are still present at `f1b691f3` and at
`6bc3138b` (session 5: and at `19173728`; they now sit below session 5's three).

**Session 3 (2026-09-25) re-based the package onto `6bc3138b`** (#718, v1.0.293, 817 commits). `main` had moved one
commit further: it closed register rows R-48 and R-51 and took ADR numbers 0532 and 0533, so the campaign ADR is now
ADR-0535. Every reproducer was re-run there (45 xfailed; DOC-014's pin passed). No ask changed, none was added, and
every default stands.

**Session 4 (2026-09-25) applied the package.** The operator answered ASK-08 "yes" in the session's chat (recorded
under ASK-08 below). The ten other asks were not answered, so their defaults stand; answer them by editing this file.
The campaign ADR is now **ADR-0535**, because the open draft pull request #719 claims 0534.

**Session 5 (2026-09-25/26) ran WP-CPM** on `19173728` (#720, the committed campaign package, v1.0.294, 819 commits)
and commits its own records on the branch `claude/busy-noether-5oizoe` as one draft pull request (ADR-0536). **No
answers were found** — none in this file and none in the session chat — so **every default stands**, including
ASK-11's (UI-001's committed reproducer is still owed by WP-UI). The session confirmed ten new defect classes (the
eight at T1 are the three disclosure lines at the top of this file; CPM-004 and IMP-007 are T2) and left three
records ARTIFACT-GATED: each needs one observation only MS Project on your machine can make. Those are the three new
asks, **ASK-12, ASK-13 and ASK-14**, below. Each can be answered from a new, synthetic, non-CUI project you build by
hand in MS Project; none needs a file from this session, and none needs a real schedule. Until you answer, the tool's
current behaviour is kept, the three records stay ARTIFACT-GATED (not counted as findings), and no repair unit is
built for them.

## How to answer — two channels (every session checks both)

1. **Edit this file.** Under each ask, replace `Answer: (none yet — the default applies)` with your answer.
   The GitHub web editor is fine once the file is committed (ASK-08).
2. **Or paste answers into the next session's chat**, one line per ask, for example
   `ASK-03: yes` · `ASK-06: keep held` · `ASK-08: yes, commit` · `ASK-11: yes`.

An ask you skip takes its default. A second round of asks happens only if an answer raises a new question.

## ASK-01 — Keep literal-IP AI endpoints until U01 lands; optionally observe the name on Windows (LAW-1)

- **Settles:** A0923-CUI-001's Windows reachability, which is UNVERIFIED (the defect itself is reproduced, was
  re-attacked in session 2 and not refuted, and is fixed by repair unit U01 whatever you answer). Session 2 added
  the platform facts: the Debian/Ubuntu default hosts file maps `ip6-localhost` to `::1`, and the Windows 10
  default hosts file is comments-only (Microsoft support, "How to reset the Hosts file"), so on Windows the name
  falls to network resolution by default unless something else answers it — execution there is what step 2 settles.
- **Exact steps:**
  1. Open POLARIS² → **AI Settings** (`/settings`). Confirm that every AI endpoint field (the Ollama endpoint
     and the OpenAI-compatible endpoint) reads a literal loopback address — the shipped default
     `http://127.0.0.1:11434`, or `http://[::1]:11434` — and not a host NAME such as `ip6-localhost`, and
     that no endpoint contains an `@`. If one does, replace it with `http://127.0.0.1:11434` and save.
  2. Optional, on your Windows machine, in PowerShell: `Resolve-DnsName ip6-localhost` and
     `Select-String -Path "$env:SystemRoot\System32\drivers\etc\hosts" -Pattern "localhost"`.
- **Artifact expected:** "endpoints are literal" (step 1) and, if you ran step 2, the two outputs pasted as text.
  They describe your machine's resolver configuration only; they contain no schedule content.
- **Default if never answered:** assume the name form can reach an off-box address on Windows; U01 is built
  regardless, and the disclosure line above stays until it merges.
- Answer: (none yet — the default applies)

## ASK-02 — The Law-1 policy wording for the approved gateway (A0923-CUI-003, A0923-CUI-004)

- **Settles:** the wording repair unit U13 writes. As built (ADR-0402, ADR-0404), the approved gateway, once
  selected, acknowledged and reachable, carries AI prompts — task names, dates, UIDs and derived figures —
  off the machine under **either** classification; the gateway branch never reads the classification. Eight
  document statements say nothing ever leaves the machine, four promise a loopback-only model server, the
  `/settings` option reads "CLASSIFIED (CUI — local only)", and `/launch` prints "NOTHING LEAVES THIS MACHINE"
  in every state (re-measured on `f1b691f3` in session 2: an armed CLASSIFIED session's Ask prompt was
  TLS-delivered off the box with the task name, UID and ISO date in the body).
- **Exact steps:** answer two questions.
  (a) May schedule content go to the approved gateway while the session is CLASSIFIED? (as built: yes)
  (b) Approve, or edit, this replacement wording for every place that now says "never":
      "Schedule content leaves this machine only when the approved gateway is armed and acknowledged;
      classification does not change that."
- **Artifact expected:** (a) yes or no; (b) "approved" or your sentence. If (a) is **no**, that is a product
  change (the gateway would have to refuse CLASSIFIED sessions), not a wording change: the plan gains a new
  Law-1 unit and U13 waits for it.
- **Default if never answered:** (a) yes, as built; (b) the sentence above everywhere "never" is written, and
  `/launch`'s line made conditional on the observed state (ADR-0396's derivation), as U13 plans.
- Answer: (none yet — the default applies)

## ASK-03 — Exclude the two intake CLAUDE.md files from session memory (A0923-TST-013; operator-only)

- **Settles:** A0923-TST-013 (repair unit U21). Two reference files, `00_REFERENCE_INTAKE/CLAUDE.md` and
  `00_REFERENCE_INTAKE/references/design_handoff_mission_ops_redesign/CLAUDE.md`, load into any Claude Code
  session that reads files in their folders, and carry seven directives contradicting the root rules (CDN
  icons, Google Fonts, a bundler, …). Session 2's refuter executed the trigger in the harness: reading one
  non-CLAUDE.md file under `00_REFERENCE_INTAKE/` injected the 19 KB intake `CLAUDE.md`, and one level deeper
  the 27 KB "standing contract". Only you may edit the assistant's own settings.
- **Exact steps:** in `.claude/settings.json`, add a top-level key `claudeMdExcludes` whose value is an array
  of glob patterns matching those two files, for example
  `["**/00_REFERENCE_INTAKE/CLAUDE.md", "**/00_REFERENCE_INTAKE/references/design_handoff_mission_ops_redesign/CLAUDE.md"]`.
  Check the current Claude Code settings reference first
  (https://code.claude.com/docs/en/settings-reference#claudemdexcludes, retrieved 2026-09-23: "Skip specific
  `CLAUDE.md` files when Claude Code loads memory … Patterns match against absolute file paths."), then commit.
- **Artifact expected:** the merged commit, or "declined".
- **Default if never answered:** not added. CI's air-gap test still fails any build that follows the CDN
  directives (measured: a Google Fonts `@import` or an unpkg script turns `tests/web/test_airgap.py` red);
  the reproducer `tests/audit/test_audit_20260923_tst.py::test_a0923_tst_013_no_loadable_nested_claude_md_contradicts_the_air_gap_rule`
  stays XFAIL.
- Answer: (none yet — the default applies)

## ASK-04 — WITHDRAWN (session 2): the throttled QC trigger

- **Was:** register `.claude/hooks/qc_session_start.sh`, or reword `CLAUDE.md:366-367` and
  `.claude/skills/README.md:45` (A0923-TST-003, repair unit U18).
- **Why it is withdrawn:** the falsification pass showed the decision it asked about is already documented and
  deliberate. `.claude/agents/README.md:40-41`: "registering it must be done by a human — the assistant is
  deliberately barred from editing its own startup/hook config"; ADR-0344:84-86 records the hook as "still
  unregistered and still needs a human". `CLAUDE.md:366-367`
  ("on demand or via a throttled SessionStart trigger") lists routes by which the agent can run — an
  availability statement, not a false claim. Under charter §4, disagreement with a documented deliberate decision
  is not an error, so A0923-TST-003 was withdrawn as a class and there is nothing to ask: registering the hook
  remains a human's settings edit whenever you choose to make it, and no unit waits on it.
- **What survives:** one sentence, `.claude/skills/README.md:45` ("runs the gate *autonomously* on a throttle"),
  which describes a run no committed configuration performs; U18 carries it as a scope note (one conditional
  clause), not as a counted finding.
- Answer: not required.

## ASK-05 — The upload limit: what the docs say and what the page does (A0923-DOC-002, A0923-WEB-001)

- **Settles:** A0923-DOC-002 (U15) and A0923-WEB-001 (U17). `README.md:68` and `docs/USER-GUIDE.md:70` say the
  dropzone takes files "up to 100 at once"; the server loads 101 (measured, and re-measured on `f1b691f3`) and
  refuses more than 1,000 parts in one request with a 400 that the page never shows (it navigates home
  silently). Session 2 established that the 1,000-part cap exists at the declared floor (Starlette 0.37.2) and
  that `home.js` sends the whole selection as one fetch.
- **Exact steps:** confirm or edit: the docs say "no count limit; one upload request carries at most 1,000
  files", and the page reports a refused upload in words instead of returning home.
- **Artifact expected:** "yes", or your preferred limit and wording.
- **Default if never answered:** yes, as stated.
- Answer: (none yet — the default applies)

## ASK-06 — EVM2 UID 25: reopen a held row given new evidence? (HELD by ADR-0505)

- **Settles:** the wave-1 hypothesis F2-H1, reported as HELD. The committed EVM2 golden's zero-duration
  milestone UID 25 carries a MATERIAL booking whose recorded window the engine never reads (the
  `t.duration_minutes > 0` gate at `src/schedule_forensics/engine/cpm.py:903` at `8c71c639`, `:907` at
  `f1b691f3`), so the engine's finish is 2012-10-03 and its Net Finish Impact −21 where the stored finish and
  Acumen read 2012-10-04 and −22. ADR-0505:202-203 left it ("its finish untouched, not this row's"). **New
  evidence:** lifting that gate in memory gives 2012-10-04 and −22 exactly and moves nothing in the other 28 files
  measured (finder and verifier); session 2's refuter re-measured the same engine reading at `f1b691f3` after
  ADR-0531's late-date work.
- **Exact steps:** answer "reopen" (the plan gains a T1 unit after U08) or "keep held".
- **Artifact expected:** the choice.
- **Default if never answered:** keep HELD; it is listed as a candidate row in the campaign's merged queue
  (not added to the 2026-08-27 register — see ASK-07).
- Answer: (none yet — the default applies)

## ASK-07 — One register or two (charter-required)

- **Settles:** where the campaign's 21 repair units live. The living register in
  `docs/STATE/AUDIT-2026-08-27-REPORT.md` §3 (80 rows; 24 still open at `6bc3138b`, eight having closed upstream
  since session 1) is guarded by `tests/guards/test_audit_report_wp8.py`, whose id pattern `R-\d{2}` rejects
  `R-100` (A0923-TST-012, U20).
- **Exact steps:** choose (a) **fold** the campaign's units into the 2026-08-27 register (U20 widens its guard
  first), or (b) **keep** the campaign's own merged queue, which cites R-numbers and never renumbers them.
- **Artifact expected:** "fold" or "keep".
- **Default if never answered:** keep a separate queue; no rows are added to the 2026-08-27 register.
- Answer: (none yet — the default applies)

## ASK-08 — Commit this READ-ONLY campaign's deliverables?

- **Settles:** whether the campaign's charter, report, repair plan, this asks file, the 46 reproducers, the
  campaign ADR (ADR-0535) and the proposed state-doc edits enter the repository. Until they do, they exist
  only in the delivered package: a later session cannot read them from the tree, and every fix kickoff prompt
  therefore carries enough of its finding to rebuild its reproducer red-first. **The package applies on
  `6bc3138b`** (#718, v1.0.293, highest ADR 0533) or a later `main`: session 2 re-based every file on `f1b691f3`
  after `main` took ADR numbers 0527–0531, and session 3 re-based it again on `6bc3138b` after #718 took 0532 and
  0533.
- **Exact steps:** answer yes or no. If yes, start a session with the instructions in the package's
  `README-APPLY.md`: it commits the files on `claude/polaris2-audit-20260923-s1` from `origin/main`, applies the
  proposed state-doc edits, runs the charter §3 pre-push checks (expected: the reproducer modules read 45 xfailed
  and 1 passed) and opens a DRAFT pull request that you merge. If `main` has moved again, the package's `README-APPLY.md`
  section "If main has moved again" gives the exact re-base procedure to run first.
- **Artifact expected:** "yes" or "no".
- **Default if never answered:** not committed. Keep the package: the plan's kickoff prompts and this file are
  the campaign's only record until it is committed.
- Answer: **yes, commit** — the operator, in session 4's chat (2026-09-25). Session 4 committed the package as one
  draft pull request on `claude/confident-hawking-qriorj`, with the campaign ADR renumbered to 0535 (open PR #719 claims
  0534).

## ASK-09 — Promote the `browser` job into `check`'s needs?

- **Settles:** a CI policy question (not a finding). `.github/workflows/ci.yml:112` keeps `browser` outside
  `check`'s `needs` on purpose ("promote it once it has a track record"); at `f1b691f3` and at `6bc3138b` it runs 56
  modules / 502 tests. Session 1's stated blocker — one of its tests red in this container and green in CI, a DUPLICATE
  of R-32 — is gone: ADR-0530 closed R-32 (the oracle reads both pages settled), and the session-2 lead verified
  the module locally (2 passed, twice, with the vendored Chromium where it had failed 3 of 3 at `8c71c639`).
- **Exact steps:** answer "promote now" or "no".
- **Artifact expected:** the choice.
- **Default if never answered:** no change (the ask now stands on its own merits, not on R-32).
- Answer: (none yet — the default applies)

## ASK-10 — Two observations only your Windows machine can make (PKG lane; R-52's residual)

- **Settles:** the installed version the PKG work package measures against, and R-52's residual ("PowerPoint
  itself stays UNVERIFIED — no PowerPoint in any container we can reach; the operator opening either deck
  settles it").
- **Exact steps:**
  1. Open POLARIS² and read the version printed in the header beside the brand (every page states the installed
     build, ADR-0494).
  2. Export a One-Pager deck (`.pptx`) and a One-Pager Compare deck from any schedule, open both in PowerPoint,
     and note whether each opens without a repair prompt and shows its bars, labels and banners.
- **Artifact expected:** the version string, and "both open cleanly" or what PowerPoint said. Do not send the
  decks themselves.
- **Default if never answered:** both stay UNVERIFIED.
- Answer: (none yet — the default applies)

## ASK-11 — Promote A0923-UI-001 into the browser census? (new in session 2)

- **Settles:** whether the next audit session turns UI-001 into a committed Chromium-gated reproducer. Session 1
  filed it UNVERIFIED (one party): `/settings`, `/compare`, `/trend` and `/mission` scroll horizontally at a
  1440-px viewport in Chromium. Session 2's refuter R08, while re-attacking DOC-016 on `f1b691f3`, observed
  `/settings` independently: 1877 px wide in the console, apollo and jarvis themes (1641 in daylight), from a 1598-px
  `<select name=qa_mode>` carrying a 264-character option, while eight other pages read exactly 1440; the route
  is not in `tests/web/test_no_horizontal_overflow.py`'s ROUTES. Two parties have now reproduced it; no committed
  test pins it, so it is a CANDIDATE, not a counted finding.
- **Exact steps:** answer "yes" (WP-UI writes the browser-census test red-first for `/settings` first, then the
  other three pages, in the next audit session) or "no" (it stays a candidate in the report).
- **Artifact expected:** the choice.
- **Default if never answered:** yes, in the next audit session (WP-UI).
- Answer: (none yet — the default applies)

## ASK-12 — Does MS Project hold a "No Later Than" date against logic? (A0923-CPM-009; new in session 5)

- **Settles:** A0923-CPM-009, ARTIFACT-GATED (not counted as a finding; no reproducer). With "Tasks will always honor
  their constraint dates" ON (`<HonorConstraints>1</HonorConstraints>`), the engine HOLDS a Must Start On / Must
  Finish On task at its date against a later predecessor, but schedules a **Start No Later Than** or **Finish No
  Later Than** task at its logic dates and carries the conflict only as negative float; the flag itself is never
  read (0 and 1 give identical output). Microsoft's wording for the option ("constraints take precedence over
  dependencies") supports holding the date; Microsoft's own constraint-definition KB formulas (SNLT "LS=CD (if
  Date<LS)", FNLT "LF=CD (if Date<LF)") match what the engine does. No committed MS Project save carries a
  conflicted SNLT or FNLT, so only MS Project itself can say which reading it uses.
- **Exact steps** (a new, blank, synthetic project; nothing from a real schedule, no file from this session):
  1. File > New > Blank Project. Project > Project Information: Start date **Mon 2026-06-01**, schedule from the
     project start date, calendar **Standard** (the default: Mon–Fri 08:00–12:00 and 13:00–17:00).
  2. File > Options > Schedule > "Scheduling options for this project": tick **"Tasks will always honor their
     constraint dates"**. Keep new tasks Auto Scheduled.
  3. Enter four tasks in this order with these durations: **Z 5d**, **A 5d**, **B 2d**, **C 1d**. Link them
     finish-to-start with no lag, Z → A → B → C (select the four rows, Task > Link the Selected Tasks).
  4. Double-click **B** > Advanced: Constraint type **Start No Later Than**, Constraint date **Wed 2026-06-10
     08:00**. If the Planning Wizard warns of a scheduling conflict, choose the option that continues and keeps
     the constraint.
  5. Write down **B's Start and Finish**, **C's Finish**, **B's Total Slack** and the **project Finish** (Project >
     Project Information > Statistics, or the project summary task).
  6. Change B's constraint to **Finish No Later Than**, **Thu 2026-06-11 17:00**, and write down the same five
     values again.
- **What the answer decides** (hand-computed expectations from the finder's and verifier's records):
  - MS Project shows **B Wed 2026-06-10 08:00 – Thu 2026-06-11 17:00** and **C finishing Fri 2026-06-12 17:00** (the
    project finishing Fri 2026-06-12 17:00) in step 5 and in step 6 → MS Project holds the date as the
    "constraints take precedence" wording says (MPXJ's own scheduler gives the same dates); the engine is wrong
    (it moves the project finish by three working days on this file), and CPM-009 becomes a counted, latent T1
    class with a repair unit.
  - MS Project shows **B Mon 2026-06-15 08:00 – Tue 2026-06-16 17:00** and **C finishing Wed 2026-06-17 17:00** —
    the engine's dates today, with B's total slack negative (the engine: −1,440 working minutes, three 8-hour
    days) → the engine matches MS Project, and CPM-009 is REFUTED.
- **Artifact expected:** the values from steps 5 and 6 typed as two short lines (for example "SNLT: B 06-10 08:00 –
  06-11 17:00, C 06-12 17:00, B slack −3d, finish 06-12"), or this synthetic file saved with File > Save As > XML
  Format (`.xml`). Neither carries any of your schedule content.
- **Default if never answered:** keep the engine's current behaviour; CPM-009 stays ARTIFACT-GATED, uncounted and
  without a reproducer; no repair unit is built.
- Answer: (none yet — the default applies)

## ASK-13 — What unit does a percent lag carry: 25 or 250? (A0923-IMP-008; new in session 5)

- **Settles:** A0923-IMP-008, ARTIFACT-GATED (not counted; no reproducer). The vendored MPXJ 16.2.0 writer — the
  converter the tool uses to read an `.mpp` — writes a 25 % lag as `<LinkLag>25</LinkLag><LagFormat>19</LagFormat>`,
  and MPXJ reads that back as 25.0 %. The tool's importer reads a LagFormat 19 / 20 `LinkLag` as TENTHS of a
  percent, so the lag becomes 2.5 %: 60 working minutes where 25 % of a 5-day (2,400-minute) predecessor is 600.
  Not known: what MS Project itself stores — whether a real `.mpp` percent lag reaches MPXJ as 25 or as 250, and
  whether MS Project's own XML export writes 25 or 250. No committed file has a percent lag (0 of the 21,609 links
  in the 29 tracked `.mpp`, by the verifier's census), so no shipped number moves today.
- **Exact steps** (a new, blank, synthetic project):
  1. File > New > Blank Project. Project Information: Start date **Mon 2026-06-01**, calendar **Standard**.
  2. Task 1, **P**, duration **5d**.
  3. Task 2, **S1**, duration 1d, Predecessors cell **`1FS+25%`**.
  4. Task 3, **S2**, duration 1d, Predecessors cell **`1FS+25e%`** (an elapsed percent lag; if MS Project will
     not accept it, skip S2 and say so).
  5. Write down **S1's Start** and **S2's Start** as MS Project displays them.
  6. File > Save (an `.mpp`), then File > Save As > XML Format (`.xml`).
  7. Open the `.xml` in a text editor, find the `<PredecessorLink>` inside S1's `<Task>` and inside S2's, and copy
     each one's `<LinkLag>` and `<LagFormat>` values.
- **What the answer decides:** the hand-computed expectation for S1 is **Tue 2026-06-09 10:00** (600 working
  minutes after P's finish); the tool today reads the MPXJ-written lag as 60 minutes and starts S1 **Mon
  2026-06-08 09:00**. No expectation is asserted here for S2. An XML `<LinkLag>` of **25** means MS Project writes
  whole percent and the importer is wrong on MS Project's own XML (IMP-008 is confirmed and gets a repair unit);
  **250** means the importer's reading of MS Project's XML is right, and the `.mpp` path is then settled by running
  the saved `.mpp` through the tool and comparing S1's Start with MS Project's.
- **Artifact expected:** the two displayed Starts and the two `LinkLag` / `LagFormat` pairs, typed as text; or the
  synthetic `.mpp` and `.xml` themselves, handed to the session (not committed: the pre-commit guard refuses an
  `.mpp` outside `tests/fixtures/`). None of it is your schedule content.
- **Default if never answered:** the importer's current reading is kept; IMP-008 stays ARTIFACT-GATED, uncounted
  and without a reproducer; no repair unit is built, and the synthetic pin
  `tests/importers/test_mspdi.py::test_percent_lag_format_reads_share_of_predecessor_duration` is left as it is.
- Answer: (none yet — the default applies)

## ASK-14 — Is a "2d" task Leveling Delay two working days or 960 clock minutes? (A0923-IMP-009; new in session 5)

- **Settles:** A0923-IMP-009, ARTIFACT-GATED (not counted; no reproducer). No importer reads
  `LevelingDelayFormat`: a task Leveling Delay stored in format 7 ("d"; 9600 tenths of a minute = 2 working days,
  as MPXJ writes and reads it) is applied as 960 CLOCK minutes, so the task starts a working day early. Every task
  delay in the committed corpus is format 8 (elapsed), so no shipped number moves today; the question is what MS
  Project writes, and how it schedules, when a task delay is entered in working days.
- **Exact steps** (new, blank, synthetic projects):
  1. File > New > Blank Project. Project Information: Start date **Mon 2026-03-02**, calendar **Standard**.
  2. Two tasks, no links: **T7**, duration **1d**; **T8**, duration **1d**.
  3. Show the Leveling Delay column (right-click a column heading > Insert Column > **Leveling Delay**). Type
     **`2d`** for T7 and **`2ed`** for T8.
  4. Write down T7's and T8's **Start** and **Finish**.
  5. A second blank project, Start date **Wed 2026-03-04**, calendar **Standard**: one task **W**, duration **1d**,
     Leveling Delay **`1d`**. Write down W's **Start**.
  6. Save each project with File > Save As > XML Format (`.xml`); in each task's `<Task>` block copy the
     `<LevelingDelay>` and `<LevelingDelayFormat>` values.
- **What the answer decides** (hand-computed expectations from the verifier's record): if MS Project counts a "d"
  delay in working time, **T7 starts Wed 2026-03-04 08:00** (finishes Wed 17:00) — the tool today gives **Tue
  2026-03-03 08:00** (Tue 17:00) — and **W starts Thu 2026-03-05 08:00**, where the tool gives **Wed 2026-03-04
  16:00**. T8 is the control: the tool already reads an elapsed ("ed") delay as elapsed. If MS Project's dates are
  the tool's, IMP-009 is REFUTED; if they are the working-time dates, it becomes a counted, latent T1 class with a
  repair unit. The XML also shows whether MS Project keeps format 7 for "2d" and how it writes the value — 9600
  (tenths of a minute, as MPXJ and the importer assume) or a bare day count (the Microsoft schema page's own
  example writes a 3-day delay as 3).
- **Artifact expected:** the Starts and Finishes from steps 4 and 5 and the `LevelingDelay` / `LevelingDelayFormat`
  pairs, typed as text; or the synthetic `.xml` files. None of it is your schedule content.
- **Default if never answered:** keep the engine's current behaviour; IMP-009 stays ARTIFACT-GATED, uncounted and
  without a reproducer; no repair unit is built.
- Answer: (none yet — the default applies)

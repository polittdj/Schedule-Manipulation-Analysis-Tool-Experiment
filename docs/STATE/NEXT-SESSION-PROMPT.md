# Kickoff prompt — next session

PR state (2026-09-11 d): **#669 is MERGED** — `main` is **`2ae8d06b`** (ADR-0485, v1.0.255; tree-verified;
`main`'s runs CI 1843 / installer-smoke 706 success). The session's third unit, **OR-15 / ADR-0486
(v1.0.256)** — the answer length is the tool's to set (`max_tokens` at the maximum, an honest fallback
when a server rejects it, a cut answer disclosed, an empty answer explained) **and OR-14 corrected: the
operator's backend is the approved gateway, not LM Studio** — is a **draft PR** from branch
`claude/optimistic-ride-3qv2jc`; its number and checks are in the SESSION-LOG's follow-up entry.
**Always `git fetch origin` and read `git log origin/main` before trusting any sha written here.** If
that PR merged, restart the branch with `--prune` + `remote set-head` + `checkout -B`.

**The operator still owes ONE piece of evidence, and it decides the next unit:** the tail of
`ai-transactions.jsonl` (`Get-Content "$env:USERPROFILE\.local\state\schedule-forensics\ai-transactions.jsonl" -Tail 40`
— fields only, the log holds no schedule content). If the `"error":"server returned HTTP 403"` lines
carry larger `prompt_bytes` than the answered ones, the gateway refuses oversized requests and
**Unrestricted mode needs a prompt-size guard** (its own unit, red-first against the measured size);
if equal, the refusal was the gateway's own and nothing in the tool is owed. Do NOT rebuild anything
for LM Studio — nothing listens on the operator's port 1234 (measured).

## The design page is CURRENT, not owed. **Take R-56.**

`/scorecards` (`setScreen('sk')`) wears the Control "Assessment Scorecards" artboard: the family's
cursor strip as NAVIGATION in a `?file=` form (`components._version_chips(..., query="file")`), the
picker byte for byte, the three scorecard panels VERBATIM in the artboard's auto-fit grid
(`cd-grid-3`), the card-head score from the ENGINE's `Scorecard.score` (one decimal, `—` + an empty
bar when unscored, the accent role). **Do NOT re-open:** the mock's score colour thresholds, INFO as a
caution colour, its status-pill rows, its reserve tiles / "No new simulation runs" note / calendar-day
figure, its take block, kicker, single ⤓ and Continue footer are refused BY NAME in ADR-0484. The
in-grid tables lay out FIXED and wrap anywhere because the first grid overflowed a third of the page
in every theme (449 / 585 / 466-px tables in 374-px cards, daylight's card scrolling 463 against
453; apollo scrolled the document at 1527) —
measured, pinned in `tests/web/test_scorecards_grid_browser.py` and in ADR-0477's census.

**Two rules that cost this session real time.**
· **Read every GREEN in a mutation battery as a finding about the instrument.** Three of this
  unit's own checks were weak and were rebuilt by the battery, not by inspection (a slice that ended
  at the thing it looked for; a class extractor that stopped at a space; a word-search that flagged
  the assertion's own prose). One green was a redundant mechanism (`table-layout: fixed` alone is
  equivalent to the wrap rule for the overflow claim) and one was case-equivalent (`_FAMILY` is
  case-sensitive) — each is recorded, not papered over.
· **Grep the artifact FIRST for any string you assert absent** (`cal d` ⊂ "technical data" in the CUI
  notice) — and measure geometry with element rects AND per-cell `scrollWidth − clientWidth`, never a
  panel's `scrollWidth` (jarvis's corner brackets sit at `right:-1px` by design).

**Environment, re-measured 2026-09-11 (b).** The clone arrives shallow; `git log -1 -- tools/mpxj`
reads `c3e4cea0` (a graft-boundary lie). **The "cheap remedy" is HALF a remedy:** `git fetch --depth 1
origin 42d92dc9…` + `SF_MPXJ_REF=42d92dc9acc98f7d87f19c82dc62be3e5d3c15ca` satisfies the BUILDER
(it verifies the tree itself) but writes that sha into `.git/shallow`, and the installer guard
`test_the_converter_pin_is_a_real_touch_not_a_shallow_graft_artifact` then refuses the pin as a
graft boundary — 3 suite failures. Do it the other way: `git fetch --unshallow origin` FIRST (765
commits, a 1.3 GB `.git`, ~1 min), confirm `git log -1 -- tools/mpxj` reads `42d92dc9` on the full
clone, then `python tools/installer/build_installers.py dist/wheel/schedule_forensics-*.whl`. Install with `uv pip install --python /usr/local/bin/python3 --system -e '.[dev]'
build playwright` (never `playwright install` — use `tests/web/browser_chrome.py::chrome_kwargs()`).
**`/root/.local/bin/ruff` 0.15.8 shadows the CI-version `/usr/local/bin/ruff` on PATH** — run both
before calling format clean. **Keep the token-guardian's `token_audit.py` in the scratchpad** —
`ruff check .` is whole-tree. Re-`uv pip install -e` after a version bump or `__version__` lags.
Executing the canvas: `npm pack react@18.3.1 react-dom@18.3.1 @babel/standalone@7.29.0`, repoint
`support.js`'s three `*_URL` constants at `./pkgs/<name>/package/...` and blank the `*_SRI`
constants, `python -m http.server --bind 127.0.0.1` in the copy, seed `sfredux-screen` /
`sfredux-guided=1` / `sfops-boot.skipNext=true` / `sfredux-theme` via `add_init_script`, wait for
`section[data-screen-label="…"]` visible (Babel needs ~10 s), census the DOM.

**Three steward traps, all measured — do not re-learn any of them:**
1. `pull_request_read` method **`get_status`** returns `{"state":"pending","total_count":0}` on a PR
   whose checks are ALL green — that is the LEGACY commit-status API. Use **`get_check_runs`**.
2. A `check_suite.completed` event can carry a **superseded** `head_sha`. Re-read the current head.
3. Check set: **eight** when `installer/**` changes (this PR does), **six** for docs-only.

**Take R-56** — the operator queue is EMPTY of blocking rows and the design page is current. R-56 is a
duration-CONTOUR defect on UNSTARTED work, so no progress rule reaches it, and it is what still holds
`Hard_File_updated3`'s finish 13 d early after ADR-0476. updated3 has **SEVEN** chain heads and 45 rows
inherited from them; the report names only UID 403, and **UID 385 is the larger driver**:

| UID | duration | engine span | MS Project span |
|---|---|---|---|
| 385 | 5,664 min | ~6 wd (944 min/d) | ~17 wd (333 min/d) |
| 403 | 1,920 min | ~5 wd (384 min/d) | ~14 wd (137 min/d) |

MS Project is spreading these at a FRACTION of a working day — a contoured / part-time assignment
the booking rule does not model. First executable step: tally `<Assignment>` Units, Work and any
TimephasedData for 385 / 403 / 302 against their `<Task>` Duration, and **check the rule against
EVERY golden by task Type** before believing it. What settles it: updated3 within a day of the stored
2026-12-12 with `-m parity` unmoved and Project2 / Project5 still exact.

**Heads-up on review cover:** `chatgpt-codex-connector[bot]` reported EXHAUSTED Codex review quota
on #655–#661. Until it is restored, the mutation battery and the full gate are the only review this
repo is actually getting.

Work the POLARIS² audit's plan-forward (Schedule-Manipulation-Analysis-Tool). Read
`docs/STATE/HANDOFF.md` FIRST (auto-injected), then `docs/STATE/AUDIT-2026-08-27-REPORT.md` §3 — the
roadmap by testimony tier, pinned by `tests/guards/test_audit_report_wp8.py`. QC-1/QC-2 bind every
session (ADR-0393). `git fetch origin` before you branch, number an ADR, or commit.

⇢ WHAT'S DONE — do not re-open. WP0–WP8 (ADR-0440..0472) · ADR-0473 (R-01) · ADR-0474 (R-44) ·
ADR-0475 (/standards on the design) · ADR-0476 (R-55) · ADR-0477 (R-20 / UI-03) · ADR-0478
(`/api/ask` says WHY there is no written answer) · ADR-0481 (OR-11e) · ADR-0482 (OR-12) · ADR-0483
(OR-13 — `SHUTDOWN_DRAIN_TIMEOUT = 5`; `active_requests > 0` does NOT protect a streaming response;
`force_exit` stays rejected) · **ADR-0484 (/scorecards on the design — see above). The design queue:
10 done, 20 artboards remain; `/margin` (Control Margin Dashboard, `setScreen('mg')`) is next by
cost, the last Control screen.** · **ADR-0485 (OR-14 — the local OpenAI-compatible server's Bearer
token: `AIConfig.openai_api_key`, the 4-arg `HeaderOpener`, the *Local server API token* field, the
401/403 note that names the field AND the cause the tool cannot see; the gateway-endpoint mislabel
fixed).** · **ADR-0486 (OR-15 — `ai/completion.py`: the *Answer length limit* field, default = max,
`max_tokens` on both OpenAI-compatible backends with one retry without it on a 400 that names it;
`finish_reason` / reasoning / `usage` read as `last_completion`; a `length` stop disclosed beside the
answer; an empty answer explained; `null` content empty, never "None"; a gateway 403 with a valid key
names entitlement + prompt size + the transaction log. OR-14 CORRECTED: the gateway, not LM Studio.)**

⇢ NEXT — the report's §3 in order, one row per unit of work (red-first → mutation proofs by name →
the full gate → an ADR → the state docs → a draft PR): **R-56** FIRST (above) · **R-49** — MPXJ omits a
ZERO `TotalSlack` (62 of Fuse's 66 zero-float activities on LTF2 carry none): the importer infers 0
when the file carries the element elsewhere and the task carries `Critical`; red-first on Fuse's Zero
Days Float 66 / 2 · R-46 (BCWS +150) · R-47 (SPI(t) 8.24 vs 8.22) · R-52 (the `.pptx` LibreOffice
refuses) · R-50 (expose the History variants) · R-57 / R-58 / R-59 · then R-03 · R-04 · R-09 · R-13 ·
R-18 · R-21 · R-22 · R-32 · R-39. PLUS the design page owed each session — **now CURRENT**: the next
is `/margin`, recipe in ADR-0471 / 0475 / 0484 (execute the canvas; census the artboard; port the
layout with every id, form byte, panel, glyph and figure; refuse and NAME every mock claim the engine
does not make; measure in four themes; a battery whose greens are read).

⇢ Traps paid for, by name (2026-09-11 e first): **a fixed bug is evidence against the hypothesis it
lived under — re-read every conclusion drawn through a mislabel the moment the mislabel is found** ·
**"raise the limit to the max" has no number: a bounded default plus a disclosed fallback** · **the
battery found a FALSE claim ("the deployed wrapping") — the app wraps only Ollama (ADR-0315)** · **read a
completion as evidence, never `str()` it**. (2026-09-11 c/d:) **a diagnostic that names a PAGE is true and
useless when that page reads ON — name the FIELD, and state the cause you cannot see** · **condition
a hint on what the transport proved, never on "unreachable" as a catch-all** · **a page-wide substring
assertion the page's own form satisfies cannot fail — read the element** · **negative pins are green
on the pristine tree by construction; prove them with a mutant** · **the same defect class lands
twice when a spec has no auth dimension — give every OpenAI-compatible surface one from day one**.
(2026-09-11 b:) **read every green in a battery as a finding about
the instrument** (three rebuilt this unit) · **grep the artifact FIRST for a string you assert
absent** (`cal d` ⊂ "technical data") · **a rect cannot see text spilling inside a fixed cell; a
panel's `scrollWidth` sees jarvis's decoration** · **two sufficient mechanisms make a single-rule
mutation equivalent, not weak** · **a mutation can be case-equivalent** (`_FAMILY` is case-sensitive)
· **a faithful port of a mock's grid re-introduced the UI-03 class in apollo** — measure every theme.
(2026-09-10 b:) **a repro that does not reproduce is a result** · **put the red arm INSIDE the test**
· **the shallow clone lies about the MPXJ pin, generously** (`+60`/`+200`/`+400` each look real).
(2026-09-09 b:) **an oracle read out of the state under test cannot judge that state** · **a mutation
with `old == new` proves nothing** · **engineer the red to prove the instrument**. (2026-09-09 a:)
**an assertion is only as strong as the text that was NOT already there** · **the suite measures the
tree as it was at second zero — freeze, build, THEN run** · **run the CONTROL before believing your
own new instrument** · **refute your own hypothesis first**. (Earlier, still live:) a green suite is
not evidence the INPUTS are consistent · when a change makes the engine honour a previously-ignored
input, sweep for code whose correctness depended on it being ignored · two errors can CANCEL · an
inherited attribution is TESTIMONY · a GREEN mutation may mean the FIXTURE CORPUS cannot express the
case · Playwright's virtual mouse SURVIVES `goto()` — park it · an `assert` in `src/` is a house-style
violation · a design mock's status word, decomposition and export label are claims about the ENGINE ·
a mock that HIDES is proposing a functionality change · MS Project's stored dates are a per-activity
CPM oracle · `LevelingDelay` is tenths of a minute · a booking rule proven on one file breaks another ·
MPXJ writes no zero · `Large_Test_File.mpp` ≠ `Large Test File.mpp`.

⇢ Measured-false / deliberately held — do NOT re-chase: the ribbon tiles' scopes · TP3's ribbon 8 /
Lags 3 (R-53) · the DCMA08 baseline basis (R-48) · Fuse's ACWP-to-time-now and updated3's BAC (R-45) ·
the four Hard_File bookings the MSPDI cannot explain (R-56) · R-20 / UI-03 (ADR-0477 — every page
measures `scrollWidth == innerWidth == 1440`; `/scorecards` is now IN that census) · the HELD and
CLOSED rows of the report · the S-curve & finish-window residuals of earlier sessions.

⇢ Residuals registered, none taken: **`test_driving_path_whole_schedule_browser.py:104` is
WIDTH-RACY** (registered by #667, carried forward — red on a docs-only PR while `main` passed the
identical code two minutes earlier; it compares the rendered `thead` inner_text of two separately
rendered pages while both captures wait on ROWS, never on the timescale. A race with a mechanism, not
a flake — its own unit, and **never** fix it by widening a wait) · **`/settings` scrolls sideways** (an over-wide `<select>`; its own
UI unit) · **the working-minute axis cannot carry a recorded instant on a day boundary or a
non-working moment** (structural) · **the hint bubble still widens the document WHILE OPEN** near
the right edge · **OR-11b** (measure the 48-fact cap on a real 32-file workbook first) · **OR-11d**
(`_AskRecord` exports an unanswered ask without its reason) · **ADR-0483's own** (a live-peer response
is cut at 5 s) · **ADR-0485's own:** `_gateway_status_note` still detects a refusal by substring
(`"401" in reason`) — a one-line unit onto `is_auth_refusal` with its own red; the live model dropdown
probes with the SAVED token only (Save first; the gateway behaves the same) · **ADR-0486's own:** a second
`max_completion_tokens` attempt before falling back to no limit; an output-side disclosure for Ollama
from `GenerationStats.done_reason`; the cross-check's `last_completion` recorded but not surfaced · **NEW, ADR-0484:** the in-grid scorecard rows as the mock's compact status-pill row
WITHOUT losing table semantics — at 1440 the cells wrap hard and apollo breaks long tokens as a last
resort; ⛶ ENLARGE gives any card the full viewport meanwhile.

⇢ Steward posture: draft PRs the OPERATOR merges (never mark ready, never merge, never approve); eight
checks when `installer/**` changes, six for docs-only; read a verdict on the FINAL head; a red cell on
`main` for a tree identical to the green PR head is the runner's claim — compare tree hashes first;
after a squash-merge restart the branch with `--prune` + `remote set-head` + `checkout -B`, never amend
the squash; the post-merge safety check is `HEAD^{tree}` vs `origin/main^{tree}`, NEVER
`git log origin/main..HEAD` (#666's correction).

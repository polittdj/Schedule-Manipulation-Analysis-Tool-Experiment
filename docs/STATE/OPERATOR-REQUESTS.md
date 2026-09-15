# Operator requests — the standing intake queue

Verbatim-intent capture of feature requests the operator raises mid-session, parked here so they
survive the session that received them. **This file is durable state** alongside `HANDOFF.md` /
`SESSION-LOG.md` / `LESSONS-LEARNED.md`: an item is added the moment it is raised, and removed only
when it ships (with the ADR / PR that closed it recorded on the line).

Status vocabulary: `OPEN` (not started) · `IN FLIGHT` (a round owns it) · `SHIPPED (ref)` · `PARKED
(reason)`.

---

## 2026-07-28 — `07282026_Prompt_Notes.docx` (received mid-round-11)

### OR-01 — Per-project summary must name what each metric is computing · `SHIPPED (ADR-0321)`

Every individual project schedule should list, **for every file**:

- SITE / COMPANY
- VERSIONS
- LATEST DATA DATE
- COMPUTED FINISH
- EFFECTIVE MARGIN
- DCMA-14 score

…and when the project is **wrapped up** (the rolled-up, one-row-per-project view), show:

- the SITE / COMPANY name
- the **number of versions** (how many schedules make up the project)
- the **LATEST DATA DATE** of the latest file
- the **most recent COMPUTED FINISH DATE**
- the **most recent EFFECTIVE MARGIN**
- the **average DCMA-14 score across the schedules**

**And the metric TITLE itself must make clear what the view is computing** — i.e. a rolled-up column
must say so in its heading ("Average DCMA-14 across N versions", "Latest data date"), never reuse the
per-file label for an aggregate. Reading the title alone must tell the analyst whether they are
looking at a latest-value or an average.

*Implementation notes for whoever picks this up:* this lands on the portfolio/ledger surface
(`_portfolio_body`, `/portfolio`) and the per-project card views. Law 2 applies — the aggregation rule
for each column is a **stated** rule (latest vs mean), and the heading must match the rule the engine
actually applied. Do not invent an aggregate the engine does not compute.

### OR-02 — A help call-out sticks over the left menu bar and cannot be dismissed · `SHIPPED (ADR-0314)` · **BUG**

> "I keep getting this weird call-out that covers the menu bar on the left side of the screen that I
> can't get to go away unless I switch to another page but then it will return. This should never
> happen. It is the DCMA 11 — Missed Activities call-out which explains what it is, why it matters,
> threshold, pass example, etc."

Reproduced, measured, and closed as **two** defects in the DCMA-overview float tip (`app.js`, not
the hint layer the notes guessed): a FOCUS-shown tip (what a click/tap does) had no reachable
dismissal — Escape, pointer-away, and alt-tab all stuck — and the nav-avoidance clamp tested for a
`fixed` header only, so daylight's `sticky` full-width bar was never avoided (overlap measured at
three viewport sizes). Fixed with document-level Escape/pointer/blur dismissal + a fixed-OR-sticky
clamp that clears a rail sideways and a bar downward. Both pinned by measured-box tests
(`tests/web/test_float_tip_dismiss.py`, the operator's own DCMA-11 callout by name). ADR-0314.

### OR-03 — Launch Sequence: motion + a full-length boot hum while projects load · `OPEN`

On the boot-up start screen (the **Launch Sequence**):

- keep the visuals showing **while projects are loading**, with "something flying around" so it is
  unmistakable that the tool is working and **not frozen**;
- play a **longer version of the Boot Audio "Hum"** for the **entire** load;
- **mix the audio correctly** if a loop is used — no audible seam;
- the source audio must be **at least a minute long** and must **not be one repeating sound**: a
  *series* of similar sounds, a *pattern* of the "Hum" boot audio.

*Implementation notes:* the loading indicator must be driven by real load state (start on upload,
end on ready) — never a fixed timer that lies about progress. Honor `prefers-reduced-motion` for the
animation and keep audio opt-in/mutable per the design system's a11y line. Audio must be a **local,
vendored** asset (Law 1: no remote fetch, and the air-gap test must stay green).

---

## 2026-07-30 — chat report (mid-planning session)

### OR-04 — Ollama's model runner keeps the GPU after quit · `SHIPPED (ADR-0315)` · **BUG**

> "when I open the tool and then close the tool Ollama stays active and it is eating up my
> Dedicated GPU memory."

Reproduced by the operator (enable in AI Settings → ask → wipe → quit): `llama-server.exe`
resident post-quit at ~10.9/12 GB dedicated VRAM and ~30 GB committed shared GPU memory, while
both of the tool's own cleanup taskkills reported "process not found". Behavior ruling (operator,
same day): **free the GPU on exit** — stop the runtime if the tool started it; if it is an
external service the tool merely used, unload the model (`keep_alive: 0`); never kill a process
the tool didn't start.

Root cause per the operator-gated adversarial audit
(`audit/VERIFICATION-REPORT-ollama-lifecycle.md`): shutdown no-opped for default-config use
(`_engaged` set only by the Settings POST), and the engaged path's own kill ordering orphaned the
runner (parent terminated before the `/T` tree-walk) with every failure invisible. Closed by the
three-tier shutdown + durable marker + startup reconciliation (ADR-0315). Operator verification:
the four-scenario smoke script in the PR body; park artifacts #1/#3/#5 (+#4) remain open in the
audit's §8.

---

## 2026-07-31 — session prompt (engine-correctness deep dive; pre-empts the PR-8/9/10 queue)

### OR-05 — PowerPoint-oracle parity for the two "Jacked" schedules · `SHIPPED (ADR-0322/0323)`

**Outcome:** the base CPM now honors per-task calendars (24-Hours task, eDays as the 24/7
degenerate case) with float measured in the task's own calendar minutes — every stored Total
Slack on both files reproduces EXACTLY (36 900 / 3 780 / 3 840 / 480 / −2 400 / 6 240 min),
finish 10/07 / 10/09, critical sets match, a violated MSO/MFO pin reports MS Project's negative
slack, and the Bible-named Open Start / Open Finish dangling checks catch the slide-1 pair.
**One file-vs-slide divergence, verified and NOT chased:** the committed
`Jacked up Schedule 2.mpp` does not contain Task 11's deadline (MPXJ provably reads MPP14
deadlines elsewhere; the .mpp's last save 09:23 EDT predates the pptx's final edit 10:29 EDT —
the deadline was added after the last save). The tool therefore correctly shows +13 d for
Task 11, the slide's own stated no-deadline outcome. **Operator action if desired:** re-save
the .mpp with the deadline set; the pipeline already flows it (pinned by test) and Task 11
will then read −5 d.
**CLOSED same day:** the operator re-saved the file with the deadline and uploaded it
(operator will also add it to `00_REFERENCE_INTAKE/` on main). Verified end-to-end with ZERO
code change: UID 32 deadline 2026-08-14 imports, stored TF −2 400 == recomputed −2 400 exactly
(every task exact), critical set gains Task 11, DCMA-07 cites all three −5 d tasks (29/30/32) —
the slide-6 picture precisely. The conversion is pinned as
`tests/fixtures/mspdi/jacked_up_schedule_2_with_deadline.xml` with its own regression test.

Three files are committed on `main` under `00_REFERENCE_INTAKE/mpp/` (non-CUI, operator-added via
the GitHub web UI, `inherited_from_main`): `Jacked Up Schedule 1.mpp`, `Jacked up Schedule 2.mpp`
(note the case difference), and `Politte Schedule Tool.pptx` (6 slides). The PowerPoint explains
the two `.mpp` files — they are built with **KNOWN issues the tool must identify** (named classes:
**Dangling Tasks**, **eDays/elapsed durations**, **Total Slack calculation**).

Operator intent, verbatim capture: READ EVERYTHING, ASSUME NOTHING — extract and read every slide
(text, tables, notes, embedded images), convert both `.mpp` via
`java -cp tools/mpxj/classes:tools/mpxj/lib/* MpxjToMspdi <in> <out>` (verified working on both:
16 and 12 tasks), and read every task/link/calendar field. Then run the tool on both files and
compare **EVERY output** (CPM dates, Total Slack per task, DCMA-14 verdicts and offender lists,
dangling/logic checks, float metrics, finish, margin) against the PowerPoint. **The PowerPoint is
the oracle — the tool is known to be WRONG on these files.** For each variance: root-cause it in
the engine, write a test that FAILS on the current code (prove-able-to-fail), prototype the fix in
a sandbox, iterate until validated, then implement it **GENERALLY** — engine-level, applying to any
file the tool ever runs (no special-casing these two), so future eDays / dangling-task / Total
Slack cases are always computed correctly.

Recon hooks recorded with the request (verify, they may drift): Jacked 1 carries a
`DurationFormat=8` (eDays) task — intersects the carried debts CC-01 rendering half (74 call
sites), V3 elapsed literals (`engine/msp_filters.py`), and CC-05 negative sub-day slack floor;
`engine/metrics/_common.py::effective_total_float` prefers the file's STORED Total Slack over
recomputed CPM float — triage every slack variance as stored-vs-recomputed FIRST. Engine changes
are in scope (Law-2 work); the parity gate (`pytest -m parity`) and goldens must stay green — any
legitimately-shifted pin gets a DELIBERATE ADR-named re-baseline via that pin's own path, never a
silent update. If the PowerPoint and the `.mpp` bytes genuinely contradict, STOP and ask the
operator rather than "fixing" to a misread oracle.

### OR-06 — Fresh launch shows stale fields from previous sessions · `SHIPPED (ADR-0324 + ADR-0332 + ADR-0334)` · **BUG**

> Operator: a fresh open of the deployed tool shows fields populated from PREVIOUS sessions
> (e.g. Target UID from a project never loaded), even after wipe-then-Quit.

**OPERATOR MEASUREMENT, 2026-08-01, on the deployed box (v1.0.149) — THE ANSWER IS ONE PID.**
This is the datum Phase 1b was blocked on. Captured verbatim because it took three runs to get a
valid one and it must never have to be re-collected:

| step | LISTENING on 8321 | `pythonw` processes |
| --- | --- | --- |
| after stopping | none | none |
| after **1st** launch | **18664** | 18664 + 39740, both 19:33:17 |
| after closing **only the browser** | **18664** (survives) | 18664 + 39740, both 19:33:17 |
| after **2nd** launch | **18664** | 18664 + 39740, **both still 19:33:17** |

**The second launch produced NOTHING — no new listener, and no fourth process even transiently
(25 s later the process list is byte-identical).** So the second launcher started, failed to take
the port, exited mute, and its already-queued browser timer opened onto the OLD server. That is
the handoff's branch one, confirmed: `sys.exit` into `os.devnull` under `pythonw`, browser timer
armed BEFORE the bind. It also defeats ADR-0324's launch token — same process, same token.

**Consequence for this item: OR-06 has a SECOND, deeper cause than the localStorage one below.**
The stale fields are not only browser memory — **the server itself is the previous session**, still
holding the previously loaded schedules and settings in RAM. No client-side sweep could ever have
fixed that half.

Two corroborating facts from the same session: an earlier snapshot showed PID 24788 LISTENING with
**zero** ESTABLISHED connections — a survivor inside its grace window; and the watchdog grace is
`idle_grace=600.0` (`web/app.py`), i.e. the server legitimately outlives the browser by up to **10
minutes**, which is the window in which a relaunch lands on the old process. A first attempt at the
measurement showed the server gone 25 s after the browser closed — that run is DISCARDED as invalid
(it contradicts the 600 s grace; Quit was evidently clicked), and is recorded here only so the
contradiction is not re-investigated as a finding.

Root cause is VERIFIED mechanism-level: `web/static/persist.js` (ADR-0186 per-page selection
memory) stores `sf-qs:<path>` (query strings incl. `?target=…`) and `sf-ui:<path>` (control
values) in browser localStorage, which survives server wipe/quit by design of localStorage —
nothing invalidates it for a new session. Fix so a wipe and/or a fresh server launch invalidates
the per-page selection memory (e.g. a server-issued launch/session ID that keys or clears the
`sf-qs:`/`sf-ui:` layers), WITHOUT killing ADR-0186's within-session page memory or the global
prefs (theme/scale/timescale are deliberately separate). UI change → DESIGN-SYSTEM.md rules; check
for JS digest/line pins over `persist.js` BEFORE editing; own ADR.

---

## 2026-08-14/15 — the gateway arc (chat directives, received live during builds)

### OR-07 — "I don't get the option to use the NASA approved AI models that are itar approved. Fix this." · `SHIPPED (ADR-0402, PR #590, v1.0.202)`

The 001c decision, made by this message. The approved AI gateway became a first-class backend:
allowlisted endpoint select, approval acknowledgment, warning banner, AI transaction log.

### OR-08 — Gateway answered HTTP 401; "the models dont show up" · `SHIPPED (ADR-0403, PR #591, v1.0.203)`

Bearer authentication with credential-grade handling (masked never-echoed key field,
blank-means-keep, `SF_GATEWAY_API_KEY` fallback, key never in log/page/repr/URL).

### OR-09 — "I do not want to have to put in the NASA API KEY everytime I open the program. I want it to work when I click on the desktop icon. Super simple." · `SHIPPED (ADR-0404, PR #592, v1.0.204)`

ALL AI settings persist across launches (`ai/config_store.py`; DPAPI-wrapped key on Windows;
load-boundary sanitizers). Arm once — every desktop-icon launch comes up armed.

### OR-10 — "Start that work and update whatever documentation … so that we don't get lost with what we have left to do or where we are and what we still have left to verify." · `IN FLIGHT`

The agent-only queue has been worked to completion — all four units shipped (ADR-0405 →
ADR-0408; the repo is xfail-free). This section is the requested ledger; `HANDOFF.md`
(auto-injected every session) and `NEXT-SESSION-PROMPT.md` carry the same state with
per-unit rotation. **Every remaining open item on this page is operator-owned.**

## 2026-09-15 (b) — "Once this PR is squashed and merged I want you to add at the top of the launch page the version number of the installed program"

### OR-18 — "… add at the top of the launch page the version number of the installed program so that we don't have to go through so much effort to tell if the correct version has been uploaded to my computer." · `SHIPPED (ADR-0494, v1.0.262): the Boot Screen line and the header chip on every page`
### OR-19 — "I am still getting this error message when I try to connect to the NASA approved API LLMs that are approved for CUI and ITAR use. Find the root cause for this error and fix it." (2026-09-15, the v1.0.262 screenshot) · `SHIPPED (ADR-0496, v1.0.264): root cause = the credential expired at the AI Hub on 2026-09-12 20:36:47 UTC (the gateway's own words, quoted by the banner); the tool now names a re-paste of the held key as such (a warning, never "replaced") and leads the refused-key banner with the expiry date, how long before the request, and the one remedy (a NEW key from the Hub); the operator generated a new key the same afternoon and reports it works`

**Resolved from the code, not guessed:** "the launch page" is `/launch`, the Boot Screen (ADR-0426) the
desktop icon opens on — OUTSIDE the story chrome (no header, no nav), rendered by
`web/launch.py::_launch_html`; its first element is the CUI bar (design system §6: never displaced).
**The unit:** a server-rendered line directly under the CUI bar carrying the installed package version
(`chrome._ASSET_VERSION` — the running process's metadata, never a literal), `data-no-i18n`, tokens only,
present even when the boot script never runs (the hero text is script-filled; this line is not);
red-first (the pristine `/launch` carries no version), measured in Chromium in the four themes with the
CUI bar still first, mutation by name (the line dropped; the version a literal); ADR-0494, v1.0.262,
wheel + nine installers, the full gate, a draft PR. **Stated to the operator:** the line witnesses what is
RUNNING (an older copy still serving the port shows its own, older, version — the truth); the installer's
console banner is the only witness that the upload happened. **DIRECTED (operator, 2026-09-15 ~14:40Z: *"I agree with your
recommendation"*):** the same chip in the global header (`chrome.py`'s `<header>`, beside the brand,
`--header-muted`, `data-no-i18n`, never displacing the CUI bar or the nav, measured at 1,440 and a narrow
width so no sideways scroll is added) so every page and every screenshot pins the build — the two surfaces
are ONE unit (AI Settings already carries `tool version:` since v1.0.261).

## 2026-09-12 — the approved gateway refuses a SAVED key on the availability probe (HTTP 401; the AI Settings screenshot, then two PowerShell runs on the NASA machine); "I want the AI setup to be as user friendly and simple as possible."

### OR-17 — "This is what I am getting when I try and activate the AI models approved for ITAR and CUI. I input the API code as I always have and it doesn't work. I also have no clue what 'Local server API token (LM Studio "Require Authentication" …)' means or does. This is new. … solve in the next session by getting to the root cause and creating tests, pass and fail, and testing your solution in a sandbox environment until you find a solution that fixes the problem." · `SHIPPED IN PART (ADR-0493, v1.0.261): the installed build measured, the tool's key path proven on the wire and on real Windows, a Save receipt, the version on the page; the key itself stays the operator's — V-4 and one more request settle the rest`

**MEASURED 2026-09-15 (ADR-0493) — read this before the registration below it.**

1. **The installed build is v1.0.255 or v1.0.256, NOT v1.0.257+.** The screenshot's placeholder
   *"(a key is saved — leave blank to keep it)"* and its banner *"could not reach … requires
   authentication: paste your organization-issued key"* are the pre-ADR-0488 strings: at the
   v1.0.257 commit the placeholder reads *"a key is saved — N characters; …"* and the banner
   *"refused the credential the tool sent"*, and `data-backend-only` (the one-backend rule) is
   absent at 0.255 / 0.256 and present at 0.257 (`git show` on the three release commits). Every
   diagnostic OR-16 shipped never reached the operator's machine; the "every backend's fields at
   once" is that build, not a regression. **Install v1.0.261 first.**
2. **The tool's key path is NOT the cause — measured, not read.** On this tree a key pasted once
   survives a fresh launch and authenticates byte for byte on the REAL urllib transport against a
   loopback fake of the gateway that demands exactly `Authorization: Bearer <key>`
   (`tests/web/test_gateway_wire.py`); a stale key on disk renders the photographed banner with the
   gateway's own reason and the key's length. The Windows DPAPI branch: its Python (struct layout,
   buffer lifetime, length, flags, `LocalFree`) runs against a fake `crypt32` on every CI
   (`tests/ai/test_dpapi_marshaling.py`); the real Win32 calls run on a real Windows runner in
   `installer-smoke.yml` (round trip of a 25- and a 67-character key, no plaintext at rest, a
   tampered blob comes up keyless) — **its first verdict is in the SESSION-LOG follow-up**.
3. **The failure the installed build could not show — a fresh key pasted into the WRONG masked
   field.** On 0.255 / 0.256 the *Local server API token* field sits directly above *Gateway API
   key*; a paste there keeps the OLD gateway key (blank keeps, ADR-0403), the page reads *"a key is
   saved"* and the gateway keeps refusing — reproduced red on the pristine tree. v1.0.261 answers
   every Save with a one-shot receipt (*"Gateway API key: replaced — 25 characters now held"* /
   *"kept (the field was blank …)"*) and a warning when a credential lands in a field no selected
   backend uses; the local-token label now says which backend uses it and that the gateway never
   does; the page states its own version so the next screenshot pins the build.
4. **What only the operator can settle (asked again, not blocking):** V-4 — the gateway's own
   refusal text (on v1.0.261 the banner quotes it, including a scheme-only challenge such as
   `Basic realm=…`, which would mean `Bearer` is the wrong shape); and **whether the key being
   pasted is the CURRENT key from the NASA AI Hub** — on 2026-09-12 the same key answered HTTP 401
   outside the tool (PowerShell), so a key that "always worked" and is refused since 09-12 has
   expired, been rotated or lost its entitlement. The catalog-refused-but-generation-works
   hypothesis is registered UNVERIFIED (the tool gates routing on `GET /v1/models`); one request
   settles it: `Invoke-RestMethod https://proxy.fast.luna.nasa.gov/v1/chat/completions -Method Post
   -Headers @{Authorization="Bearer <key>"} -ContentType application/json -Body '{"model":"<id>","messages":[{"role":"user","content":"ping"}],"max_tokens":8}'`.

5. **ANSWERED 2026-09-15 17:05Z by the v1.0.262 screenshot (ADR-0496).** V-4 is on the page: the
   gateway's own reason is *"Authentication Error - Expired Key. Key Expiry time 2026-09-12
   20:36:47.844000+00:00 and current time 2026-09-15 17:05:33.767685+00:00"* — the credential the
   tool sent (the saved key, 25 characters, receipt "replaced") **expired at the AI Hub on
   2026-09-12 20:36:47 UTC**, 2 days 20 hours before the request. A gateway cannot call a key it does
   not recognise *expired*, so the 25 characters reached it intact — the key path is confirmed by
   the server's own answer. The one competing hypothesis (a stale in-memory key after a Save) is
   refuted on the wire (`test_a_key_re_pasted_in_the_same_process_is_the_key_sent_on_both_paths`).
   **Root cause: the key, not the tool. Remedy: generate a NEW key at the NASA AI Hub, paste it,
   Save** — re-pasting the expired key changes nothing, and v1.0.264 says so (OR-19). The
   `/v1/chat/completions` request in §4 is no longer needed; the 09-11 `"ok": false` lines still are.
6. **CLOSED by the operator, 2026-09-15:** *"I fixed the AI. The API code was expired so I made a new one and it
   seems to work now."* A new Hub key answers — the whole of OR-17 is settled: the tool's part (ADR-0493 /
   ADR-0496) and the key's part (the Hub's expiry).

**The registration as written at the close of the previous session (2026-09-15, before the above):**


**What the operator's screen shows (the settings page, no schedule content):** Backend "Approved AI
gateway"; endpoint `https://proxy.fast.luna.nasa.gov` with the approval box checked; the Gateway API
key field reads "(a key is saved — leave blank to keep it)"; the red panel reads "Approved-gateway AI
is OFF — could not reach https://proxy.fast.luna.nasa.gov: server returned HTTP 401. The gateway
answered but requires authentication: paste your organization-issued key … If a saved key still gets
this, the key may be expired or not yet entitled to this gateway"; the Model row reads
"qwen2.5:7b-instruct — not installed · not reachable: server returned HTTP 401"; "Active backend:
null · installed models: null". The page ALSO shows the Ollama endpoint, the OpenAI-compatible
endpoint and the LM Studio token field at the same time as the gateway fields — ADR-0488 said AI
Settings shows one backend at a time, so either the installed build predates v1.0.257 or the
one-backend rule regressed; **the installed version is UNVERIFIED (the banner is not in the
screenshot) — establish it first.** The banner quotes no gateway reason of its own (ADR-0488's
"quotes the gateway's own refusal reason" — either absent from the response, or the build predates it).

**The operator says the same key that used to work no longer does.** Nothing here proves the key is
wrong: the key store's Windows DPAPI branch is UNVERIFIED (carried in every handoff since ADR-0488),
so a saved key that does not round-trip on Windows (empty or garbled after decryption) would produce
exactly this 401 with "a key is saved" in the field. That is the first hypothesis to refute or
confirm, before the header shape (`Authorization: Bearer …` versus what the gateway expects) and
before the catalog probe (`GET /v1/models` answering 401 while generation would not).

**The directive (the operator's, verbatim intent):** root cause first; tests that FAIL on the
defect and PASS on the fix; the fix tested in a sandbox (a loopback fake of the gateway that answers
401 with and without a body / `WWW-Authenticate`, and a fake of the Windows key store) before it is
implemented; iterate until it is fixed. The LM Studio token field: explain it in one sentence on the
page or hide it unless the OpenAI-compatible backend is selected — it is the "Require Authentication"
token of a LOCAL LM Studio server (ADR-0485), sent only to the loopback endpoint, and has nothing to
do with the gateway. V-4 (the gateway's own reason, via the step-2 PowerShell) remains the one
measurement only the operator can make; ask for it again, but do not wait on it to start.

### OR-16 — "I can't log into Opus 4.8 Thinking even if I put in the API Gateway Key." · `SHIPPED IN PART (ADR-0488, v1.0.257): the diagnostics; the simplification is OR-16b, OPEN`

**The operator's evidence (2026-09-12):** AI Settings on v1.0.256 — Backend = Approved AI gateway,
the key field's placeholder *"a key is saved"*, the banner *"could not reach
https://proxy.fast.luna.nasa.gov : server returned HTTP 401. The gateway answered but requires
authentication: paste your organization-issued key …"*, and the Model dropdown showing
`qwen2.5:7b-instruct — not installed` (the catalog never loaded, so the gateway model could not be
picked — the "can't log into Opus" of the report). Then, at this session's request, PowerShell on
the NASA machine with the same key, outside the tool:
`Invoke-WebRequest https://proxy.fast.luna.nasa.gov/v1/models -Headers @{Authorization="Bearer …"}`
→ **HTTP 401** (the masked paste read 25 characters).

**ROOT CAUSE, measured:** **the gateway refuses the key itself.** The tool's key path — form →
session → DPAPI store → reload → `Authorization: Bearer` on `GET /v1/models` — is unchanged between
v1.0.254 (which answered the operator on 2026-09-11 21:44–21:58Z) and v1.0.256 (diffed), and on the
real code a saved key comes back byte-identical and rides the probe (an executable check plus the 32
existing gateway / store tests). A key the gateway accepted at 21:58Z on 09-11 and refuses on 09-12
has expired, been rotated, or is not the key being pasted. **What the tool got WRONG:** the banner
threw the gateway's own reason away (the response body and the RFC 6750 `WWW-Authenticate`
challenge) and said only "HTTP 401"; it could not say WHICH credential it had sent; "paste your key"
is the wrong advice when a key IS saved; and it detected the refusal by substring (ADR-0485's
residual).

**SHIPPED (ADR-0488, v1.0.257):** `ai/refusal.py` — the server's own one-line reason, bounded,
quoted in every probe / generation refusal for every backend (`server returned HTTP 401 (its reason:
"…")`), the response body read once and shared with the answer-length fallback; the gateway banner
names the credential sent — *the saved key* or *SF_GATEWAY_API_KEY* — with its character count
(never its characters, ADR-0403) and sends the operator for the CURRENT key from the Hub; the key
field's placeholder states the saved key's length so a cut paste is visible; the refusal is
word-bounded.

**What to do on the deployed machine:** install v1.0.257 and open AI Settings — the banner now
quotes the gateway's reason and the length of the key it sent. Compare that length with the key the
AI Hub shows; if the Hub's key has expired or rotated, paste the current one and Save. **PENDING
OPERATOR VERIFICATION (V-4):** the gateway's reason text — the step-2 PowerShell (the
`WWW-Authenticate` header and the 401 body) was requested and had not arrived when this shipped.

### OR-16b — "I want the AI setup to be as user friendly and simple as possible." · `SHIPPED (ADR-0488 decision 4, v1.0.257 — this status line was stale until 2026-09-15; the disclosure is JavaScript-driven, so a build before v1.0.257 or a page without JavaScript still shows every backend's rows)`

The page renders every backend's rows at once — two look-alike masked secret fields one above the
other (the *Local server API token* directly above the *Gateway API key*), Ollama's endpoint,
context window and runtime note under a gateway session, an Ollama default model under the gateway
backend when its catalog probe fails. The unit: show only the selected backend's fields
(progressive disclosure in `settings.js`, every field still posted; no-JS renders everything), the
Ollama runtime note only under Ollama, no local default model presented for the gateway, and a
*Test connection* verdict inline. What "simple" will NOT mean: removing the classification, the
approval acknowledgment, or the loopback locks — Law 1 stays.

## 2026-09-11 (b) — the Ask panel's answers stop mid-sentence, then come back empty (two pastes + the settings screenshot; the backend is the approved gateway)

### OR-15 — "I want you to do option 3 and I want you to raise the limit to the max." · `SHIPPED (ADR-0486, v1.0.256)`

**The operator's evidence (2026-09-11):** two answers from `claude-opus-4.8-thinking-itar` via the
approved gateway that stop mid-sentence (*"…an SPI of"*, *"…62 workdays behind"*), then a
one-sentence-longer question that produced *"The local model ran but returned no text … select a
different model in AI Settings."*; AI answer mode = Unrestricted.

**ROOT CAUSE, measured on the code:** neither OpenAI-compatible backend sent `max_tokens` (the
server's default output budget governed, and a thinking model spends it reasoning before it writes);
neither read `finish_reason` (a `length` stop rendered as a complete answer); neither read the
reasoning fields (an empty answer could not say why); and a `null` content became the literal word
"None". The tool's timeout was refuted (it reports a timeout by name); a cut paste was refuted (twice
the same shape, then an empty third).

**CLOSED by ADR-0486 (v1.0.256):** an **Answer length limit** field in AI Settings — bounded
256–131,072, **default = the maximum** (the directive), 0 = server default — sent as `max_tokens` on
every generation to an OpenAI-compatible server or the gateway. "The max" is not a number: a server
that REJECTS the value (HTTP 400 naming it) gets the request once more without it and the answer says
the server's own default cut it and to lower the setting. A `length` stop is disclosed beside the
answer; an empty answer says the budget was spent thinking (with the characters of reasoning, when
the server exposes them) and names the smaller-prompt remedy (Annotate); `null` is empty, never
"None"; a gateway 403 with a valid key names entitlement and prompt size instead of "paste your key".

**What to do on the deployed machine:** install v1.0.256 and ask again — the setting is already at
the maximum. If the answer still stops, the panel now says which of three things happened (the
server rejected the limit → lower it; the budget was spent thinking → Annotate mode or a
non-thinking model; a clean stop → the answer was complete). **PENDING OPERATOR VERIFICATION:** the
gateway model's real output ceiling (UNVERIFIED — the fallback is designed so the tool need not know
it) and whether the gateway exposes reasoning fields at all.

## 2026-09-11 — Ask-the-AI on `/integrity`: "server returned HTTP 403" from the local OpenAI-compatible server (screenshot)

### OR-14 — "do a deep dive and figure out why the ASK the AI is not working the way it should and fix it." · `SHIPPED (ADR-0485, v1.0.255)`

**The operator's screenshot (2026-09-11):** backend = OpenAI-compatible (LM Studio on
`http://127.0.0.1:1234`), a manipulation question in the box, and the note *"the model server at
http://127.0.0.1:1234 was reachable, but the generation itself failed: server returned HTTP 403. AI
Settings shows its live status."* over the raw cited facts.

**ROOT CAUSE, measured on the code and reproduced on the wire before the fix:** the server answers
`GET /v1/models` (so the backend routes and AI Settings reads ON) and refuses
`POST /v1/chat/completions` with 403 — the shape of an LM Studio whose *Require Authentication*
is on (LM Studio 0.4+ can demand `Authorization: Bearer <token>`). **The tool sent no credential
and had NO WAY to send one for this backend:** no `AIConfig` field, no form field, no constructor
parameter, no header slot in its 3-arg opener. The only 401/403 diagnostic in the tree belonged to
the approved gateway (ADR-0403) — the same defect class, closed for the remote backend a month ago
and left open for the local one. Three other hypotheses (a corporate proxy — refuted, the client
already bypasses every proxy; a wrong model id — a 404/400 shape, not a 403; the Ollama path — not
involved) died first.

**CLOSED by ADR-0485 (v1.0.255):** a **Local server API token** field in AI Settings (masked,
never echoed, blank keeps, persisted with the same DPAPI / 0600 protector as the gateway key,
forgotten by Turn-the-AI-off and a wipe), sent as the Bearer header on EVERY request to the
loopback server (probe, catalog, generation; the cross-check second model and the live model
dropdown included) and on nothing else; an empty token sends no header. The Ask note and the
settings hint now NAME the field on a 401/403 — and state, honestly, that if authentication is off
the refusal came from the server or from something in front of it (check the server's log), because
the tool cannot see which. A gateway generation failure is also no longer mislabelled with the
local server's address.

**What to do on the deployed machine:** LM Studio → Developer → Server Settings → *Require
Authentication* → *Manage Tokens*; paste the token into **Local server API token** in AI Settings →
Save → ask again. **PENDING OPERATOR VERIFICATION:** LM Studio's exact refusal code (401 vs 403)
and whether its `/v1/models` is exempt are UNVERIFIED (the docs do not say; the fix accepts both
codes and both catalog shapes). If the 403 persists WITH a token saved, the token is wrong/revoked
or something on the machine sits in front of the server — the note says so.

**CORRECTED the same day (ADR-0486).** The operator's AI Settings screenshot shows the backend is
the **approved gateway** (`https://proxy.fast.luna.nasa.gov`, `claude-opus-4.8-thinking-itar`, key
saved, Unrestricted mode), and their PowerShell against `http://127.0.0.1:1234` reads *"Unable to
connect to the remote server"* — **nothing listens on port 1234; LM Studio is not in play.** The
morning note said `127.0.0.1:1234` because v1.0.254 printed the OpenAI endpoint for EVERY non-Ollama
backend — the mislabel ADR-0485 fixed, and the misdirection it did not re-read. **The 403 was the
gateway's**, on the chat completion, with a key the catalog accepts. The LM Studio token stands as a
real capability gap closed for LM Studio users; it was not this operator's fix. **PENDING OPERATOR
EVIDENCE (still open):** the tail of `ai-transactions.jsonl` (no schedule content — a SHA-256 and a
byte count per prompt) to see whether the 403s correlate with `prompt_bytes` (Unrestricted mode ships
the per-activity table) or were the gateway's own. v1.0.256's note for a gateway 403 with a valid key
now names both causes and the log.

## 2026-09-08 — Ask-the-AI returned no answer on `/integrity` (screenshot, 32-version workbook)

### OR-13 — "I still can't open the program when I close the browser without quitting" · `SHIPPED (ADR-0483, v1.0.253)`

**The operator's report (2026-09-10), after ADR-0482 shipped.** Closing the browser without
*Wipe and Quit* still leaves the tool unopenable. **ADR-0482 is not the culprit and is not
wrong** — a real-Chromium test on a clean single cycle measures the beacon leaving the browser,
passing the CSRF gate, and the server stopping **5 s** after the close. The defect is one layer
further down, in the EXIT.

**ROOT CAUSE, verified against the installed API rather than from memory:**

```
uvicorn 0.52.4 — Config(..., timeout_graceful_shutdown: int | None = None)
web/app.py serve(): uvicorn.Config(app, host=host, port=port, log_level=log_level)   # never set
```

`None` means **wait forever**. So: the watchdog fires correctly, `_trigger_shutdown` sets
`should_exit`, uvicorn begins a GRACEFUL shutdown — and then blocks indefinitely waiting for a
connection that will never drain. The operator's live repro showed exactly that socket:

```
LocalPort RemotePort    State OwningProcess
     8321      54055 FinWait2         16876      <-- half-closed; the browser is gone
     8321          0   Listen         16876      <-- and it is STILL serving
```

**This explains the whole arc, including the pre-ADR-0482 behaviour**: the 600 s idle rule never
worked either (a server survived 8:35 PM → next day, ~18 h), the process keeps answering
`/api/whoami` while "shutting down", the port stays held, and the desktop icon then has to rely on
ADR-0334's handover — which under `pythonw` fails INVISIBLY if it times out. **The bug was never
in the detection. It is in the exit.**

**Four theories died on measurement before this one survived** — the CSRF gate refusing the
beacon (refuted: real Chromium, `POST /api/closing` sent and accepted, server stopped in 5 s), an
Ollama-manager hang (refuted: the server still answers, so it never left `serve()`), the
`browser_seen` gate (refuted: the operator had used the app), and a surviving tab holding the
fuse open (refuted: every browser window closed, 20 s, still alive).

**Proposed fix, NOT yet built and NOT yet proven:** pass a bounded `timeout_graceful_shutdown` to
`uvicorn.Config`. The value looks safe to keep short because `active_requests > 0` already blocks
the watchdog from requesting a stop while real work is in flight — so by the time `should_exit` is
set there should be no legitimate long request to cut off. **That reasoning is exactly the kind
that has been wrong four times today; it needs a red-first reproduction (a half-closed socket that
makes the current build hang, going green with the timeout) before a line is written.**

**Immediate operator workaround, measured:** `POST http://127.0.0.1:8321/api/shutdown` stops a
stuck instance (both processes exited within 4 s). The desktop icon's handover also replaces a
stuck predecessor, so the operator is not hard-blocked.

**CLOSED by ADR-0483 (v1.0.253).** `SHUTDOWN_DRAIN_TIMEOUT = 5` is passed to `uvicorn.Config`, and
the bound comes from `launcher._HANDOVER_TIMEOUT` (20 s) rather than from taste: `CLOSE_GRACE 5 +
watchdog poll 2 + drain 5 = ~12 s` measured, ~8 s of margin, with the **arithmetic** pinned by a
test so raising any of the three re-opens the question.

**The demand for a red-first repro paid for itself twice.**

1. **Five plausible shapes did not reproduce** — idle keep-alive, half-closed after a small
   response, unread small response, truncated request, truncated POST — all stopped cleanly in
   ~6 s. The mechanism is narrower than "a half-closed socket": the peer must stop draining a
   **large in-flight write**. Wedged that way, the current build gives `exited=False`,
   `listening=False`, **`port_rebindable=False`** — the operator's sentence as a measurement.
2. **The safety argument recorded above is FALSE.** `active_requests > 0` does not protect a
   streaming response: Starlette's middleware decrements on *dispatch return*, before the body is
   written, so the watchdog fires with megabytes still queued. The fix is the same one line; the
   justification for it is not the one written here, and the code comments now say so.

**One correction to the evidence reading above.** The `Listen` row cannot show the process "STILL
serving" *during* the hang — `Server.shutdown` closes the listener before it waits, and in every
reproduction the listener is closed while the process hangs. That capture was taken before the fuse
burned. A second failure mode in which the watchdog never fires at all was hypothesised and
searched for; the truncated-POST shape refutes it. The observation was real, that one inference
from it was wrong, and the diagnosis was right regardless.

### OR-11 — "Figure out what the root problem is and then create tests, both pass and fail, and test your proposed solution in a sandbox environment prior to implementing the fix" · `SHIPPED (ADR-0478, PR #655, v1.0.248)`

The question asked (verbatim intent): compare all 32 versions two data dates at a time, oldest
forward; say whether there are signs of an intentional effort to keep **UID 152** from slipping
right; give the evidence; deliver it as a ~10-minute speech for senior management; **and compute
the driving path for UID 152 for each version** (the tasks are not marked critical in the parent
files). The panel answered *"No local model is active (or strict mode discarded its answer)"* while
AI Settings showed a configured model.

**Root problem (measured, not inferred):** `/api/ask` was not self-diagnosing. Five materially
different failures — nothing routed · the generation REFUSED (an Ollama that is up but has not
pulled the selected model answers HTTP 404) · a timeout · an empty completion · a strict-mode
discard — all returned a byte-identical payload with no key distinguishing them, so one hard-coded
`ask.js` sentence covered all five. It led with the cause the operator can see is false, and offered
a strict-mode discard in ANNOTATE mode (the default), where a discard is impossible. Closed by
ADR-0478: `no_answer: {code, text}` on the payload, composed from the operator's own configuration,
rendered by the panel.

### 🔎 WHAT OR-11 DID **NOT** ANSWER — the operator's question still needs these

| # | Open item | Why it blocks the ask | Status |
|---|---|---|---|
| OR-11a | **Per-version driving path.** ~~`ask_workbook` adds `driving_path_facts(schedules[-1], cpms[-1], text)` — the newest version only.~~ | Measured 1 of 32 before, **32 of 32** after, on BOTH surfaces (`/api/ask` and an unscoped `/api/driving-path`), 0.2 s / 0.1 s. Two pinned facts: the per-version series and the movement census. | `SHIPPED (ADR-0479, v1.0.249)` |
| OR-11b | **The evidence cap.** `qa._MODEL_MAX_FACTS = 48` (pinned population facts survive it; the rest are ranked by question overlap). | UNVERIFIED how many facts a 32-version workbook produces, so it is not yet known how much of the 31-pair comparison series is dropped before the model sees it. Measure before changing anything. | `OPEN (measure first)` |
| OR-11c | **The model's own context window.** ~~`OllamaBackend.generate` sends no `num_ctx`.~~ Resolved from primary sources: `/api/generate` returns `prompt_eval_count`; ollama's defaults are VRAM-tiered and moved in v0.15.5 (ollama/ollama#14073). | An answer formed on a truncated prompt now carries `evidence_warning` beside it, measured from the server's own count — never guessed, and the window is never auto-raised. | `SHIPPED (ADR-0480, v1.0.250)` |
| OR-11e | ~~**Send `num_ctx` on the operator's say-so.**~~ ADR-0480 measured truncation and named a remedy the tool could not perform. | Shipped OFF by default (`num_ctx=0` omits the key — byte-for-byte the old request), clamped at all three entry points into `[2048, 262144]`, ceiling = Ollama's OWN `>= 48 GiB` tier default. The form states the mechanism, the `OLLAMA_NUM_PARALLEL` multiplier, the tier defaults and the #14073 incident **attributed** — and no GB-per-token figure, which the tool cannot know. What the server does on receipt stays **UNVERIFIED** and is claimed nowhere. | `SHIPPED (ADR-0481, v1.0.251)` |
| OR-11d | **An unanswered ask exports without its reason.** `_AskRecord` still stores only `answer=None`, so the Q&A Excel/Word export of a failed ask says nothing about why. | Cosmetic next to the above, but it re-creates the same "no diagnosis" gap in the exhibit. | `OPEN` |

### ⏳ PENDING OPERATOR VERIFICATION (the "what we still have left to verify" list)

| # | What to verify | How | Outcome recorded where |
|---|---|---|---|
| V-1 | **v1.0.205 (or later) arm-once flow on the NASA machine**: reinstall, arm once (endpoint + acknowledgment + key + model), quit, then a plain double-click launch must come up ARMED with the model catalog populated | Desktop icon → AI Settings shows "Approved-gateway AI is ON" without any re-entry | Tell the session; HANDOFF "Next" clears its first item |
| V-2 | **The gateway accepts the Bearer key** (`Authorization: Bearer <AI-Hub key>`) | Same check as V-1 — the catalog populating IS the proof; still-401-with-key means the AI Hub uses a different scheme: capture their documented auth header (name/format, never the key value) | A follow-on ADR implements the real scheme on evidence |
| V-4 | **The gateway's own reason for refusing the saved key** (OR-16): the v1.0.257 banner quotes it; the step-2 PowerShell (`WWW-Authenticate` + the 401 body) says the same | Open AI Settings on v1.0.257 with the refused key saved; paste the banner's quoted reason (never the key) | If it names expiry / rotation: a fresh Hub key closes OR-16; if it names the scheme: a follow-on ADR implements the real one |
| V-3 | **The AI transaction log records real gateway use** | After a few questions: `Get-Content "$env:USERPROFILE\.local\state\schedule-forensics\ai-transactions.jsonl" -Tail 20` shows `generate.sent/done` lines | Spot-check only; no session action needed if present |

### 🔒 BLOCKED ON OPERATOR (not verifiable or executable by an agent)

- **DISC-01 release determination** (authorizing official): gateway hostname + ITAR model id are in
  public git history; history-rewrite vs accept-as-is is not an engineering commit.
- **PO-04/05 primary oracle**: an operator-delivered CEI/HMI vendor reference export.
- **8 stale remote branches (DoD 091) + SMAT-SANDBOX branch names**: sessions cannot push ref
  deletions (proxy 403s them, measured ADR-0401) — GitHub UI cleanup.

### 🤖 AGENT QUEUE (no operator input needed; worked in this order)

1. ~~DOC-01 FINAL-REPORT overclaims + JCL docs follow-ups~~ — `SHIPPED (ADR-0405, PR #593 MERGED, v1.0.205)`.
2. ~~TEST-01 chromium build-number unpinning (22 modules; audit xfail flipped)~~ — `SHIPPED (ADR-0406, PR #593 MERGED)`.
3. ~~ENG-DEAD-01 `actual_start_driven` disclosure wiring (INFO finding + grid column + dictionary)~~ —
   `SHIPPED (ADR-0407, v1.0.206; its own draft PR — #593 merged before this unit pushed)`.
4. ~~JCL-BR-01 session branches fed SSI but not `compute_jcl`~~ — `SHIPPED (ADR-0408, v1.0.207;
   carried through with byte-identical marginals, both web call sites; the last strict xfail
   flipped — the repo is now xfail-FREE)`. **THE QUEUE IS EMPTY** — a new audit sweep or a new
   operator directive opens the next arc.

## How to work this queue

- Pick items up in a numbered round like any other tail work; record the ADR that closes each.
- An item here is **not** a licence to widen an in-flight round's scope — round 11 was mid-flight when
  these arrived and correctly did not absorb them.

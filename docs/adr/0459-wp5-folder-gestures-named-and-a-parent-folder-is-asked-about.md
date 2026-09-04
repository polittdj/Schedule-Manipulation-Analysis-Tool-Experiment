# ADR-0459 — WP5: the three folder gestures are named on the dashboard, and a parent folder that holds several project folders is ASKED about, never guessed

- **Status:** Accepted — 2026-09-04 (POLARIS² campaign WP5; the operator chose BOTH builds on 2026-08-27, closing #611's standing ask)
- **Version:** 1.0.235
- **Extends:** ADR-0437 (dropped folders traverse; each dropped folder is its own Project), ADR-0258 (a folder is one Project by the operator's rule — no guessing), ADR-0289 (bounded pre-read of File-likes), ADR-0439 (operator content is data, never markup)
- **Shipped:** `web/app.py` (the dropzone copy, the `.dz-how` legend, the hidden `#dzAsk` shell), `static/home.js` (`fileLike` hoisted, `subfolderPlan`, `reroot`, `askSubfolders`, `ingest`), `static/base.css` (`.dz-how`, `.dz-ask*` — tokens only), `tests/web/test_folder_ask.py` (6, NEW), `tests/web/test_folder_ask_browser.py` (7, NEW)

## Context

The operator's 2026-08-21 ask — *select multiple folders at one time and have the program group the
files in each folder into a separate project* — was settled by measurement that day (SESSION-LOG
2026-08-21 (b)) into three facts that this build takes as given and does **not** re-derive:

1. the folder-picker DIALOG cannot multi-select — `webkitdirectory` overrides `multiple`
   (Chromium's file-chooser modes are exclusive, WICG entries-api #24);
2. DROPPING several folders at once WORKS — each dropped folder lands as its own Project
   (ADR-0437, proven with real Chrome entries via CDP `Input.dispatchDragEvent`);
3. Ctrl/Shift multi-select of FILES already works through *choose files…*.

Two candidate builds were offered and deliberately not built until the operator chose; on
2026-08-27 they chose **both**: (A) clearer labels, and (B) a parent-folder pick that asks *"one
Project, or one per sub-folder?"* — with the standing rule that the tool **asks, never guesses**,
because year sub-folders (`Project/2024/x.mpp`, `Project/2025/y.mpp`) are legitimately ONE Project
with versions while sibling program folders (`Programs/Apollo/…`, `Programs/Artemis/…`) are one
Project EACH, and the paths alone can never say which.

**Measured baseline before a line changed.** The server groups every uploaded file by the FIRST
segment of the client's companion `rel` path (`_parse_upload_meta` → `group_into_projects`), so a
parent-folder pick landed as ONE Project named after the parent with every schedule a version
(pinned as the fact that makes the question necessary:
`test_server_groups_a_parent_folder_pick_as_one_project`). The dropzone copy already carried
ADR-0437's contract sentence, but the folder button said *choose a folder…* as if the dialog
could take several, and nothing on the page said Ctrl/Shift on files works today.

## Decisions

1. **Build A — the three gestures are stated where the operator reads how to load.** The folder
   button reads *choose one folder…* (what the dialog can do), and a `.dz-how` legend names each
   gesture in the operator's terms: *Several files* (Ctrl-click / ⌘-click / Shift-click; loose
   files group by document Title) · *One folder* (the dialog takes one folder per pick) · *Several
   Projects at once* (select the folders together in File Explorer / Finder and drop them; each
   becomes its own Project; picking one parent folder that holds several project folders asks
   you how to load it). Both buttons carry the same facts as hover hints. The two phrases the
   2026-08-21 build pinned — *each folder is its own Project*, *drop several folders at once* —
   survive verbatim; `#pickBtn` / `#pickFolderBtn` keep their ids (home.js and the launch-audio
   drivers bind them).
2. **Build B — the question is asked exactly when the gesture is ambiguous, on BOTH gestures.**
   `ingest()` is the single funnel every way in passes through (picked files, the picked folder,
   a drop's traversal, its `dataTransfer.files` fallback). `subfolderPlan()` returns a plan only
   when **one folder root**'s schedule files span **two or more immediate sub-folders**; it
   returns `null` — and the upload proceeds exactly as before — for a loose file in the gesture
   (not a folder gesture), for several roots (each is already its own Project, ADR-0437's
   contract byte-for-byte), and for a root with at most one schedule-bearing sub-folder (ADR-0437:
   the folder is one Project). Files the server would ignore anyway (no schedule extension,
   read from the file input's own `accept` list, which equals `supported_extensions()`) never
   count toward the plan.
3. **The per-sub-folder answer changes only the companion paths; the server is untouched.**
   `reroot()` wraps each file with three or more path segments in a `preread()`-shaped File-like
   whose `webkitRelativePath` drops the parent segment (`Programs/Apollo/a1.xml` → `Apollo/a1.xml`),
   so the unchanged server groups the sub-folders apart; a two-segment rel (`Programs/top.xml`)
   is left alone, so a schedule directly under the parent keeps the parent as its Project either
   way — and the question SAYS so (`#dzAskNote`). `fileLike` is hoisted out of `walkEntries` and
   shared; `preread()` itself is byte-stable (the ADR-0289 harness window is untouched).
4. **The question is a server-rendered, hidden `role=dialog` shell filled with `textContent`.**
   Title (*“Programs” holds schedules in 2 sub-folders (and 1 schedule directly inside it). How
   should they load?*), the sub-folders BY NAME with their schedule counts (the FileList arrives
   in filesystem-traversal order, which differs machine to machine — Artemis came first on the
   build box), the never-guess rule in one sentence, then three controls: *N Projects, one per
   sub-folder* (focused, so a keyboard user lands on a real choice) · *One Project “Programs” — N
   versions* · *Cancel* (also Escape), which clears both inputs so the same folder can be picked
   again. Folder names are operator content (ADR-0439), so the shell is built with
   `createElement`/`textContent` — `home.js` still has exactly ONE `innerHTML` sink, the
   pre-existing notice. The buttons do **not** prime the launch hum: the gesture that produced the
   question already did (`test_launch_sequence` pins the prime count at exactly four).
5. **The ask's ids and classes live outside every control-census family word.** The sitewide
   control-effect census (M1) recognises steppers by `zoom|fit|pan|entire|play|prev|next|step|
   cf-btn` in id+class; `dzAskSplit` / `dzAskOne` / `dzAskCancel` / `dz-ask*` / `dz-how` match none,
   asserted with the census module's OWN regex (`test_ask_controls_stay_outside_the_control_census_families`),
   so the `/` census row is unchanged by construction and a stepper-shaped rename would be red.
6. **Deliberately NOT done:** no picker-dialog workaround (fact 1 is the platform's); no
   server-side heuristic (ADR-0258's no-guessing rule); no question for a multi-root drop (each
   root is already its own Project — a cascade of questions would be a new behaviour); no question
   for a root with a single sub-folder; no i18n catalog entries for the new strings (the AI
   fallback translates them, exactly as ADR-0451/0456's panel titles).

## Verification (QC-1)

- **Red first, on the pristine tree (2026-09-04):** `test_folder_ask.py` 3 failed / 3 passed — the
  three build pins red by name, the census-naming pin and the two server-fact pins green (they
  pin behaviour that pre-dates the build and MUST stay true); `test_folder_ask_browser.py` 7
  failed — the ask never appeared and the parent pick uploaded as ONE Project.
- **Green:** 6 + 7 new tests; the existing drop module (ADR-0437), `test_home_shell`,
  `test_multi_folder_ingestion`, `test_launch_sequence`, `test_landing`, `test_header_and_loading`,
  `test_preread_concurrency`, `test_i18n`, `test_accessibility`, `test_r11_panel_contract`,
  `test_responsive` (94 passed); the M1 census `/` row and route-table guard.
- **The picker path is driven with REAL platform objects:** Playwright 1.62's `set_input_files`
  accepts a directory for a `webkitdirectory` input and the FileList carried genuine
  `webkitRelativePath` values (`Programs/Apollo/2024/a2.xml`, …) — measured before the test was
  written. The drop path reuses ADR-0437's fake-entry machinery for one root vs two.
- **Mutation, on scratch copies of the FINAL code (never `git checkout --`), each red by name:**
  `reroot` → no-op ⇒ the per-sub-folder pick and the single-root drop land ONE Project (2 red) ·
  `subfolderPlan` → always `null` ⇒ the five ask scenarios red, the two never-ask scenarios green ·
  threshold `< 2` → `< 1` ⇒ the one-sub-folder folder asks and never loads (1 red) · the sort
  removed ⇒ the list order pin red. `home.js` byte-identical to the pre-battery copy afterwards.
- **Render, four themes, 1440 px:** the dropzone panel with the question open in console, daylight,
  apollo and jarvis — zero page errors, nothing wider than the viewport (widest = the full-bleed
  CUI banner), focus on the per-sub-folder button; all four PNGs viewed.

## Consequences

- An operator whose programs live side by side under one parent can load them as separate
  Projects with the dialog they already use — one pick, one honest question — and an operator
  whose sub-folders are years is asked the same question and keeps one Project.
- The multi-folder DROP (ADR-0437) is unchanged in behaviour and re-proven green; a single dropped
  parent folder now gets the same question as a pick.
- The `.dz-how` legend adds ~110 px to the dropzone on a 1440 px viewport (measured); the
  `/` census row's floors are unchanged.
- Version 1.0.234 → 1.0.235; wheel + nine installers rebuilt in lockstep as the LAST step.

# ADR-0208 — Mission Ops redesign step 3 (page shell): chapter 10 "What changed"

## Status
Accepted. Tenth page shell of step 3, applying the template to chapter 10 "What changed" =
Compare at `GET /compare`. Presentation only; every figure is read from the UniqueID-matched
version diff (`diff_versions`) plus the two CPM finishes the page already has.

## Decisions
- **`_what_changed_header(prior, current, prior_cpm, current_cpm)`** compares the two latest
  solvable versions:
  - **Takeaway h1** — "`Between the two versions, C activities changed, A added and D removed, with
    L logic links added and R removed; the finish moved out X days.`" ("the two versions are
    identical" when nothing changed).
  - **6-KPI strip** — Activities changed · Added · Removed · Logic added · Logic removed · Finish
    move.
  - **Two composition bars** (`_status_stack`): **Activity changes** (Added / Changed / Removed /
    Unchanged over the newer version's total) and **Logic changes** (Links added vs removed).
- Data from `VersionDiff` (added/deleted/changed tasks, added/removed links) + `offset_to_datetime`
  on the two CPM finishes. No new math.

## Consequences
- Compare reads as chapter 10. Chromium-verified console + daylight, zero console errors ("106
  activities changed, 0 added and 0 removed, 3 logic links added and 2 removed; the finish moved
  out 148 days" — the golden P2→P5 slip). Part of the bundled 08-12 PR.

# ADR-0023: Professional file-first landing + JSON open/save

- **Status:** Accepted
- **Date:** 2026-06-09 (post-build enhancement, requested by the operator)
- **Relates to:** §6.A (UX; open/import; in-tool affordances), ADR-0018/0019 (web app + visuals)

## Context
The operator showed a screenshot of the **previous** build's UI (a JSON-editor SPA with
non-functioning "Open .json" / "Import .xml/.xer/.mpp" buttons) and asked for a professional,
working interface. That UI is not in the current code (greenfield removed it); the current
build's landing was a bare upload form. The operator chose a **file-first report dashboard**.

## Decision
1. **Professional landing (`web/app.py home()`)** — a hero + a drag-and-drop **dropzone** with a
   "choose a file…" picker (`accept=".json,.xml,.mspdi,.xer,.mpp,.mpt"`, so *Open .json* **and**
   *Import .xml/.xer/.mpp* are one working control) and a **"Load example"** button. Dropped/
   chosen files POST to the existing `/upload`; the loaded-schedules list gains **Open report** +
   **Save .json** actions. Styled via additions to the shared dark theme (hero, dropzone, buttons).
2. **JSON is a first-class format (`importers/json_schedule.py`)** — `parse_json`/`parse_json_text`
   read a friendly, human-readable schedule (name, project_start, calendars, tasks with working-
   minute durations, top-level or task-level relationships incl. FS/SS/FF/SF + lag), with the
   strict pydantic serialization as a fallback; `to_json_text` writes that friendly format back
   (for **Save .json**), round-tripping. Wired into the loader (`.json`) and `_parse_upload`.
3. **One-click example (`/example`)** — a bundled, non-CUI `web/examples/house_build.json`
   (a 9-activity project with progress, baselines, and logic) loads and opens its full report, so
   a new user sees the tool work immediately without having a file.
4. **Save/Open (`/download/{name}.json`)** — exports the loaded (normalised) schedule as a
   re-openable `.json`. URLs are percent-encoded so schedule names with spaces work.

CUI/quality unchanged: server stays 127.0.0.1-only, no new dependency, the parse happens locally,
egress + air-gap guards stay green.

## Consequences
- The dashboard is professional and the open/import/example/save controls all function. RTM A2/A5
  (UX/help) and B1 (ingestion) are reinforced; `.json` joins `.mpp/.xml/.mspdi/.xer` in
  `supported_extensions`.
- +`importers/json_schedule.py` (92%), new landing/example/download routes (web/app 93%), and
  `tests/importers/test_json_schedule.py` + `tests/web/test_landing.py`. Full suite 469 passing
  (after the M-AUDIT remediation, ADR-0024); parity + egress + air-gap green.

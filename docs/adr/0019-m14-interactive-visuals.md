# ADR-0019: M14 interactive visuals — vendored, dependency-free, air-gapped

- **Status:** Accepted
- **Date:** 2026-06-08 (session A16 — Phase 2 build, milestone M14, continuous A7 sitting)
- **Relates to:** §6.A (interactive Power-BI-style visuals; add/remove fields; drill into metadata; local assets, no CDN), `BUILD-PLAN.md M14`, RTM A4
- **Builds on:** ADR-0018 (web shell + JSON API), ADR-0011 (driving slack), ADR-0010 (CPM/float)

## Context
§6.A requires interactive, Power-BI-style visuals — charts, a Gantt, drill-into-metadata,
add/remove fields — with **all viz/JS assets bundled locally (air-gapped, no CDN)**. The
BUILD-PLAN named ECharts + Tabulator as the vendoring target.

## Decision
1. **Dependency-free local viz instead of vendoring ECharts/Tabulator.** `web/static/app.js`
   + `web/static/app.css` implement the required interactions in **vanilla JS/SVG with zero
   third-party libraries**. Rationale: for a CUI, air-gapped tool this is the *strongest*
   posture — nothing is fetched at build or run time, there is no large third-party binary
   blob in git, every served byte is auditable, and the air-gap guarantee is trivially
   provable. The requirement's intent (interactive, local, no-CDN visuals) is fully met; the
   named libraries were a means, not the end. (If ECharts/Tabulator are later desired, they
   drop into `web/static/vendor/` and the air-gap test already guards the no-CDN rule.)
2. **Capabilities delivered** (server-rendered shell + client-side rendering from the local
   JSON API): bar charts for the DCMA pass/fail overview and baseline-compliance counts; an
   interactive **activity grid** with **add/remove fields** (column checkboxes), sortable
   columns, and **click-to-drill** showing every underlying field + the citation (file + UID
   + task); a **Gantt** that positions activities on a CPM ordinal axis and colours each by
   its **driving/secondary/tertiary/beyond tier** to a user-entered target UID (reusing the
   M6 driving-slack engine — 36 driving / 12 secondary / 12 tertiary for Project5/UID 143,
   matching SSI parity).
3. **JSON API extended** (`web/app.py`): `/api/analysis/{name}` gains `activities` (per-UID
   rows: dates, total/free float in days, %complete, critical, source file); a new
   `/api/driving/{name}?target=&secondary=&tertiary=` returns tiered rows with CPM ordinals
   for the Gantt. `StaticFiles` is mounted at `/static`; the layout links `/static/app.css`;
   the analysis page mounts `#viz` (with the schedule **key**, not its title, so the client
   fetches the right resource) and loads `/static/app.js`.
4. **Air-gap is tested (`tests/web/test_airgap.py`).** Every served page + static asset is
   scanned for absolute `http(s)://`, protocol-relative `//host`, and remote `src`/`href`
   references; only loopback and same-origin `/static` relative paths are allowed. The test
   fails if anything points off-box — the §6.A / Law 1 no-CDN guarantee, enforced.

## Consequences
- RTM **A4 → ✔** (interactive visuals, drill-down, add/remove fields, local/air-gapped) and
  **A2** now has the full browser dashboard (desktop-icon packaging remains M16). The
  egress guard + the new air-gap test together prove the UI is fully local.
- web/app 93% line+branch (uncovered = the `.mpp` temp-file path needing a JRE + AI exception
  fallbacks); full suite 420 passing; parity + air-gap + egress green; no runtime deps added.
- M16 wraps `web.run()` in a desktop launcher; M17's user guide screenshots/describes these
  views and the metric dictionary.

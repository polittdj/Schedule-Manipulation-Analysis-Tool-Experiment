# ADR-0008: M3 MSPDI + XER importers (clean-room, stdlib, fail-loud)

- **Status:** Accepted
- **Date:** 2026-06-05 (session A5 — Phase 2 build, milestone M3)
- **Relates to:** §6.B (ingestion; all metadata; UniqueID-only), §3 (units), §0/§6.G (CUI), §7 (TDD/RTM)
- **Builds on:** ADR-0004 (stack), ADR-0007 (M2 model). Study reference (not copied): prior build
  `0324ba4` (`importers/msp_xml.py`, `importers/xer.py`), enumerated by Explore sub-agents.

## Context
M3 is the first ingestion milestone: parse a hand-authored **MSPDI** (MS Project XML) and a
**Primavera P6 XER** into the M2 `Schedule` model. No native `.mpp` yet (M4 converts `.mpp`→MSPDI via
MPXJ and feeds this same code); no CPM yet (M5). The model is frozen/strict/closed, so importers must
parse source strings into real `datetime`/`int`/enum values and surface any malformed input loudly.

## Decision
1. **Two clean-room importers + shared helpers.** `importers/mspdi.py`, `importers/xer.py`, and
   `importers/_common.py` (error type + deterministic value parsing). Each importer exposes a
   file entry point (`parse_mspdi`/`parse_xer`, sets `source_file` for citations) and a string entry
   point (`parse_mspdi_text`/`parse_xer_text`, for inline tests). Reimplemented from the M2 model and
   the format specs — the prior build was studied for mapping tables only, never copied.
2. **Standard library only (no new deps).** MSPDI via `xml.etree.ElementTree`; XER via tab-delimited
   `%T/%F/%R/%E` line parsing (fields read **by name**, never position). The CUI egress guard stays
   green; honors the HANDOFF directive ("stdlib `xml.etree`/`csv`-style parsing, no new remote deps").
3. **UniqueID is the sole identity.** Tasks/resources keyed by `UID`/`task_id`/`rsrc_id`;
   relationships/assignments reference endpoints by UID only. The model's referential-integrity and
   self-loop validators do the enforcing; a violation is re-raised as `ImporterError`.
4. **Fail loud, never silently drop in-scope data.** Malformed XML/XER, a missing project start, a
   `<Task>` without `<UID>`, a non-integer id, a bad duration/lag, a duplicate UID, a self-loop, or a
   **dangling** relationship all raise `ImporterError`. The one deliberate exception: in a
   *multi-project* XER, a link crossing into a non-selected project is **out of scope** and is
   excluded (the selected project is the one owning the most tasks).
5. **Deterministic units (§3).** Durations/lags convert to integer working minutes via
   `Decimal` + `ROUND_HALF_UP` (no binary-float drift): MSPDI ISO-8601 `PnDTnHnMnS` (working hours in
   the span; ISO `D` = 24 h); XER `*_hr_cnt` hours × 60 (sign preserved → leads). Dates are ISO-8601
   with the pre-1985 "not set" sentinel → `None`.
6. **Mapping tables (MS Project / P6 standard).** MSPDI `ConstraintType` 0-7 → ASAP/ALAP/MSO/MFO/
   SNET/SNLT/FNET/FNLT; MSPDI link `Type` 0-3 → FF/FS/SF/SS; MSPDI `Resource/Type` 0-2 →
   MATERIAL/WORK/COST. XER `cstr_type` (`CS_*`) → constraint; `pred_type` (`PR_*`) → link type;
   `rsrc_type` (`RT_Labor`/`RT_Equip`→WORK, `RT_Mat`→MATERIAL); `task_type`
   (`TT_Mile`/`TT_FinMile`→milestone, `TT_WBS`→summary, `TT_LOE`→LOE). XER WBS is the dotted
   PROJWBS root→leaf path.
7. **Security — untrusted-XML hardening.** Schedule files are external/CUI, so before parsing MSPDI
   the importer **rejects any document carrying a `<!DOCTYPE>` or `<!ENTITY>`** (the precondition for
   XXE and billion-laughs), making the stdlib parser safe on untrusted input. `defusedxml` was
   considered and rejected (the M3 directive is stdlib-only); the DOCTYPE/entity rejection is the
   mitigation. Two minimal, justified `# nosec B405/B314` annotations cover the ET import and parse.

## Source-pending (flagged; validate against a real export at M4/M9 — Law 2, R-11)
- **MSPDI `LinkLag`** is treated as tenths-of-a-minute (value ÷ 10 = working minutes; `LagFormat`
  governs display only). Plausible per the MS Project XML schema but unconfirmed against a real file.
- **XER `cstr_type` set** maps the common codes (incl. `CS_MANDSTART`/`CS_MANDFIN`→MSO/MFO); rarer
  codes default to ASAP.
- **XER `target_start/end_date`→baseline_start/finish** and **% complete from `phys_complete_pct`**
  (physical only when `complete_pct_type==CP_Phys`) are the pragmatic mappings; P6's baseline lives in
  a separate project and full %-complete resolution by `complete_pct_type` is deferred.

## Deferred (carried forward)
- **Calendar parsing** — both importers use the default 8 h/Mon-Fri `Calendar`; MSPDI `<Calendars>`
  and XER `CALENDAR.clndr_data` parsing lands when CPM (M5) needs real working time.
- **XER per-task cost** (TASKRSRC/expense roll-up) and **P6 secondary constraint** (`cstr_type2`).
- **Activity code** (XER `task_code`, e.g. `A1000`) has no model field yet (used as a name fallback);
  a future `activity_code` field would go through the schema-freeze change-control gate.

## Consequences
- Both importers are at **100% line+branch coverage**; 92 importer tests (field-coverage on two
  synthetic, non-CUI fixtures under `tests/fixtures/` + loud-failure edge cases). Full suite 256
  passing, 99.90% overall; ruff/ruff-format/mypy(strict)/bandit clean; egress guard green (no new
  deps). M4's `.mpp`→MSPDI path now has a tested, typed landing zone.
- Synthetic field-coverage proves the *mapping*; **numeric parity** against Acumen/SSI is asserted
  later (M6-M9) once real exports drive the suite. Source-pending items are tracked as R-11.

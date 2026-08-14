# ADR-0399 — The CUI pre-commit guard learns disguise suffixes, anchored renames, and containers

**Status:** Accepted · **Date:** 2026-08-14 · **Closes:** HOOK-01 (audit 2026-08-13, ADR-0395;
remediation plan P4) · **Extends:** ADR-0347 (the guard's first two detectors) · **Supersedes:**
nothing. **No shipped code changed** — `.githooks/` + tests + docs only; version stays v1.0.201,
no wheel/installer rebuild (precedent: ADR-0395).

## Context

The 2026-08-13 audit's HOOK-01 finding, proven with a 19-case scratch-repo battery: the pre-commit
CUI boundary was wider than "no image detector". A schedule renamed to a non-sniffed extension
(`sched.png`, `notes.md`, `chart.svg`) slipped the content detector, whose sniff set was only
`.json`/`.txt`/extension-less; a blocked-extension double-extension (`data.mpp.png`,
`sched.mpp.zip`) double-missed both detectors (the closed backup-suffix set had no disguise
suffixes, and `.png`/`.zip` were not sniffed); and a schedule-bearing PDF or ZIP was covered by
neither `.gitignore` nor the hook. `tests/audit/test_audit_findings.py` carried the finding as an
`xfail(strict=True)` pin on the hook's own `sniff_re`, designed to flip loudly when fixed.

ADR-0347's constraints still bind and shaped everything here: the suffix set stays CLOSED (the
obvious "blocked ext followed by any dot" wedges `tools/mpxj/lib/jakarta.xml.bind-api-3.0.1.jar`,
whose Java package name merely contains `.xml.`), and a guard that fires on prose, config, real
screenshots or report PDFs gets switched off — after which it guards nothing (the remediation
plan names the 120+ tracked PNGs as the false-positive population to protect).

## Decision

`.githooks/pre-commit` now runs THREE detectors; every rule was measured against the tracked tree
before adoption, not assumed.

1. **Extension chain.** `blocked_re` accepts a *chain* of trailing suffixes after a blocked
   extension — the existing closed backup/copy set plus a closed disguise set
   (`png|svg|jpg|jpeg|gif|bmp|webp|pdf|zip|7z|rar|tar|tgz|md|txt|json|log`) — so `data.mpp.png`,
   `sched.mpp.zip`, `export.xer.png` and `data.mpp.png.bak` are blocked by NAME with any bytes.
   Measured: the final chain claims **zero** tracked files beyond the hard-anchored core
   (population 1633; the jar stays unclaimed because `bind-api-3` is in no closed set).
2. **Anchored text rules for prose-capable and image extensions.** `sniff_re` widens to
   `.md/.png/.svg/.jpg/.jpeg/.gif/.bmp/.webp/.pdf/.zip` (satisfying the audit's static pin), but
   for these NEW classes the three ADR-0347 signatures fire only when the staged bytes *start* as
   the serialization (an XER header line, a brace opening the save-JSON, an XML declaration
   carrying the MSPDI namespace, BOM/whitespace tolerated). Measured why anchoring is required:
   `docs/STATE/AUDIT-2026-06-25.md` legitimately contains the save-format signature mid-file — an
   unanchored `.md` sniff would have blocked a tracked doc on day one. `.json`/`.txt`/
   extension-less keep their original UNANCHORED sniff — no behaviour regressed.
3. **Container magic (never name alone).** An OLE2 compound file (the `.mpp`/`.xls`/`.doc`
   family) under ANY sniffed name is blocked; a ZIP under a non-archive name is blocked (no
   sniffed extension is legitimately a zip); a real `.zip` is blocked only when its member list
   names a blocked-extension file (which also catches every renamed OOXML package via
   `[Content_Types].xml`) or a Power BI payload (`DataModel`, `Report/Layout`); a real PDF is
   blocked only when it EMBEDS a blocked-extension attachment (`/EmbeddedFile` plus a filespec
   naming it). Rendered/printed report PDFs and real screenshots carry none of these signals.
   Consistency note: blocking a zip that carries `member.xml` is the same policy that blocks
   `member.xml` staged directly.

Detectors 2b/3 run as ONE embedded python3 batch (this is a Python-3.11 project; every build/CI
machine has it). Without python3, or if the sniffer errors, the hook prints a warning and keeps
detectors 1–2 — never silently, and never below its pre-ADR-0399 floor. Deliberately NOT sniffed:
`.jar`/`.whl` — legitimate zip-based artifacts whose members (e.g. `*.xml` inside every MPXJ jar)
would wedge each vendored-toolchain upgrade and wheel rebuild.

## The guard flagged ITSELF, and the census caught it before the commit did

The first draft of the new hook wrote the save-format signature verbatim in a header comment. The
hook is an extension-less file — one of its own sniff classes — so the whole-tree census test
flagged `.githooks/pre-commit` as schedule content: **the commit landing the fix would have been
wedged by its own guard.** The comment now describes the signatures without quoting any of them,
and warns future editors. This is the audit's redaction lesson ("a document that flags a
disclosure must not repeat the disclosed literal") landing on the guard itself.

## Verification (QC-1)

- **Red first.** A 30-case scratch-repo battery instrument (independent of the committed tests)
  run against the UNFIXED hook: all 15 gap cases ALLOW (the audit's defect reproduced live), all
  7 controls BLOCK, all 8 false-positive guards ALLOW — 30/30 as the audit reported. The same
  instrument with post-fix expectations goes red on exactly the 15 gap rows against the unfixed
  hook, so it can refute the fix claim. Against the fixed hook: **30/30**.
- **Committed battery.** `tests/guards/test_precommit_blocklist.py` gains 16 block cases
  (disguise chains, anchored renames, OLE2/ZIP/PDF containers), 5 allow cases (screenshot PNG,
  tool SVG, prose `.md` quoting the signature, text PDF, innocent zip), a staged-bytes-not-
  working-tree case for the container path, and a python3-absent floor test (classic block still
  fires; the skip WARNS). The audit module's HOOK-01 `xfail(strict)` flipped loudly (XPASS) and
  the marker is removed in this commit — the test stands as the permanent sniff-set pin.
- **Whole-tree census with two controls.** A scratch repo stages every tracked file outside
  `00_REFERENCE_INTAKE/` and the allow-prefixes (population > 900, staged count proven equal to
  the copied population — the audit's `git add -A`-missed-files trap, guarded) plus a planted
  `schedule_canary.png`; the REAL hook must flag exactly the canary and nothing else. This test
  caught the self-flag defect above on its first run.
- **Sweep repointed, with teeth.** The suffix-clause tracked-tree sweep derived its "core" by
  splitting the pattern on a literal tail the chain form no longer has — it would have passed
  VACUOUSLY (the phase-2 trap: a source-text guard staying green when its subject changes shape).
  It now reads the extension alternation itself, and a committed negative control proves the
  any-dot mutant still claims the MPXJ jar over the same population.
- **Mutation battery, by name.** Eight named mutations applied to sandbox COPIES of the hook
  (each diff verified non-inert), run through the independent battery instrument: chain reverted,
  OLE removed, zip-member removed, zip-disguise removed, PDF removed, anchored trio removed,
  anchoring dropped (the naive implementation — must flip the prose-`.md` ALLOW case, proving the
  false-positive side has teeth), sniff set narrowed. **8/8 caught by their named rows** (lead
  re-ran M2 and M7 by hand: M2 flips exactly its three container rows; M7 flips exactly
  `guide.md`, blocked as "P6 XER content" because the unanchored variant matches the quoted
  `ERMHDR` in prose — precisely the false positive the anchoring exists to prevent). Instruments
  (`battery.py`, the real hook, the test module) md5-identical before and after.
- **Adversarial fan-out (ADR-0240) — and it EARNED its cost.** Three attack agents (evasion,
  false-positive, bash robustness; 40 + 37 + 32 executed POC cases) ran against the
  mutation-proven hook and found **five in-scope defect classes**, every one lead-re-verified
  from its POC transcript and **fixed in this same unit**:
  1. *C-quoting fail-open (pre-existing, severity: silent CUI commit).* `git diff --cached
     --name-only` C-quotes any name carrying a non-ASCII/quote/backslash/control byte
     (`core.quotepath` default), the escaped token matches no extension pattern AND
     `git show ":$token"` fails — so a real OLE2 `schädule.mpp`, an XER `xér häder.txt`, an
     extension-less `café` save-JSON all bypassed EVERY detector, on the old hook too. Fixed:
     `-z` + `read -r -d ''` delivers raw bytes end-to-end.
  2. *Trailing-whitespace names (pre-existing).* `sched.mpp ` defeated every end-anchor. Fixed:
     matching runs on a whitespace-stripped copy of the basename; git lookups keep the real name.
  3. *MSPDI quote over-fit (bash AND python).* A single-quoted `xmlns='…'` is XML-spec-valid,
     loads as the identical schedule, and slipped both double-quote-literal signatures. Fixed:
     quote/whitespace-agnostic matching in both.
  4. *False positive: templated `.md`.* Hugo `{{<` / Jekyll `{%` docs start with `{` and were
     blocked when they QUOTED the save format — breaking the header's promise. Fixed: the brace
     must open a JSON object (`{` then a quoted key).
  5. *False positive: PDF paren-string conflation.* The attachment regex matched printed page
     text (`(…see attached schedule.xml) Tj`) in a benign-attachment report PDF. Fixed:
     `ATTACH_RE` binds to a `/F`/`/UF` filespec — which also catches legal spaces inside the
     filespec parens (a variant that previously slipped).
  The battery grew to **42 cases** (the 12 new rows shown red against the pre-fix hook first,
  then 42/42 green), the committed tests grew to match (two hostile-name cases skip on
  Windows, which cannot create those names), and the **8-mutation battery was re-run against
  the FINAL hook: 8/8 caught with the enlarged expected sets** (M2 now also flips
  `plané.json`; M7 flips all three templated-doc rows). Instruments md5-verified unmutated
  after the fan-out.
- **Existing suite.** The full guards/audit/redaction modules pass (136 passed, 2 xfailed —
  TEST-01 and PO-03 remain live by design); full gate at close recorded in SESSION-LOG.

## Deliberately NOT done (documented limits, not defects)

- **Nested archives** (a schedule zipped inside a zip inside a zip), **non-stdlib archive
  bodies** (`.7z`/`.rar`), and **bare `.gz` bodies** are not opened — no decisive std-lib
  signal; the chain clause still catches their names when a blocked extension is visible.
- **The sniff set is CLOSED, like the suffix set.** A schedule renamed to an unsniffed
  extension (`.dat`/`.log`/`.bin`/`.rst`/`.html`/`.yaml`/…, confirmed by the evasion agent)
  is not content-checked: the audit scoped the rename gap to image/doc extensions, and an
  open-ended sniff of every extension re-creates the false-positive exposure one class at a
  time. Widening it further is a deliberate future decision, not drift.
- **Container rules are NAME-based inside the container.** A zip member named `payload`
  carrying XER bytes, or a PDF whose embedded stream is a schedule but whose filespec names no
  blocked extension, is not detected — member/attachment CONTENT is not decompressed and
  sniffed. Likewise an MSPDI hidden behind a leading XML comment defeats the
  serialization-start anchor (a legit SVG can also start with a comment, so the anchor cannot
  be loosened without buying back the prose false positive).
- **A schedule PRINTED into PDF page content** (a rendered Gantt) is not detectable by any
  decisive signature and is a report, not a serialization; blocking on guesses is how a guard
  gets switched off.
- **Session activation is unchanged.** git cannot self-activate hooks; the SessionStart hook
  activates it for build sessions and the header documents `git config core.hooksPath .githooks`
  for everyone else. A clone that never activates it still has `.gitignore` + the intake
  manifest. This residual is the finding's "operator policy" half and stays open by design.
- **`tests/fixtures/` keeps its unconditional allowance** (ADR-0347's position, unchanged), and
  `.gitignore` is untouched (tracked PDFs/PNGs are legitimate; ignoring `*.zip` would not survive
  the first legitimate archive).
- **python3-absent container coverage.** The floor is the pre-ADR-0399 guard plus a loud
  warning; a committing machine without python3 cannot run this Python project anyway.

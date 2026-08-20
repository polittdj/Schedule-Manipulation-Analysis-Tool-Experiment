# ADR-0435 — The installer banner names the version it embeds, and the README explains updating

**Status:** Accepted · **Date:** 2026-08-20 · **Extends:** ADR-0148 (wheel/installer lockstep), ADR-0299 (one-file installers)

## Context

The standing queue's item 1, and — this session established — the probable source of the
operator's "broken timescale" screenshot (ADR-0432): the operator re-ran an `install-tier2.ps1`
already sitting in Downloads and it installed **v1.0.148** from a fully green run, because an
installer EMBEDS its wheel and never consults the repository. Two measured gaps: the banner
printed the tier but not the embedded version, and `installer/README-DISTRIBUTABLE.md` had no
"updating an install you already have" section. Seventy releases of fixes were invisible to an
operator holding an old file.

## Decision

- `build_installers.py` derives the embedded wheel's version from the wheel filename and
  substitutes a new `{{WHEEL_VERSION}}` placeholder; all three templates' banners become
  `Schedule Forensics installer — vX.Y.Z — <tier>` plus the honesty line "This file embeds and
  installs exactly vX.Y.Z. For a newer release, re-download the latest installer — an old file
  reinstalls its old version."
- The guard asserts the **RENDERED** banner, never the template
  (`test_rendered_banner_carries_the_embedded_wheels_version`): for each of the nine generated
  installers it extracts the version FROM THAT FILE's embedded wheel name and requires the same
  file's banner line to carry it — an expectation the file itself supplies, not a transcribed
  number. Observed RED against the committed pre-fix installers before the templates changed.
- `README-DISTRIBUTABLE.md` gains "## Updating an install you already have": re-download the
  latest installer (an old file reinstalls its old embedded version, by design — the install
  works offline), a re-run replaces only the tool and keeps everything else, and the banner is
  how you check which version a file installs. A file whose banner prints no version predates
  v1.0.219 and is old by definition.

## Consequences

- A stale installer now ANNOUNCES itself at the first line of output, and the distribution
  README tells the recipient what to do about it. All nine installers regenerated (v1.0.219).

## Deliberately NOT done

- **No self-update / version check against the repository** — the installers are deliberately
  offline-capable and repo-independent (Law 1 posture); visibility, not connectivity, is the fix.
- The installed APP's own version display is unchanged — it already exists; the gap was the
  installer artifact's self-identification.

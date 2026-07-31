# 0319 — The /resources period labels yield to the MEASURED caption

Date: 2026-07-31
Status: accepted

## Context

Round 10's `defer` made the `/resources` histogram paint on first load — which exposed the
page's caption debt: applying the four-theme visual pass measured a REAL collision in 8 of 12
theme × scale combos. The end-anchored X caption "Period (month commencing)" (drawn by the
shared helper at the frozen `(R, B-4)` corner) was parked over the last 40°-rotated period tick
labels — console@1 by ~36×2 px per label, apollo@1 (IBM Plex Mono, wider glyphs) by ~40×4 px.
Everything else passed. The round-10 lead deliberately did not adjust it (standing requirement
5: the captions are finished — placement never moves), recording it as owed work with the
remedy named: ADR-0303's "data label yields", applied in `resources.js` where the collision is
caused, plus `/resources` joining the visual pass in the same change. PR-5 of the approved
queue (`docs/STATE/PLAN-20260730.md`).

## Decision

A **measured yield**, not a geometric guess: after the SVG is appended (live boxes need
layout), `resources.js` finds the X caption (`text.ch-at[text-anchor=end]`), reads its real
`getBoundingClientRect`, and **removes any rotated period label whose live box comes within
2 px of it**. The caption never moves. Measuring the live boxes — rather than estimating text
metrics — makes the yield correct per theme and scale by construction: apollo's wider mono
caption reserves a wider corner automatically. A zero-width caption box (hidden host) skips
the yield rather than shredding every label. The alternative in the recorded note — thinning
the tick cadence (`step`) — was rejected: it degrades every label to protect one corner.

Freeze bookkeeping, both per their own prescribed paths: the 16-site axis-caption census is
untouched (the yield sits BELOW the call site; recorded line 243 and every digest unchanged),
and the r10 contract's whole-file `resources.js` digest — round 10's "this round touched no
byte" statement — is refreshed deliberately with this ADR named, while its load-bearing pins
(the call-site block digest + the two caption strings) prove the `axisTitles` call itself is
byte-identical.

## Verification

`tests/web/test_axis_titles_visual.py` now walks `/resources` in all 12 theme × scale combos
(PAGES gained the route in the same change, per the file's own protocol note, which now records
the closure instead of the debt): the full pass reads green with the yield in place. Proved
able to fail: with the yield stashed, the pass reports the original collisions ("overlaps
2027-08 by 20x2px", "overlaps 2027-09 by 43x2px", …) and exits 1. The r10 resources contract
(defer pin, first-paint chromium test, caption strings) and the r11 census stay green.

## Consequences

The last measured caption collision on a shipped chart page is closed; the visual pass covers
six pages. A period bucket whose label yielded still carries its full tooltip (period + booked
vs capacity) — the label is presentation, the bar is the data. Future rotated-label charts
should copy the measured-yield idiom rather than reserving fixed corners.

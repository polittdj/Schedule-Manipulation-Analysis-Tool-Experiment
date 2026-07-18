# ADR-0267 — role-selection strip i18n catalog (ROLES-2 completion)

## Status

Accepted. Completes the partial ROLES-2 item (the ADR-0255 role strip shipped with its
headings translatable but the catalog incomplete — the standing queue's last unblocked item).

## Decision

`web/i18n.py` `_TERMS` gains the full role-strip vocabulary ×4 languages (ES/FR/DE/PT),
~46 entries: the picker heading ("Who’s analyzing today?" — keyed with the page's actual
`&rsquo;` character, `noqa`'d for RUF001), the five role labels and their taglines, the five
combined "Start here — {role}" headings (single DOM text nodes, so the combined strings are
the keys), every Start-here card title not already catalogued (Portfolio, Compare, Margin
Dashboard, Schedule Quality Ribbon, Assessment Scorecards, Schedule Integrity, Standards &
Execution Indices, Where we stand (±DCMA-14)), all 24 card why-lines, "Show everything",
and the no-role tooltip blurb (`translate.js` walks `title` attributes, so the pill
tooltips translate too). Product/standard names (IMS, DCMA, SSI, SEM, Fuse, Fig 5-30) stay
untranslated by the catalog's existing convention; the picker's explanatory paragraph
(inline-markup-split text nodes) stays on the AI-fallback layer like other explainer prose.

## Consequences

- Pure catalog data — no route, engine, or markup change; EN rendering byte-identical.
- i18n + roles suites green (the catalog-shape test covers every new entry's four columns).
- Version 1.0.71 → 1.0.72 (shared with ADR-0266); wheel + 9 installers in lockstep.

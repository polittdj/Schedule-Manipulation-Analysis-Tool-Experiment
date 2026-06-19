# ADR-0102 — Expand i18n: French + German, aligned multi-language catalog

Date: 2026-06-19 · Status: accepted · Builds on ADR-0099 (EN/ES display language)

## Context

ADR-0099 shipped the English/Spanish toggle with a per-language catalog dict. The operator asked to
complete the open options, which included **broadening language coverage**. Adding languages with the
original per-language-dict shape risks the catalogs drifting out of alignment (a term translated in one
language but missing in another).

## Decision

Restructure the catalog as a single `english source → {lang: translation}` table (`web/i18n._TERMS`) and
**derive** the per-language `CATALOG` from it, so every non-English language is guaranteed to cover the
same key set. Add **French (`fr`)** and **German (`de`)** alongside Spanish, and expand the shared term
set (now ~90 terms: nav, page titles, buttons, frequent labels, metric/status vocabulary, the common
empty-state prompts). `LANGUAGES` lists all four endonyms; the nav selector renders them automatically.

Everything else from ADR-0099 is unchanged: `<html lang>` + the embedded catalog drive `static/translate.js`,
which applies catalog hits instantly and routes the misses (imported names, AI prose) to the AI-backed
`/api/translate`. English remains the source language, so any uncatalogued term shows in English.

## Consequences

- The app's fixed UI now ships hand-translated in **Spanish, French, and German**; dynamic/imported
  content uses the local model in the selected language (same mechanism). Adding a fifth language is one
  column per term plus its endonym — no code change.
- A test pins that the `es`/`fr`/`de` catalogs are aligned to the same key set and that French/German
  translate correctly, so coverage can't silently drift as terms are added.
- These are fixed-vocabulary translations (verified structurally, not numerically — they are not
  metrics). With this, the operator's open options are complete except Float Ratio™ (no published
  formula, unbuildable).

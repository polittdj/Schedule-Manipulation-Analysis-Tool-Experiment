# ADR-0099 — Display language (English / Spanish) for the UI and AI output

Date: 2026-06-19 · Status: accepted

## Context

Operator request: let the user choose the language for **all displayed data and all AI results**, starting
with English and Spanish, and (their choice) **also translate imported content** (task / WBS / resource
names), not just the app's own labels.

A fully hand-translated UI would be thousands of catalog entries and still miss the dynamic content
(imported activity names, computed prose, AI answers). So the design is a two-layer translation pass.

## Decision

A per-session language (`SessionState.language`, default `en`) with a nav selector (`POST /language`,
returns to the page via Referer). The page declares `<html lang=…>` and ships, when not English, an
embedded catalog + `static/translate.js`. Translation has two layers (`web/i18n.py`):

- **Catalog** — a hand-built English→Spanish map of the app's own fixed vocabulary (nav, page titles,
  buttons, metric names, statuses, common labels). High-quality and offline; the authority for forensic
  terms. English is the source language, so any missing entry falls back to the original text.
- **AI fallback** — `POST /api/translate` (catalog → per-session cache → the configured local model)
  translates everything the catalog does not cover (imported names, computed/AI prose), memoised so each
  string is translated at most once. With no model reachable (the Null backend), it returns nothing and
  the client keeps the source text — never a broken page.

`static/translate.js` walks the rendered DOM's text nodes (skipping scripts/inputs/`[data-no-i18n]` and
pure number/date/code text), applies catalog hits instantly, and batches the misses to `/api/translate`.
A `MutationObserver` re-translates content added later — AJAX grids, charts, and AI answers — so **one
mechanism covers server-rendered pages, dynamic views, and AI results**. An applied-output guard stops
the observer from re-translating its own output.

## Consequences

- One language switch translates the whole experience; the catalog guarantees the core UI is correct and
  offline, while imported/AI content is handled by the same local model the other AI features use
  (nothing leaves the machine).
- Adding a language = one catalog dict; widening coverage = more catalog entries (purely additive,
  English always the safe fallback).
- Client-side translation can briefly show English before the swap, and machine-translated dynamic text
  is only as good as the local model (the operator opted into translating imported content). Numbers,
  dates, codes and IDs are deliberately left untouched. The committed tests exercise the catalog + the
  plumbing + the AI round-trip parser (the live model path runs on the operator's machine).

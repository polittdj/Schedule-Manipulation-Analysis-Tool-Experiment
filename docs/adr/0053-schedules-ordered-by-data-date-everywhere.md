# ADR-0053 — Schedules listed earliest→latest data date in every view

Date: 2026-06-16 · Status: accepted

## Context

Operator: *regardless of what tab or visual is being used, the schedules must always be listed
from the earliest data date to the latest data date.*

The loaded schedules live in `SessionState.schedules`, a dict keyed by a cleaned filename.
Dict iteration is **insertion (upload) order**, not data-date order. The session already had a
canonical sorter — `engine/trend.order_versions` (sort by `status_date`, oldest first; undated
keep load order, after the dated ones) — exposed as `SessionState.ordered_versions()`, and the
analytical multi-version views (trend, slippage curves, Bow Wave / CEI, compare, critical-path
evolution, forecast drift) plus the header version dropdown already went through it.

But three places iterated `state.schedules` directly, so they rendered in **upload order**:

1. the home page **"Loaded schedules"** table;
2. the **Dashboard** per-schedule health cards (`/api/dashboard`);
3. a dead, misleadingly-named `SessionState.ordered()` accessor (no callers, but it returned
   upload order — a latent footgun for any future view).

So uploading P5 (Aug-26) before P2 (May-26) listed them P5→P2 on the landing page and the
dashboard, contradicting every other tab.

## Decision

Route **every** schedule listing through `order_versions` so the earliest data date is always
first, no matter the upload order:

- the home "Loaded schedules" table iterates `st.ordered_versions()`;
- `_dashboard_data` builds its cards from `st.ordered_versions()` (the client `dashboard.js`
  renders the array as received — no re-sort — so the API order is the displayed order);
- `SessionState.ordered()` now returns `order_versions(...)` too, matching its name and
  removing the last upload-order accessor.

The single-schedule "Ask the AI" fast path (`len(schedules) == 1`) keeps its direct lookup —
with one version there is nothing to order.

## Scope / safety

Presentation-layer ordering only — no engine, CPM, or metric change; parity untouched. Undated
schedules still fall after the dated ones in load order (they have no data date to place on the
axis). A web regression test uploads the two goldens in **reverse** data-date order and asserts
both the home table and the dashboard card API come back earliest→latest.

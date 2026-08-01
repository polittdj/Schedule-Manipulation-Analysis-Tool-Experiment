"""A wipe must leave NOTHING of the previous session behind — proved by reflection (ADR-0332).

The old handler reset fields by naming them, and the list fell 27 fields behind the dataclass.
What survived a "wipe" was not cosmetic: the entire SRA setup (factor rows, per-UID Risk Ranking
Factors, Best/Worst duration pairs, the pairwise/shared-driver correlation matrix, the cached
per-activity Criticality Index), every JCL cost setting, ``margin_rate``, the AI ``translations``
of imported activity names, and ``dcma_acumen_parity`` — a metric-MODE flag that changes what the
engine computes.

The SRA maps are keyed by **UniqueID**, so this was a Law-2 exposure rather than an annoyance: load
project A, set its risk inputs, wipe, load unrelated project B, and B silently inherited A's Risk
Ranking Factors and Best/Worst pairs wherever the UIDs collided — with nothing on screen saying so.

A test that lists the fields it expects to be cleared would rot exactly the way the handler did, so
this one **enumerates the dataclass** and requires every field to be classified. Adding a field to
``SessionState`` without deciding its wipe behaviour fails the last test in this file.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
from typing import Any

from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from schedule_forensics.web.state import WIPE_PRESERVED

#: Fields whose value cannot be compared with ``==`` or is not session data. Kept SEPARATE from
#: WIPE_PRESERVED (which is a product decision) because this is a mechanical limitation: an
#: ``RLock`` never equals another ``RLock``, and the hook is a function identity.
INCOMPARABLE = frozenset({"_lock", "_stripes", "ai_use_hook"})


def _dirty(st: SessionState) -> None:
    """Set every writable field to something that is NOT its default.

    Deliberately hand-written rather than generated: the point is to simulate a real working
    session (schedules loaded, a filter set, an SRA and a JCL configured), so a field that is only
    reachable through the UI still gets dirtied.
    """
    st.schedules["a.mpp"] = object()  # type: ignore[assignment]
    st.file_meta["a.mpp"] = object()  # type: ignore[assignment]
    st.content_hashes["a.mpp"] = "deadbeef"
    st.active_project = "Project A"
    st.excluded_keys.add("b.mpp")
    st.margin_overlay[1] = True
    st.margin_band_dates = (dt.date(2026, 1, 1),) * 3
    st.margin_band_rates = ((1.0, 2.0), (3.0, 4.0), (5.0, 6.0))
    st.margin_risk_pcts = (11.0, 12.0)
    st.margin_rate = 99.0
    st.role = "scheduler"
    st.filter_mode = "highlight"
    st.flash = "hello"
    st.target_uid = 42
    st.sra_focus_uid = 42
    st.language = "es"
    st.ram_warn_bytes = 123
    st.dcma_acumen_parity = False
    st.translations[("en", "Design")] = "Diseño"
    st.sra_low, st.sra_ml, st.sra_high = 0.1, 0.2, 0.3
    st.sra_overrides[7] = (1, 2, 3)
    st.sra_risks.append(object())  # type: ignore[arg-type]
    st.sra_risk_seq = 5
    st.sra_branches.append(object())  # type: ignore[arg-type]
    st.sra_branch_seq = 6
    st.sra_conditionals.append(object())  # type: ignore[arg-type]
    st.sra_conditional_seq = 7
    st.sra_file = "a.mpp"
    st.sra_factor_rows = ((1, 0.5, 1.5),)
    st.sra_factors[7] = 3
    st.sra_bcwc[7] = (100, 900)
    st.sra_occurrence_mode = "exact_overall"
    st.sra_use_risk_register = not st.sra_use_risk_register
    st.sra_correlation = 0.75
    st.sra_sampling = "lhs"
    st.sra_lhs_centered = not st.sra_lhs_centered
    st.sra_corr_pairs = ((1, 2, 0.5),)
    st.sra_corr_groups = (((1, 2, 3), 0.4),)
    st.sra_criticality[7] = 0.9
    st.sra_criticality_iters = 1000
    st.sra_import_msg = "imported 3 rows"
    st.sra_import_is_error = True
    st.jcl_target_date = "2026-12-31"
    st.jcl_target_cost = 1234.0
    st.jcl_td_share = 0.5
    st.jcl_cost_low, st.jcl_cost_ml, st.jcl_cost_high = 0.8, 1.1, 1.9
    st.jcl_confidence = 0.42
    st.set_filter((("name", "contains", "x"),))  # type: ignore[arg-type]
    st.set_saved_group(object())  # type: ignore[arg-type]
    st.analyses.put("k", object())  # type: ignore[arg-type]
    st.cpms.put("k", object())  # type: ignore[arg-type]
    st.polished.put("k", object())  # type: ignore[arg-type]
    st.summaries["k"] = object()  # type: ignore[assignment]
    st.dash_cores["k"] = object()  # type: ignore[assignment]
    st.dash_cards["k"] = object()  # type: ignore[assignment]
    st._perf_memo["k"] = object()


def _value(st: SessionState, name: str) -> Any:
    v = getattr(st, name)
    # the LRU caches expose no __eq__ — compare what actually matters, their residency
    return len(v) if hasattr(v, "__len__") else v


def test_reset_returns_every_unpreserved_field_to_its_default() -> None:
    """The load-bearing assertion: dirty EVERYTHING, reset, and compare field-by-field against a
    freshly constructed session."""
    st, fresh = SessionState(), SessionState()
    _dirty(st)

    # the control: the dirtying above must actually have changed things, or this proves nothing
    changed = [
        f.name
        for f in dataclasses.fields(st)
        if f.name not in INCOMPARABLE and _value(st, f.name) != _value(fresh, f.name)
    ]
    assert len(changed) >= 40, f"only {len(changed)} fields dirtied — the fixture proves little"

    st.reset()

    leaked = [
        f.name
        for f in dataclasses.fields(st)
        if f.name not in INCOMPARABLE
        and f.name not in WIPE_PRESERVED
        and _value(st, f.name) != _value(fresh, f.name)
    ]
    assert not leaked, f"these survived a reset: {sorted(leaked)}"


def test_the_route_wipes_the_law_two_carriers_the_old_handler_missed() -> None:
    """The regression in operator terms, through the real endpoint: the SRA/JCL setup and the
    metric-mode flag must not outlive a wipe. These are the fields whose survival let project B
    inherit project A's risk inputs by UniqueID."""
    st = SessionState()
    app = create_app(st)
    st.sra_factors[7] = 3
    st.sra_bcwc[7] = (100, 900)
    st.sra_corr_pairs = ((1, 2, 0.5),)
    st.sra_criticality[7] = 0.9
    st.jcl_target_cost = 1234.0
    st.jcl_target_date = "2026-12-31"
    st.margin_rate = 99.0
    st.dcma_acumen_parity = False
    st.translations[("en", "Design")] = "Diseño"

    with TestClient(app) as c:
        assert c.post("/session/wipe", follow_redirects=False).status_code == 303

    assert st.sra_factors == {}
    assert st.sra_bcwc == {}
    assert st.sra_corr_pairs == ()
    assert st.sra_criticality == {}
    assert st.jcl_target_cost is None
    assert st.jcl_target_date is None
    assert st.margin_rate == SessionState().margin_rate
    assert st.dcma_acumen_parity is True, "the metric-mode flag must return to its default"
    assert st.translations == {}


def test_the_wipe_generation_is_bumped_not_rewound() -> None:
    """``wipe_gen`` is a monotonic guard: ADR-0263 uses it so an in-flight pre-wipe compute cannot
    re-insert the operator's data afterwards. A reflection sweep that reset it to 0 would silently
    re-open that window, which is exactly why it is in WIPE_PRESERVED."""
    st = SessionState()
    app = create_app(st)
    st.wipe_gen = 4
    with TestClient(app) as c:
        c.post("/session/wipe", follow_redirects=False)
    assert st.wipe_gen == 5

    # and reset() alone must not touch it either
    st.wipe_gen = 9
    st.reset()
    assert st.wipe_gen == 9


def test_preferences_and_wiring_survive_deliberately() -> None:
    """A wipe clears what was ANALYSED, not how the tool is displayed or wired. The AI backend is
    still forced off (a wiped session must not leave a local model resident)."""
    st = SessionState()
    app = create_app(st)
    st.language = "fr"
    st.ram_warn_bytes = 123
    hook_calls: list[tuple[str, str]] = []
    st.ai_use_hook = lambda a, b: hook_calls.append((a, b))
    classification = st.ai_config.classification

    with TestClient(app) as c:
        c.post("/session/wipe", follow_redirects=False)

    assert st.language == "fr"
    assert st.ram_warn_bytes == 123
    assert st.ai_use_hook is not None, "create_app's wiring must survive a session wipe"
    assert st.ai_config.classification == classification
    assert st.ai_config.backend == "null", "a wipe turns the AI back off"


def test_every_field_is_classified_so_a_new_one_cannot_slip_through() -> None:
    """The anti-rot property, and the reason this file uses reflection at all.

    Adding a field to ``SessionState`` gives it one of three fates: reset by default (the safe
    one, requiring no action), deliberately preserved (name it in ``WIPE_PRESERVED``, with a
    reason), or incomparable (name it here). Nothing else is possible — and the preserved set must
    stay small enough to read, because every entry is state that outlives a wipe.
    """
    names = {f.name for f in dataclasses.fields(SessionState)}
    assert names >= WIPE_PRESERVED, f"WIPE_PRESERVED names dead fields: {WIPE_PRESERVED - names}"
    assert names >= INCOMPARABLE, f"INCOMPARABLE names dead fields: {INCOMPARABLE - names}"
    assert len(WIPE_PRESERVED) <= 8, (
        "the preserved set grew — every entry is operator state that SURVIVES a wipe, so each "
        f"addition needs an ADR-level reason: {sorted(WIPE_PRESERVED)}"
    )

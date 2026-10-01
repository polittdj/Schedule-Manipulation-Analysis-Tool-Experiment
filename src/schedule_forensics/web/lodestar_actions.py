"""Every change LODESTAR's studio makes, through ONE door (ADR-0543).

LODESTAR 2.0 edits a slide two ways: the studio's script posts a small JSON body to ``/api/…``
and repaints from the answer, and — with scripting off — the very same controls are plain forms
that post to the v1 routes and redirect. Both land in :func:`perform`. It calls the SAME shared
action Polaris² calls (:mod:`schedule_forensics.web.onepager_actions` — one copy of every refusal,
rule and sentence), and around it does the two things only LODESTAR does:

* **the session log** — the change is logged for undo with the label the studio's log shows
  (:class:`~schedule_forensics.web.lodestar_history.History`; a refused action changes nothing
  and logs nothing), and
* **the toast** — the one-line confirmation or warning the studio floats bottom-right (every
  refusal is also the page's banner, as it always was: never silent, never half-applied).

It also owns the two example lists LODESTAR offers a newcomer: the template's own six rows as a
list, and a PRIOR / CURRENT pair built from them that shows every kind of move. They are read
through the real reader from a real workbook — exactly what downloading the template and
dropping it back would do — and named as examples everywhere they appear.

Std-lib only (the shared actions are), so ``LODESTAR.pyz`` carries it verbatim.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass

from schedule_forensics.reports.tableset import Cell, Table, TableSet
from schedule_forensics.reports.xlsx import render_xlsx
from schedule_forensics.web import onepager_actions as actions
from schedule_forensics.web.lodestar_history import History, capture
from schedule_forensics.web.onepager import TEMPLATE_HEADER, TEMPLATE_ROWS
from schedule_forensics.web.onepager_common import OnePagerSession

#: The studio's two pages, by the name its API uses.
PAGES: tuple[str, str] = ("timeline", "compare")
#: What :func:`perform` accepts (``upload`` is a file — a list, the risk register or an export to
#: restore, by its ``kind`` field; the rest are small JSON / form bodies; ``risks`` clears the
#: register, ADR-0544).
ACTIONS: frozenset[str] = frozenset(
    {"upload", "example", "title", "window", "today", "clear", "links", "swap", "marking", "risks"}
)
#: An upload's kinds: a One-Pager list (the default), the risk register, an export to restore.
UPLOAD_KINDS: tuple[str, ...] = ("list", "risks", "restore")

#: The example list's and the example pair's file names — named as examples wherever they show.
EXAMPLE_LIST = "example-list.xlsx"
EXAMPLE_PRIOR, EXAMPLE_CURRENT = "example-prior.xlsx", "example-current.xlsx"
#: The example PRIOR list: last month's version of the template's rows, so the pair shows every
#: kind of move — Boots 1 slips, the lander campaign pulls in, MET Testing slips and is newly
#: complete, Boots 2 and MET On-Dock stand still, the CDR is new and the readiness review is gone.
EXAMPLE_PRIOR_ROWS: tuple[tuple[Cell, ...], ...] = (
    ("Flight Manifests", "Boots 1", "6/1/2027", "6/1/2027", ""),
    ("Flight Manifests", "Boots 2", "3/28/2028", "3/28/2028", ""),
    ("Dallas", "Uncrewed Lander Campaign", "4/20/2027", "7/15/2027", ""),
    ("Crew Life", "MET Testing", "12/1/2026", "3/31/2027", "In Progress"),
    ("Crew Life", "MET On-Dock", "10/15/2026", "10/15/2026", "Complete"),
    ("Crew Life", "Crew Readiness Review", "2/1/2027", "2/1/2027", ""),
)


@dataclass(frozen=True)
class Outcome:
    """What one action did: the label it was logged under (``None`` when nothing changed — a
    refusal, or a no-op), and the toast the studio floats (``""`` for none) with its status
    (``pass`` / ``warn`` / ``info``). ``page`` is the page the outcome belongs to when it is
    not the page the action was posted from — a restore lands on the page the export came from
    (ADR-0544); ``None`` otherwise."""

    label: str | None
    toast: str = ""
    status: str = "info"
    page: str | None = None


def page_of(value: str | None) -> str:
    """``"compare"`` for the Compare page (by its API name or its v1 path), else ``"timeline"``."""
    v = (value or "").strip().lower()
    return "compare" if v in ("compare", "onepager-compare", "/onepager-compare") else "timeline"


def item_name(label: str) -> str:
    """The item's own name out of a link label ``swimlane · item (dates)`` — what the log and the
    toasts say (the swimlane and the dates are on the slide already)."""
    name = label.split(" · ", 1)[1] if " · " in label else label
    head, sep, tail = name.rpartition(" (")
    return head if sep and tail.endswith(")") else name


def _workbook(rows: tuple[tuple[Cell, ...], ...]) -> bytes:
    return render_xlsx(
        TableSet("One-Pager list", (Table("One-Pager list", TEMPLATE_HEADER, rows),))
    )


def _message(st: OnePagerSession, page: str) -> tuple[str | None, bool]:
    if page == "compare":
        return st.onepager_compare_msg, st.onepager_compare_is_error
    return st.onepager_msg, st.onepager_is_error


def _links_message(st: OnePagerSession, page: str) -> tuple[str | None, bool]:
    if page == "compare":
        return st.onepager_compare_links_msg, st.onepager_compare_links_is_error
    return st.onepager_links_msg, st.onepager_links_is_error


def _refused(st: OnePagerSession, page: str, *, links: bool = False) -> Outcome:
    """A refusal: logged as nothing, toasted as its own sentence (the banner carries it too)."""
    msg, _error = _links_message(st, page) if links else _message(st, page)
    return Outcome(None, msg or "Nothing changed.", "warn")


def perform(
    st: OnePagerSession,
    history: History,
    action: str,
    params: Mapping[str, str],
    *,
    max_bytes: int,
    upload: tuple[str | None, bytes] | None = None,
) -> Outcome:
    """Do ``action`` with ``params`` (every value a string, as a form or a JSON body gives it) on
    ``params["page"]``, log it, and say how it went. ``upload`` is ``(file name, bytes)`` for the
    ``upload`` action. An unknown action changes nothing and says so."""
    page = page_of(params.get("page"))
    get = params.get
    before = capture(st)
    compare = page == "compare"
    if action == "upload":
        if upload is None:
            return Outcome(None, "No file arrived — choose the workbook again.", "warn")
        name, data = upload
        layout = get("layout", "auto") or "auto"
        kind = (get("kind") or "list").strip().lower()
        if kind == "risks":
            had_risks = st.onepager_risks
            actions.load_risks(st, page, name, data, max_bytes=max_bytes)
            if st.onepager_risks is had_risks or st.onepager_risks is None:
                return _refused(st, page)
            label = f"Risks loaded: {st.onepager_risks.source}"
            history.record(label, before, st, always=True)
            return _loaded(st, page, label)
        if kind == "restore":
            got = actions.restore_export(st, page, name, data, max_bytes=max_bytes)
            if isinstance(got, str):
                _tell(st, page, got)
                return Outcome(None, got, "warn")
            label = f"Restored from {actions.source_name(name)}"
            history.record(label, before, st, always=True)
            return Outcome(label, got.message, "pass", page=got.page)
        if compare:
            slot = (get("slot") or "current").strip().lower()
            had = st.onepager_prior if slot == "prior" else st.onepager_current
            actions.load_compare(st, slot, name, data, max_bytes=max_bytes, layout=layout)
            now = st.onepager_prior if slot == "prior" else st.onepager_current
            if now is had or now is None:
                return _refused(st, page)
            history.record(f"{slot.upper()} list loaded", before, st, always=True)
            return _loaded(st, page, f"{slot.upper()} list loaded")
        had_doc = st.onepager
        actions.load_list(st, name, data, max_bytes=max_bytes, layout=layout)
        if st.onepager is had_doc or st.onepager is None:
            return _refused(st, page)
        label = f"List loaded: {st.onepager.source}"
        history.record(label, before, st, always=True)
        return _loaded(st, page, label)
    if action == "example":
        if compare:
            # the real path, twice: each list read from a real workbook and dropped on its slot,
            # so the operator's Compare links re-bind exactly as they would to any new pair
            actions.load_compare(
                st, "prior", EXAMPLE_PRIOR, _workbook(EXAMPLE_PRIOR_ROWS), max_bytes=max_bytes
            )
            actions.load_compare(
                st, "current", EXAMPLE_CURRENT, _workbook(TEMPLATE_ROWS), max_bytes=max_bytes
            )
            prior, current = st.onepager_prior, st.onepager_current
            if prior is None or current is None:  # pragma: no cover — a fixed workbook
                return _refused(st, page)
            st.onepager_compare_msg = (
                f"Loaded the example pair: {prior.source} as PRIOR ({len(prior.items)} items) and "
                f"{current.source} as CURRENT ({len(current.items)} items) — the template's own "
                "rows, last month and this month."
            )
            st.onepager_compare_is_error = False
            history.record("Both lists loaded", before, st, always=True)
            return Outcome("Both lists loaded", "Example pair loaded — PRIOR and CURRENT.", "pass")
        actions.load_list(st, EXAMPLE_LIST, _workbook(TEMPLATE_ROWS), max_bytes=max_bytes)
        label = f"List loaded: {EXAMPLE_LIST}"
        history.record(label, before, st, always=True)
        return _loaded(st, page, label)
    if action == "title":
        (actions.set_compare_title if compare else actions.set_title)(st, get("title", "") or "")
        return _logged(history, "Slide title changed", before, st)
    if action == "window":
        verb = (get("action") or "apply").strip().lower()
        setter = actions.set_compare_window if compare else actions.set_window
        setter(st, get("start", "") or "", get("end", "") or "", verb)
        win = st.onepager_compare_window if compare else st.onepager_window
        if verb == "clear":
            return _logged(history, "Date window cleared", before, st)
        if _message(st, page)[1] or win is None:
            return _refused(st, page)
        label = f"Date window {win[0].isoformat()} → {win[1].isoformat()}"
        return _logged(history, label, before, st)
    if action == "today":
        verb = (get("action") or "apply").strip().lower()
        actions.set_today(st, "compare" if compare else "onepager", get("today", "") or "", verb)
        if verb == "clear":
            return _logged(history, "Data date cleared", before, st, toast=_message(st, page)[0])
        if _message(st, page)[1] or st.onepager_today is None:
            return _refused(st, page)
        iso = st.onepager_today.isoformat()
        toast = (
            f"Data date {iso} — the red line, caption and legend follow it on both pages and in "
            "every PowerPoint."
        )
        return _logged(history, f"Data date {iso}", before, st, toast=toast)
    if action == "clear":
        if compare:
            actions.clear_compare(st)
            return _logged(history, "Both lists cleared", before, st)
        actions.clear_list(st)
        return _logged(history, "List cleared", before, st)
    if action == "links":
        return _links(st, history, page, before, params)
    if action == "risks":
        verb = (get("action") or "clear").strip().lower()
        if verb != "clear":
            return Outcome(None, f"Unknown risks action “{verb[:20]}” — nothing changed.", "warn")
        actions.clear_risks(st, page)
        return _logged(history, "Risks cleared", before, st, toast=_message(st, page)[0])
    if action == "swap":
        actions.swap_compare(st)
        return _logged(history, "Prior and current swapped", before, st)
    if action == "marking":
        want = (get("marking") or "").strip().lower()
        unclassified = (
            (not st_unclassified(st))
            if want not in ("cui", "unclassified")
            else (want == "unclassified")
        )
        set_unclassified(st, unclassified)
        word = "Unclassified" if unclassified else "CUI"
        toast = f"Marked {word} — the page bars and every PowerPoint now carry it."
        return _logged(history, f"Marking switched to {word}", before, st, toast=toast)
    return Outcome(None, f"Unknown action “{action[:20]}” — nothing changed.", "warn")


def st_unclassified(st: object) -> bool:
    """The session's marking choice (LODESTAR's own attribute, not part of the shared protocol)."""
    return bool(getattr(st, "unclassified", False))


def set_unclassified(st: object, value: bool) -> None:
    st.unclassified = value  # type: ignore[attr-defined]


def _tell(st: OnePagerSession, page: str, msg: str) -> None:
    """A refusal on the page's own banner — what a page view with scripting off shows."""
    if page == "compare":
        st.onepager_compare_msg, st.onepager_compare_is_error = msg, True
    else:
        st.onepager_msg, st.onepager_is_error = msg, True


def _logged(
    history: History, label: str, before: tuple[object, ...], st: object, toast: str | None = None
) -> Outcome:
    """Log ``label`` when the action changed something; a no-op is not a step."""
    if history.record(label, before, st):
        return Outcome(label, toast or "", "info" if toast else "pass")
    return Outcome(None)


def _loaded(st: OnePagerSession, page: str, label: str) -> Outcome:
    """A list landed: its summary sentence is the toast — a warning when rows were skipped."""
    msg, error = _message(st, page)
    return Outcome(label, msg or "", "warn" if error else "pass")


def _links(
    st: OnePagerSession,
    history: History,
    page: str,
    before: tuple[object, ...],
    params: Mapping[str, str],
) -> Outcome:
    compare = page == "compare"
    get = params.get
    verb = (get("action") or "add").strip().lower()
    pred, succ = (get("pred") or "").strip(), (get("succ") or "").strip()
    kind = (get("kind") or "FS").strip().upper()[:4]
    had = st.onepager_compare_links if compare else st.onepager_links
    actions.edit_links(st, "compare" if compare else "onepager", verb, pred, succ, kind)
    now = st.onepager_compare_links if compare else st.onepager_links
    if now == had and verb != "clear":
        return _refused(st, page, links=True)
    if verb == "add":
        new = now[-1]
        what = f"{item_name(new.pred_label)} → {item_name(new.succ_label)} ({new.kind})"
        history.record(f"Add link {what}", before, st)
        return Outcome(f"Add link {what}", f"Link added: {what}", "pass")
    if verb == "remove":
        gone = next(ln for ln in had if ln not in now)
        what = f"{item_name(gone.pred_label)} → {item_name(gone.succ_label)} ({gone.kind})"
        history.record(f"Remove link {what}", before, st)
        return Outcome(f"Remove link {what}", f"Link removed: {what}", "info")
    if verb == "clear" and had:
        history.record("Remove all links", before, st)
        return Outcome("Remove all links", f"All {len(had)} logic link(s) removed.", "info")
    return Outcome(None)


def example_session(st: OnePagerSession, page: str, *, max_bytes: int) -> None:
    """Put the example list (Timeline) or pair (Compare) on ``st`` — for a PREVIEW copy (the
    Show-me demos on an empty studio), never the session itself: no log."""
    if page == "compare":
        actions.load_compare(
            st, "prior", EXAMPLE_PRIOR, _workbook(EXAMPLE_PRIOR_ROWS), max_bytes=max_bytes
        )
        actions.load_compare(
            st, "current", EXAMPLE_CURRENT, _workbook(TEMPLATE_ROWS), max_bytes=max_bytes
        )
    else:
        actions.load_list(st, EXAMPLE_LIST, _workbook(TEMPLATE_ROWS), max_bytes=max_bytes)


def today_or(value: str, fallback: dt.date) -> dt.date:
    """A preview's data date: the ISO date given, else ``fallback`` (never an error — a preview
    of an unreadable date is the slide as it is)."""
    try:
        return dt.date.fromisoformat(value.strip()[:10])
    except ValueError:
        return fallback

"""The Boot Screen — the startup "launch sequence" page served at ``/launch`` (ADR-0426).

The Mission Ops v2 prototype (the MERLIN deck) opens on a full-bleed particle lightshow with a
BEGIN LAUNCH SEQUENCE control, a staged transit, and a welcome panel that hands the operator into
the deck. The repo shipped only ADR-0328's audio module — the sound of a boot sequence with no
boot sequence attached. This module is the screen.

**It is deliberately NOT a ``_page``.** Every other route returns through the story chrome
(header, nav rail, chapter kicker, Continue footer), and every one of those is wrong here: a boot
screen that renders a nav rail is a dashboard with a picture on it. What it does keep — because
design system §6 admits no exception — are the CUI marking bars top and bottom and the compliance
drawer. The classification wording comes from the same session setting the rest of the app reads,
so an UNCLASSIFIED-asserted session shows the same marking here as everywhere else.

**Nothing on this page is a fabricated number.** The prototype's telemetry tiles count "225.4 M
km" down to zero and tick off "14 pre-flight checks" — theatre, with nothing behind it. The design
system's numbers rule (every displayed number traces to the engine payload; missing values show an
em dash) does not have a cinematic exemption, so the tiles here carry three real session facts —
files aboard, activities aboard, the newest data date — and an em dash when the session is empty.
The one non-fact on screen is the stage LABEL ("IGNITION", "CRUISE"), which claims nothing.

The route reads only what is already in memory: ``len(state.schedules)``, a task-count sum, and
the newest ``status_date``. It never triggers a CPM pass — a boot screen that solves seven
networks before it can paint is not a boot screen.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass

from .chrome import _compliance_drawer, _e
from .state import SessionState

#: The em dash the design system requires for "the session cannot supply this". The LITERAL
#: character — never the HTML entity form, which double-escapes the moment anything routes it
#: through ``_e``. That is the defect ``test_no_mdash_entity_sentinel_values_remain_in_app_source``
#: exists to catch, and this module joins that guard's module list in the same commit (the guard
#: reads a NAMED list, so a new view module is uncovered until it is added — ADR-0349's lesson).
_NONE = "—"


@dataclass(frozen=True)
class _BootFacts:
    """The three real facts the boot screen is allowed to show, plus the quick-action set.

    ``files``/``activities`` are counts of what is loaded in this session; ``data_date`` is the
    newest ``status_date`` across those files, or ``None`` when no loaded file carries one (a
    schedule may legitimately have no data date — that is "unknown", not "zero").
    """

    files: int
    activities: int
    data_date: dt.date | None

    @property
    def loaded(self) -> bool:
        return self.files > 0


def _boot_facts(state: SessionState) -> _BootFacts:
    """Read the session's already-in-memory facts. No CPM pass, no scoping, no cache write."""
    schedules = list(state.schedules.values())
    dates = [s.status_date.date() for s in schedules if s.status_date is not None]
    return _BootFacts(
        files=len(schedules),
        activities=sum(len(s.tasks) for s in schedules),
        data_date=max(dates) if dates else None,
    )


#: Quick actions on the welcome panel, as ``(kicker, title, subtitle, route)``. Each points at a
#: route that EXISTS — the same rule ADR-0425 applied to the nav rails, for the same reason: an
#: entry pointing at a screen that is not there is a dead link wearing a label.
_QUICK_ACTIONS: tuple[tuple[str, str, str, str], ...] = (
    (
        "START HERE",
        "Mission Control",
        "The whole programme on one screen, then twelve chapters in order.",
        "/mission",
    ),
    (
        "FORENSICS",
        "Schedule Integrity",
        "Which record edits moved dates, and how much slip those edits absorb.",
        "/integrity",
    ),
    (
        "CHAPTER 03",
        "What drives the date",
        "The one chain that carries the finish, solved and cited.",
        "/path",
    ),
    (
        "CHAPTER 12",
        "The briefing",
        "The findings, in the order a review board asks for them.",
        "/brief",
    ),
)

#: Shown instead when the session is empty — there is nothing to analyse yet, so the only
#: honest action is to load something.
_EMPTY_ACTION: tuple[str, str, str, str] = (
    "NOTHING ABOARD",
    "Import a schedule",
    "Drop an MSPDI, XER or MPP file — or load the worked example — to begin.",
    "/",
)


def _quick_action_html(action: tuple[str, str, str, str]) -> str:
    kicker, title, sub, route = action
    return (
        f'<button type=button data-sf-boot-href="{_e(route)}">'
        f"<div class=qk>{_e(kicker)}</div>"
        f"<div class=qt>{_e(title)}</div>"
        f"<div class=qs>{_e(sub)}</div>"
        f"</button>"
    )


def _launch_html(state: SessionState, *, cui_class: str, cui_text: str) -> str:
    """Render the whole boot document.

    ``cui_class``/``cui_text`` are passed in rather than recomputed so this page can never drift
    from the marking every other page shows — one derivation, in ``_page``, reused here.
    """
    facts = _boot_facts(state)
    drawer = _compliance_drawer(state)

    aboard = (
        f"{facts.files:,} file{'s' if facts.files != 1 else ''} · "
        f"{facts.activities:,} activit{'ies' if facts.activities != 1 else 'y'}"
        if facts.loaded
        else _NONE + " nothing aboard"
    )
    data_date = facts.data_date.isoformat() if facts.data_date else _NONE

    actions = _QUICK_ACTIONS if facts.loaded else (_EMPTY_ACTION,)
    enter_route = "/mission" if facts.loaded else "/"
    enter_label = "ENTER THE DECK" if facts.loaded else "GO TO IMPORT"

    quick = "".join(_quick_action_html(a) for a in actions)

    # A non-executable JSON block, parsed by launch.js — the strict script-src CSP (ADR-0268)
    # forbids an inline `window.SF_BOOT=` script, and "<" is escaped so no imported text could
    # ever close the block early.
    boot_json = json.dumps(
        {
            "files": facts.files,
            "activities": facts.activities,
            "dataDate": facts.data_date.isoformat() if facts.data_date else None,
        }
    ).replace("<", "\\u003c")

    welcome = (
        "Every schedule you have loaded, already parsed and waiting."
        if facts.loaded
        else "No schedules aboard yet — the deck is ready when you are."
    )

    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Launch Sequence — POLARIS</title>
<link rel=icon href="/static/favicon.ico">
<script id=sfBootData type="application/json">{boot_json}</script>
<script src="/static/theme.js"></script>
<script src="/static/launch_audio.js"></script>
<script src="/static/launch.js"></script>
<link rel=stylesheet href="/static/base.css"><link rel=stylesheet href="/static/sf-themes.css">
<link rel=stylesheet href="/static/launch.css">
</head><body class=boot-body>
<div class="cui-banner {cui_class}" data-no-i18n>{cui_text}</div>
{drawer}
<div id=sfBoot>
<canvas id=sfBootCanvas aria-hidden=true></canvas>
<div class=boot-stage>

<div class=boot-hero id=sfBootHero>
<div class=boot-kicker id=sfBootKicker></div>
<h1 class=boot-h1 id=sfBootH1></h1>
<p class=boot-sub id=sfBootSub></p>
</div>

<div class=boot-tel>
<div><div class=boot-tel-k>SCHEDULES ABOARD</div><div class=boot-tel-v>{aboard}</div></div>
<div><div class=boot-tel-k>NEWEST DATA DATE</div><div class=boot-tel-v>{data_date}</div></div>
<div><div class=boot-tel-k>SEQUENCE</div><div class=boot-tel-v id=sfBootSeq>PRE-FLIGHT</div></div>
</div>

<div class=boot-parked>
<div class=boot-controls>
<span>BOOT AUDIO</span>
<button type=button id=humMute class=boot-alt aria-pressed=false>&#9834; HUM</button>
<label>VOL<input type=range id=humVol min=0 max=100 value=40 aria-label="Boot audio volume"></label>
</div>
<div class=boot-actions>
<button type=button id=sfBootBegin class=boot-go>BEGIN LAUNCH SEQUENCE</button>
<button type=button id=sfBootSkip class=boot-alt>Skip to the deck</button>
</div>
<div class=boot-dots>
<button type=button data-sf-boot-dot=0 title="Every schedule, under one light" aria-pressed=true></button>
<button type=button data-sf-boot-dot=1 title="Everything converges on the date" aria-pressed=false></button>
<button type=button data-sf-boot-dot=2 title="A portfolio already in orbit" aria-pressed=false></button>
<button type=button data-sf-boot-dot=3 title="Evidence arrives as a cloud" aria-pressed=false></button>
</div>
<label class=boot-never><input type=checkbox id=sfBootNever> Go straight to the deck next time</label>
</div>

<div class=boot-travel>
<div class=boot-stagelabel id=sfBootStage>PRE-FLIGHT</div>
<div class=boot-stagenote>NOTHING LEAVES THIS MACHINE</div>
</div>

<div class=boot-ready>
<div class=boot-ready-kick><i></i><span>DECK ONLINE</span></div>
<h2>Welcome back.</h2>
<p class=lede>{_e(welcome)}</p>
<div class=boot-quick>{quick}</div>
<div class=boot-actions>
<button type=button id=sfBootEnter class=boot-go data-sf-boot-href="{_e(enter_route)}">{_e(enter_label)}</button>
</div>
</div>

</div>
</div>
<div class="cui-banner bottom {cui_class}" data-no-i18n>{cui_text}</div>
</body></html>"""

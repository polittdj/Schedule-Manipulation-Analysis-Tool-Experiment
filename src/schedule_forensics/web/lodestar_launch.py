"""LODESTAR's launch page — the boot screen the program opens on (ADR-0541, operator ask
2026-09-30: "a launch page very similar to that of Polaris², but different enough that the user
can easily identify the tool").

The SAME screen as Polaris²'s ``/launch`` (ADR-0426): the particle lightshow and the staged
transit of ``static/launch.js``, the styles of ``static/launch.css``, the Boot Audio Hum and its
controls, the compliance chrome top and bottom, real facts in the tiles and a welcome panel that
hands the operator in. What makes it LODESTAR's is served in the page, never forked in the
script: its own name and mark (the ✦ lodestar), its own hero copy and stage words (the star to
steer by, the bearing, the course), its own accent (``lodestar_launch.css`` re-points the boot
palette to the lodestar's gold in every view), its own three facts (the lists aboard, the items,
the data date), and quick actions that name the two pages it has. ``launch.js`` reads those
tables out of the page's JSON block and falls back to Polaris²'s own when a page gives none —
one painter, two identities, and Polaris²'s screen byte-for-byte what it was.

§7a's four rules hold here as there: the compliance chrome is not optional off the shell; no
invented number (an empty studio shows an em dash); the ground is dark in every view; reduced
motion is a still frame. Std-lib only, so ``LODESTAR.pyz`` carries it verbatim.
"""

from __future__ import annotations

import datetime as dt
import json

from schedule_forensics.web.htmlkit import _e
from schedule_forensics.web.lodestar_shell import (
    NAME,
    TAGLINE,
    VERSION,
    compliance_drawer,
    credit_html,
    marking,
)
from schedule_forensics.web.onepager_common import OnePagerSession

#: The design system's em dash for "the session cannot supply this" — the literal character.
_NONE = "—"

#: LODESTAR's hero scenes: ``(kicker, headline, sub, shape)`` — the shape is the index of the
#: particle scene ``launch.js`` composes (0 helix · 1 wave · 2 galaxy · 3 nebula). Three scenes,
#: none of them Polaris²'s: the galaxy for the star to steer by, the wave for the movement
#: between two lists, the nebula for the logic the operator draws out of it.
HEROES: tuple[tuple[str, str, str, int], ...] = (
    (
        "01 — LODESTAR · ONE-PAGER STUDIO",
        "One list. One slide. One star to steer by.",
        "Drop a plain Excel list and get the one-slide swimlane timeline a review board reads in "
        "a minute — and a PowerPoint of the same slide, built from native, editable shapes. "
        "Nothing you load leaves this computer, and there is no AI in it.",
        2,
    ),
    (
        "02 — PRIOR AND CURRENT · WHAT MOVED",
        "Two lists, and the distance between them.",
        "Compare lays last month's list under this month's on one slide: what slipped, what "
        "pulled in, what is new and what was removed — every move in calendar days, every "
        "decision the page made named by row.",
        1,
    ),
    (
        "03 — YOUR LOGIC · YOUR ARROWS",
        "Draw only the logic you mean.",
        "Pick two items and add the link — Finish-to-Start, Start-to-Start, Finish-to-Finish or "
        "Start-to-Finish. Only the links you add are drawn, every one fitted on the slide, and "
        "each carried into PowerPoint as an arrow.",
        3,
    ),
)

#: The transit's stage words — labels, never measurements (§7a): a lodestar's, not a rocket's.
STAGES: tuple[str, ...] = (
    "PRE-FLIGHT",
    "STAR FIX",
    "BEARING SET",
    "COURSE LAID",
    "ON STATION",
    "STUDIO OPEN",
)

#: The welcome panel's quick actions, ``(kicker, title, sub, route)`` — each a route that EXISTS.
QUICK_ACTIONS: tuple[tuple[str, str, str, str], ...] = (
    (
        "TIMELINE",
        "One-Pager Timeline",
        "One Excel list becomes one swimlane slide — and a PowerPoint of the same slide.",
        "/onepager",
    ),
    (
        "COMPARE",
        "One-Pager Compare",
        "A prior and a current list on one slide: what slipped, pulled in, is new or is gone.",
        "/onepager-compare",
    ),
)

#: Where the studio opens: the Timeline page (the skip, the Escape key and the "go straight to
#: the studio next time" opt-out all land here).
HOME = "/onepager"


def _quick_action_html(action: tuple[str, str, str, str]) -> str:
    kicker, title, sub, route = action
    return (
        f'<button type=button data-sf-boot-href="{_e(route)}">'
        f"<div class=qk>{_e(kicker)}</div>"
        f"<div class=qt>{_e(title)}</div>"
        f"<div class=qs>{_e(sub)}</div>"
        f"</button>"
    )


def facts(st: OnePagerSession) -> tuple[int, int]:
    """``(lists aboard, items aboard)`` — the Timeline list and the Compare page's two, counted
    from what the session holds; no layout is computed."""
    docs = [d for d in (st.onepager, st.onepager_prior, st.onepager_current) if d is not None]
    return len(docs), sum(len(d.items) for d in docs)


def lodestar_launch_html(
    st: OnePagerSession, *, unclassified: bool, today: dt.date, chosen: bool
) -> str:
    """The whole launch document. ``today`` is the data date in force (the operator's when
    ``chosen``, else the computer's) — the third tile, a real session fact."""
    cls, text = marking(unclassified)
    lists, items = facts(st)
    aboard = (
        f"{lists} list{'s' if lists != 1 else ''} · {items:,} item{'s' if items != 1 else ''}"
        if lists
        else f"{_NONE} nothing aboard"
    )
    dd = f"{today.isoformat()} · {'set by you' if chosen else 'computer date'}"
    boot_json = json.dumps(
        {
            "files": lists,
            "activities": items,
            "dataDate": today.isoformat(),
            "home": HOME,
            "stages": list(STAGES),
            "heroes": [{"k": k, "h": h, "s": s, "shape": shape} for k, h, s, shape in HEROES],
        }
    ).replace("<", "\\u003c")
    dots = "".join(
        f'<button type=button data-sf-boot-dot={i} title="{_e(h)}" '
        f"aria-pressed={'true' if i == 0 else 'false'}></button>"
        for i, (_k, h, _s, _shape) in enumerate(HEROES)
    )
    quick = "".join(_quick_action_html(a) for a in QUICK_ACTIONS)
    welcome = (
        "Every list you have loaded is parsed and waiting."
        if lists
        else "No list aboard yet — the studio is ready when you are."
    )
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Launch — {NAME}</title>
<link rel=icon href="/static/lodestar.ico">
<script id=sfBootData type="application/json">{boot_json}</script>
<script src="/static/theme.js"></script>
<script src="/static/launch_audio.js"></script>
<script src="/static/launch.js"></script>
<link rel=stylesheet href="/static/base.css"><link rel=stylesheet href="/static/sf-themes.css">
<link rel=stylesheet href="/static/launch.css"><link rel=stylesheet href="/static/lodestar_launch.css">
</head><body class="boot-body lodestar-boot">
<div class="cui-banner {cls}" data-no-i18n>{_e(text)}</div>
{compliance_drawer()}
<div class=boot-version data-no-i18n title="The version of this program — what LODESTAR --version reports">{_e(NAME)} {_e(VERSION)}</div>
<p class="ls-credit ls-boot-credit">{credit_html()}</p>
<div id=sfBoot>
<canvas id=sfBootCanvas aria-hidden=true></canvas>
<div class=boot-stage>

<div class=ls-boot-brand aria-label="{_e(NAME)} — {_e(TAGLINE)}">
<span class=ls-boot-mark aria-hidden=true>&#10022;</span>
<span class=ls-boot-name>{_e(NAME)}</span>
<span class=ls-boot-tagline>{_e(TAGLINE)}</span>
</div>

<div class=boot-hero id=sfBootHero>
<div class=boot-kicker id=sfBootKicker></div>
<h1 class=boot-h1 id=sfBootH1></h1>
<p class=boot-sub id=sfBootSub></p>
</div>

<div class=boot-tel>
<div><div class=boot-tel-k>LISTS ABOARD</div><div class=boot-tel-v>{_e(aboard)}</div></div>
<div><div class=boot-tel-k>DATA DATE</div><div class=boot-tel-v>{_e(dd)}</div></div>
<div><div class=boot-tel-k>SEQUENCE</div><div class=boot-tel-v id=sfBootSeq>{_e(STAGES[0])}</div></div>
</div>

<div class=boot-parked>
<div class=boot-controls>
<span>BOOT AUDIO</span>
<button type=button id=humMute class=boot-alt aria-pressed=false>&#9834; HUM</button>
<label>VOL<input type=range id=humVol min=0 max=100 value=40 aria-label="Boot audio volume"></label>
</div>
<div class=boot-actions>
<button type=button id=sfBootBegin class=boot-go>TAKE A STAR FIX</button>
<button type=button id=sfBootSkip class=boot-alt>Skip to the studio</button>
</div>
<div class=boot-dots>{dots}</div>
<label class=boot-never><input type=checkbox id=sfBootNever> Go straight to the studio next time</label>
</div>

<div class=boot-travel>
<div class=boot-stagelabel id=sfBootStage>{_e(STAGES[0])}</div>
<div class=boot-stagenote>NOTHING LEAVES THIS COMPUTER · NO AI</div>
</div>

<div class=boot-ready>
<div class=boot-ready-kick><i></i><span>STUDIO OPEN</span></div>
<h2>Welcome to the studio.</h2>
<p class=lede>{_e(welcome)}</p>
<div class=boot-quick>{quick}</div>
<div class=boot-actions>
<button type=button id=sfBootEnter class=boot-go data-sf-boot-href="{HOME}">OPEN THE STUDIO</button>
</div>
</div>

</div>
</div>
<p class="ls-credit ls-boot-credit ls-boot-foot">{credit_html()}</p>
<div class="cui-banner bottom {cls}" data-no-i18n>{_e(text)}</div>
</body></html>"""

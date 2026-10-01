"""LODESTAR's launch page — the front door the program opens on (ADR-0541; rebuilt to the
"Console" design handoff by ADR-0543, LODESTAR 2.0).

Two columns on the graticule. On the left: the mark, a hero that cycles through LODESTAR's three
stories every 6.5 s, **Take a star fix** (a six-stage transit — PRE-FLIGHT to STUDIO OPEN — that
ends on a welcome panel handing the operator to either page), **Skip to the studio**, the "go
straight to the studio next time" opt-out, and three real facts: the lists aboard, the data date,
the stage. On the right: the list→slide animation that shows what the program does, the six
stages, and the sentence that matters most — nothing leaves this computer, and there is no AI.

The v1 page borrowed Polaris²'s boot screen (its particle field and its Boot Audio Hum); the
design replaces that column with the teaching animation and has no sound, so LODESTAR 2.0 loads
nothing of Polaris²'s here. The opt-out keeps v1's storage key (``sf-boot-skip``, read by
``static/lodestar_launch.js`` before the page paints) so an operator who chose it keeps it.

§7a's rules hold: the compliance chrome is not optional off the shell (the marking bars top and
bottom, the handling drawer, the credit); no invented number (an empty studio shows an em dash);
reduced motion is a still frame. Std-lib only, so ``LODESTAR.pyz`` carries it verbatim.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.web.htmlkit import _e
from schedule_forensics.web.lodestar_icons import icon, sprite
from schedule_forensics.web.lodestar_shell import (
    NAME,
    TAGLINE,
    VERSION,
    compliance_drawer,
    credit_html,
    json_block,
    mark_bar,
)
from schedule_forensics.web.lodestar_studio import list_to_slide
from schedule_forensics.web.onepager_common import OnePagerSession

#: The design system's em dash for "the session cannot supply this" — the literal character.
_NONE = "—"

#: LODESTAR's hero copy, ``(kicker, headline, sub)`` — the design handoff's, verbatim.
HEROES: tuple[tuple[str, str, str], ...] = (
    (
        "01 — LODESTAR · ONE-PAGER STUDIO",
        "One list. One slide. One star to steer by.",
        "Drop a plain Excel list and get the one-slide swimlane timeline a review board reads in "
        "a minute — and a PowerPoint of the same slide, built from native, editable shapes. "
        "Nothing you load leaves this computer, and there is no AI in it.",
    ),
    (
        "02 — PRIOR AND CURRENT · WHAT MOVED",
        "Two lists, and the distance between them.",
        "Compare lays last month's list under this month's on one slide: what slipped, what "
        "pulled in, what is new and what was removed — every move in calendar days, every "
        "decision the page made named by row.",
    ),
    (
        "03 — YOUR LOGIC · YOUR ARROWS",
        "Draw only the logic you mean.",
        "Pick two items and add the link — Finish-to-Start, Start-to-Start, Finish-to-Finish or "
        "Start-to-Finish. Only the links you add are drawn, every one fitted on the slide, and "
        "each carried into PowerPoint as an arrow.",
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
#: The hero's dwell, and one transit stage's, in milliseconds (the design's figures).
HERO_MS, STAGE_MS = 6500, 650


def facts(st: OnePagerSession) -> tuple[int, int]:
    """``(lists aboard, items aboard)`` — the Timeline list and the Compare page's two, counted
    from what the session holds; no layout is computed."""
    docs = [d for d in (st.onepager, st.onepager_prior, st.onepager_current) if d is not None]
    return len(docs), sum(len(d.items) for d in docs)


def _quick(action: tuple[str, str, str, str]) -> str:
    kicker, title, sub, route = action
    return (
        f'<a class=ls-quick href="{_e(route)}"><span class=ls-quick-k>{_e(kicker)}</span>'
        f"<span class=ls-quick-t>{_e(title)}</span><span class=ls-quick-s>{_e(sub)}</span></a>"
    )


def lodestar_launch_html(
    st: OnePagerSession, *, unclassified: bool, today: dt.date, chosen: bool
) -> str:
    """The whole launch document. ``today`` is the data date in force (the operator's when
    ``chosen``, else the computer's) — the second tile, a real session fact."""
    lists, items = facts(st)
    aboard = (
        f"{lists} list{'s' if lists != 1 else ''} · {items:,} item{'s' if items != 1 else ''}"
        if lists
        else f"{_NONE} nothing aboard"
    )
    dd = f"{today.isoformat()} · {'set by you' if chosen else 'computer date'}"
    welcome = (
        "Every list you have loaded is parsed and waiting."
        if lists
        else "No list aboard yet — the studio is ready when you are."
    )
    k0, h0, s0 = HEROES[0]
    dots = "".join(
        f'<button type=button class=ls-hero-dot data-ls-hero="{i}" title="{_e(h)}" '
        f'aria-label="{_e(h)}" aria-pressed={"true" if i == 0 else "false"}></button>'
        for i, (_k, h, _s) in enumerate(HEROES)
    )
    stages = "".join(
        f'<div class="ls-stage{" is-active" if i == 0 else ""}" data-ls-stage="{i}">'
        f"<div class=ls-stage-bar></div><div class=ls-stage-label>0{i + 1} {_e(s)}</div></div>"
        for i, s in enumerate(STAGES)
    )
    boot = json_block(
        "lsBoot",
        {
            "home": HOME,
            "stages": list(STAGES),
            "heroes": [{"k": k, "h": h, "s": s} for k, h, s in HEROES],
            "heroMs": HERO_MS,
            "stageMs": STAGE_MS,
        },
    )
    return f"""<!doctype html><html lang=en class=no-js data-theme=dark><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Launch — {NAME}</title>
<link rel=icon href="/static/lodestar.ico">
<script src="/static/lodestar_view.js"></script>
{boot}
<script src="/static/lodestar_launch.js"></script>
<link rel=stylesheet href="/static/lodestar_tokens.css"><link rel=stylesheet href="/static/lodestar_studio.css">
<link rel=stylesheet href="/static/lodestar_launch.css">
</head><body class="ls-app ls-launch lodestar-boot">{sprite()}
<div class=ls-root>
{mark_bar(unclassified, "top")}
<div class=ls-launch-main>
<div class=ls-launch-top>
<span class=boot-version data-no-i18n title="The version of this program — what LODESTAR --version reports">{_e(NAME)} {_e(VERSION)}</span>
<span class=ls-launch-drawer>{compliance_drawer()}</span>
<span class="ls-credit-who ls-boot-credit">{credit_html()}</span>
</div>
<div class=ls-launch-grid>
<div class=ls-launch-left>
<div class=ls-launch-brand aria-label="{_e(NAME)} — {_e(TAGLINE)}">
<span class=ls-launch-mark aria-hidden=true>&#10022;</span>
<span class=ls-launch-name>{_e(NAME)}</span>
<span class=ls-launch-tagline>{_e(TAGLINE)}</span>
</div>
<div class=ls-hero id=lsHero>
<div class=ls-hero-k id=lsHeroK>{_e(k0)}</div>
<h1 class=ls-hero-h id=lsHeroH>{_e(h0)}</h1>
<p class=ls-hero-s id=lsHeroS>{_e(s0)}</p>
<div class="ls-hero-dots ls-js-only">{dots}</div>
</div>
<div class=ls-welcome id=lsWelcome hidden>
<div class=ls-welcome-status><span class="ls-dot ls-dot-pass"></span>STUDIO OPEN</div>
<h1 class=ls-hero-h>Welcome to the studio.</h1>
<p class=ls-welcome-lede>{_e(welcome)}</p>
<div class=ls-quicks>{"".join(_quick(a) for a in QUICK_ACTIONS)}</div>
<div><a class="aismat-btn aismat-btn--primary aismat-btn--lg" href="{HOME}" id=lsEnter><span>Open the studio</span>{icon("arrow-right", 18)}</a></div>
</div>
<div class=ls-launch-actions id=lsActions>
<button type=button class="aismat-btn aismat-btn--primary aismat-btn--lg ls-js-only" id=lsStarFix>{icon("compass", 18)}<span>Take a star fix</span></button>
<a class="aismat-btn aismat-btn--ghost aismat-btn--lg" href="{HOME}" id=lsSkip><span>Skip to the studio</span></a>
</div>
<label class="aismat-check ls-js-only" id=lsNeverWrap><input type=checkbox class=aismat-check__input id=lsNever><span class=aismat-check__box>{icon("check", 13)}</span><span>Go straight to the studio next time</span></label>
<div class=ls-tel>
<div class=ls-tel-cell><div class=ls-tel-k>LISTS ABOARD</div><div class=ls-tel-v>{_e(aboard)}</div></div>
<div class=ls-tel-cell><div class=ls-tel-k>DATA DATE</div><div class=ls-tel-v>{_e(dd)}</div></div>
<div class=ls-tel-cell><div class=ls-tel-k>SEQUENCE</div><div class="ls-tel-v is-gold" id=lsSeq>{_e(STAGES[0])}</div></div>
</div>
</div>
<div class=ls-launch-right>
<div class=ls-launch-card>
<div class=ls-tel-k style="margin-bottom:12px">HOW IT WORKS · WATCH THE LIST BECOME THE SLIDE</div>
{list_to_slide()}
</div>
<div class=ls-stages>{stages}</div>
<div class=ls-launch-foot>NOTHING LEAVES THIS COMPUTER · NO AI</div>
</div>
</div>
<div class="ls-launch-credit ls-credit-who">{credit_html()}</div>
</div>
{mark_bar(unclassified, "bottom")}
</div>
</body></html>"""

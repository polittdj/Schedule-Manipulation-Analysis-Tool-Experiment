"""The HTML kit every page body is built from — escaping, the takeaway headline, the panel head
and its tool strip — in a leaf module that imports nothing but the standard library (ADR-0539).

These four were born in ``chrome.py`` (``_e``, ``_utility_takeaway``) and ``components.py``
(``_shell_tools``, ``_panel_head``), and both of those import the session state and, through it,
the engine. The One-Pager pages use only these four, and LODESTAR — the standalone One-Pager
program built from the SAME page modules — must import them without the engine. So they live
here, moved VERBATIM, and ``chrome`` / ``components`` re-export them with the ``X as X`` idiom:
every existing import path resolves to the same objects (pinned by
``tests/web/test_monolith_split_contract.py``).

The marking wording lives here for the same reason: the CUI banner Polaris² draws and the one
LODESTAR draws must be the SAME two sentences, never two copies.
"""

from __future__ import annotations

import html

#: The page and export marking (ADR-0426's one derivation reads these): the default CLASSIFIED
#: session marks CUI; only the operator-asserted UNCLASSIFIED mode drops the controls marking.
CUI_MARKING = "Controlled Unclassified Information • CUI"
UNCLASSIFIED_MARKING = "Unclassified • no CUI controls asserted"


def _e(text: object) -> str:
    return html.escape(str(text))


def _utility_takeaway(headline: str, lede: str) -> str:
    """The takeaway h1 + context line the DoD requires of any page (ADR-0311, rank 12).

    Rank 12's pages are Setup utilities and per-file drills, not spine chapters, so they take the
    kicker/no-segue treatment ADR-0311 settled — but the DoD's *takeaway h1 + context line* applies
    to every page regardless of where it sits in the story. `DESIGN-SYSTEM.md` §5: a headline states
    a FINDING, not a topic. Every figure passed in here must already be rendered further down the
    same page, so the number the reader sees first is one they can verify below it, and a missing
    value must arrive as an em dash rather than a fabricated zero.
    """
    return f'<h1 class="page-takeaway" data-no-i18n>{headline}</h1><p class="page-lede">{lede}</p>'


def _shell_tools(*, export_title: str = "", big: bool = True) -> str:
    """The three-glyph tool strip (panelkit.js wiring): ⤓ EXCEL renders ONLY when the panel
    carries a ``data-export`` URL to an EXISTING endpoint (never a dead link — rank-3 law);
    ⛶ ENLARGE by default. ▦ DATA is omitted on the analysis panels: each one's table IS the
    data (the home-shell precedent). ``big=False`` omits the ⛶ for the ONE panel whose chart
    script supplies the panel's single ⛶ itself (the /analysis scatter — the curves.js
    pattern, ADR-0317): a second head glyph on that panel was the round-11 inert-duplicate
    defect (it flipped its label while ``:has(.sf-tilebox)`` kept the panel static)."""
    excel = (
        f'<button type=button data-sf-excel title="{_e(export_title)}" '
        'aria-label="Export this panel&#39;s data to Excel">⤓ EXCEL</button>'
        if export_title
        else ""
    )
    enlarge = (
        "<button type=button data-sf-big aria-pressed=false "
        'aria-label="Enlarge this panel">⛶ ENLARGE</button>'
        if big
        else ""
    )
    return f"<div class=sf-tools data-noprint=1>{excel}{enlarge}</div>"


def _panel_head(title: str, *, tools: str = "", prov: str = "", h2_attrs: str = "") -> str:
    """The panel-contract headline strip: h2 + tools + provenance chip. ``title`` is HTML —
    callers escape their own dynamic parts (the heading TEXT is unchanged; the uppercase
    treatment is CSS, so existing content assertions keep holding). ``h2_attrs`` carries a
    pre-existing heading attribute through a conversion (leading space included, e.g.
    ``" data-no-i18n"``) — the /margin headings were deliberately translation-pinned and
    joining the contract must not silently unpin them."""
    return f"<div class=panel-head><h2{h2_attrs}>{title}</h2>{tools}{prov}</div>"


#: The handling & export-control drawer — the ONE copy of the CUI / ITAR / EAR prose (DESIGN-SYSTEM
#: §6, §7a). ``{locality}`` is the sentence about where data goes (Polaris² derives it from the
#: session's AI routing) and ``{where}`` names where the page's marking is set ("in AI Settings"
#: in Polaris², the marking switch in LODESTAR) — moved here from ``chrome.py`` (ADR-0539) so the
#: standalone program shows the same words rather than a second copy.
_DRAWER_HTML = """<details class=compliance-drawer id=complianceDrawer>
<summary>Handling &amp; export-control notice — click to review (CUI / ITAR / EAR)</summary>
<div class=compliance-body>
<h3>Controlled Unclassified Information (CUI)</h3>
<p>Treat every loaded schedule and every derived metric on these pages as CUI unless the project
is explicitly marked UNCLASSIFIED {where}. Handle per 32 CFR Part 2002 and your
organization's CUI program: store on approved systems only, share only with a lawful government
purpose, and destroy per records schedules. {locality}</p>
<h3>Export control (ITAR / EAR)</h3>
<p>WARNING — Schedules for defense or space programs may contain technical data subject to the
International Traffic in Arms Regulations (ITAR, 22 CFR 120&ndash;130) or the Export
Administration Regulations (EAR, 15 CFR 730&ndash;774). Do not export, release, or disclose such
data to foreign persons, in the U.S. or abroad, without proper authorization. Violations carry
severe criminal and civil penalties.</p>
<h3>Your responsibility</h3>
<p>The markings above reflect the session's declared classification &mdash; not a review of your
data. You remain responsible for confirming the actual sensitivity, markings, and distribution
statements of every file you load and every report you export.</p>
</div>
</details>"""

"""LODESTAR — One-Pager Studio: the One-Pager Timeline and the One-Pager Compare as a program of
their own, shared as ONE file that needs nothing but Python (ADR-0539).

Created by David Politte (david.j.politte@nasa.gov). Built from the SAME modules Polaris² serves
the two pages with — the intake, the layout, the logic links, the compare, the PowerPoint and
Excel writers, the page bodies and the server security policy — so the two programs cannot draw
a different slide from the same list. No AI of any kind; nothing leaves the machine.

``tools/lodestar/build_lodestar.py`` packs the allowlisted modules VERBATIM into
``lodestar/LODESTAR.pyz``; ``tests/lodestar/`` keeps that file in lockstep with ``src``.
"""

from __future__ import annotations

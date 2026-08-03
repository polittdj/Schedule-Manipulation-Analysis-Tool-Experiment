---
name: render-verify
description: Render POLARIS/SMAT's actual pages and measure them, instead of reading the source that produces them. Use whenever a claim concerns what a page SHOWS — a displayed figure, a takeaway sentence, a KPI card, a chart, a caption, an axis, a data-date line, an enlarge/toggle control, a theme — and whenever a finding says "depends on how it is rendered" or "I did not execute the page". Also use before asserting a UI change works, and to diff two trees' renders. In this repo, inspection and green unit tests have repeatedly disagreed with the browser.
---

# Render it, don't read it

The repo's #1 verification lesson: *inspection and green unit tests lie; execute the artifact.*
Nearly every UI, packaging and security war story here was invisible to code review and CI and only
surfaced by rendering the real page or driving a real browser.

**When a prior finding names the evidence it lacked, that sentence IS the task definition.** Three
falsy-zero rows sat UNSURE for five weeks behind *"I did not execute the rendered page"*; rendering
settled all three in an hour (ADR-0343).

## Tier 1 — server-rendered HTML (fast, no browser)

Enough for text, figures, `—` sentinels, captions, panel markup, and render diffs. Write this to the
scratchpad (not the repo):

```python
"""Render one route to HTML, with per-launch nonces normalised."""

import json, re, sys
from pathlib import Path
from fastapi.testclient import TestClient
from schedule_forensics.web.app import SessionState, create_app

REPO = Path("/home/user/Schedule-Manipulation-Analysis-Tool-Experiment")
FIX = REPO / "tests" / "fixtures" / "test_projects"


def load(c, names, folder="TP4_DataCenter"):
    """Upload as ONE multi-version project — without file_meta each file is its own project."""
    files = [("files", (n, (FIX / n).read_bytes(), "text/xml")) for n in names]
    meta = json.dumps(
        [
            {"rel": f"{folder}/{n}", "mtime": 1_700_000_000_000 + i * 86_400_000}
            for i, n in enumerate(names)
        ]
    )
    assert c.post("/upload", files=files, data={"file_meta": meta}).status_code == 200


def normalise(html: str) -> str:
    """Strip per-launch nonces/tokens so two renders are byte-comparable."""
    html = re.sub(r'(name=sf-launch content=")[^"]*"', r'\1LAUNCH"', html)
    return re.sub(r"\?v=[0-9a-zA-Z._-]+", "?v=V", html)


route = sys.argv[1]
names = (
    sys.argv[2].split(",")
    if len(sys.argv) > 2
    else [f"TP4_DataCenter_v{i}.xml" for i in range(1, 6)]
)
app = create_app(SessionState())
with TestClient(app) as c:
    load(c, names)
    r = c.get(route)
    print(f"# {route} -> {r.status_code} ({len(r.text)} bytes)", file=sys.stderr)
    sys.stdout.write(normalise(r.text))
```

**Normalise the launch nonce.** `app.py` emits `<meta name=sf-launch content="…">` fresh per server
process and cache-busts static URLs to `?v=<version>`; without normalising, every diff is noise.

**Render diff across a change** — the strongest available proof that an edit moved (or did not move)
a page:

```bash
python render.py /cei > /tmp/…/before.html      # pristine tree
# … apply the change …
python render.py /cei > /tmp/…/after.html
diff /tmp/…/before.html /tmp/…/after.html       # empty == byte-identical == no-op proven
```

## Tier 2 — real chromium (the measured-box proof)

Required for anything about **layout, geometry, or a control's effect**: enlarge, focus overlays,
tick spacing, overlap, scroll behavior. A class read-back is **not** a proof — `.is-big` is only
`grid-column:1/-1`, so on a block-layout panel it is inert while the assertion passes (ADR-0304).

```bash
python -m pip install playwright         # dev-only; the runtime stays std-lib for I/O
python -m pytest -q tests/web/test_r11_panel_contract.py -p no:cacheprovider
```

Resolve the browser the way the suite does — vendored binary if present, else playwright's own.
Never pin a build number; the vendored dir is versioned (`chromium-1194`, …) and a container bump
silently reintroduces a skip:

```python
_VENDOR_ROOT = Path("/opt/pw-browsers")
_VENDOR_GLOBS = (
    "chromium*/chrome-linux/chrome",
    "chromium_headless_shell*/*/chrome-headless-shell",
)
```

Serve for real (`uvicorn` on a free 127.0.0.1 port in a daemon thread), then measure
`getBoundingClientRect()` on **both sides of a real click** and require the box to have CHANGED.
Let charts settle before the baseline rect (~1.2 s) and make measurements **scroll-invariant**
(ADR-0317).

**A SKIP here is a FAILURE, not a pass.** A browser-gated proof that never executes is the exact
failure class ADR-0304/0305 exist to retire.

## The cheap, high-yield check

Render any page that mixes an em-dash KPI strip with a chart, **on an input where the figure is
absent**, and see whether the two halves still agree. A self-contradiction inside one viewport —
takeaway saying "no month could be scored", KPI cards saying `—`, and the panel between them drawing
"Latest scored month · 0 planned" — is invisible to grep and to a unit test of either half, and
glaring on render.

## Traps this repo has paid for

- **Source call sites ≠ rendered charts.** `curves.js` has ONE `axisTitles` call site and renders
  THREE charts. Count what renders, not what is written.
- **Read the emitter before writing the parser.** `_stat_cards` emits **value THEN label**, so a
  regex scanning forward from a label reports the NEXT card's value. A KPI read claimed `Planned = 0`
  where the page said `—`.
- **The missing-value sentinel is the literal `—`**, never `&mdash;`.
- **Headless hides scrollbars** — a layout finding taken headless may not reproduce for the operator.
- **`pgrep -f <pat>` self-matches exactly like `pkill -f`.** A pattern that matches your own command
  line will always "find" a process — and a *compound* wait condition built on one can report the
  **opposite** of the truth. Measured 2026-08-03: an `until [ ! -d /proc/$(pgrep -f "pytest -q" | head -1) ] || …`
  waiter printed "SUITE FINISHED" while pytest was still burning CPU, because the self-matched PID it
  picked had already exited. Bracket the first character (`[p]ytest`) so the pattern cannot match the
  waiter, and **confirm with `ps` before acting on a completion signal you built yourself.**
- **Verify in all four themes** (console / daylight / apollo / jarvis) — daylight's nav is a `sticky`
  top bar while the dark themes use a `fixed` left rail, and a clamp written for one missed the other.
- **Load with `file_meta`** or each file becomes its own one-version project and multi-version pages
  render their fallback instead of the view you meant to measure.

## Running the app for real

```bash
schedule-forensics            # or: python -m schedule_forensics.launcher
```
Binds a free 127.0.0.1 port and opens a browser. The watchdog stops the server ~10 min after the last
heartbeat, so a relaunch inside that window can land on the OLD process (OR-06) — check for a
survivor before concluding a fresh launch showed stale state.

"""The render oracle: a committed, route-derived corpus of labelled HTTP renders.

**Why this file exists.** Every monolith-split slice since ADR-0372 proves its extraction is
behaviour-preserving by rendering a large corpus of URLs against the pristine tree and the cut
tree and asserting the two are byte-identical. For nine slices that corpus lived only in a
session scratchpad and was described in ADR prose, so every new container *re-derived* it — and
ADR-0381 measured the result: the mechanically-derived core healed itself from ``app.routes``
(``[empty]`` reproduced on the nose) while the hand-authored variant labels did not, because the
ADRs name some in prose and record none of their URLs. The corpus shrank 648 → 592 and the
shortfall would have been reported as byte-identity. *The parts of an oracle that were added
because they were hard to reach are the parts most likely to be lost.*

So the instrument lands in the repo (ADR-0382). Two halves, deliberately different in kind:

* :func:`route_labels` is **derived from** ``app.routes`` — it cannot go stale, and it grows on
  its own when a route is added. This is the self-healing core.
* :data:`VARIANT_LABELS` is **hand-authored** — query-string and POST-sequence labels that reach
  code the bare route surface cannot. This is the half that decayed, so it is written down here,
  by URL, and pinned by ``tests/guards/test_render_oracle_corpus.py``.

Nothing here is a product module: it renders pages through ``TestClient`` for verification only.

Usage from a slice harness (both trees get the SAME corpus — that is the point)::

    PYTHONPATH=<tree>/src python tests/web/oracle_corpus.py --out /tmp/pristine
    PYTHONPATH=<tree>/src python tests/web/oracle_corpus.py --out /tmp/cut
    diff -r /tmp/pristine /tmp/cut

Set ``SF_ORACLE_FIXTURES`` to pin the fixture root when the tree under test is not this one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, NamedTuple

_FIXTURES = Path(
    os.environ.get("SF_ORACLE_FIXTURES", str(Path(__file__).resolve().parents[1] / "fixtures"))
)

#: The five-snapshot MSPDI pool every loaded stage renders.
TP4 = tuple(f"TP4_DataCenter_v{i}" for i in range(1, 6))

#: The resource-bearing goldens. ADR-0379: the TP4 pool has zero <Assignment>/<Resource>, so
#: /resources renders the same bytes at every TP4 stage and is blind to its own family. This
#: pool is the render condition that lights it.
RESOURCE_GOLDENS = ("Project2", "Project5")

#: A REAL TP4 unique id. Never 0 — ``_parse_uid`` maps 0 to "clear", so a 0 target can never be
#: set through the form (standing trap).
TARGET_UID = 22

#: Export formats the tool actually serves. NOT csv.
FMTS = ("xlsx", "docx")


class Label(NamedTuple):
    """One oracle observation: a stable name, and how to produce it."""

    name: str
    method: str
    url: str

    def key(self) -> str:
        return self.name


# --------------------------------------------------------------------------- the derived half
def _paths(app: Any) -> list[tuple[str, str]]:
    """Every (method, path) the app serves. Enumerated by METHOD + PATH, never by route class
    (ADR-0377): ``/openapi.json`` is served by a plain ``Route``, not an ``APIRoute``, and
    filtering on the class silently dropped it."""
    out: list[tuple[str, str]] = []
    for r in app.routes:
        path = getattr(r, "path", None)
        if path is None:
            continue
        for m in sorted(getattr(r, "methods", None) or ()):
            if m in ("GET", "POST"):
                out.append((m, path))
    return sorted(set(out))


def route_labels(app: Any, *, loaded: bool) -> list[Label]:
    """The self-healing half of the corpus, derived from ``app.routes``.

    ``loaded=False`` yields only the parameterless GETs — with no schedules in the session every
    ``{name}``-parameterized URL is a 404 about the same missing file, which measures the fixture
    pool rather than the code. ``loaded=True`` adds both export formats over every export route
    and binds every ``{name}`` to the newest TP4 snapshot.
    """
    labels = [Label(f"GET {p}", "GET", p) for m, p in _paths(app) if m == "GET" and "{" not in p]
    if not loaded:
        return sorted(labels)

    newest = TP4[-1]  # `{name}` keys drop the `.xml` — the session keys by stem
    for m, p in _paths(app):
        if m != "GET" or "{" not in p:
            continue
        if "{fmt}" in p:
            for fmt in FMTS:
                url = p.replace("{fmt}", fmt).replace("{name}", newest)
                labels.append(Label(f"GET {url}", "GET", url))
        else:
            url = p.replace("{name}", newest)
            labels.append(Label(f"GET {url}", "GET", url))
    return sorted(labels)


# ---------------------------------------------------------------------- the hand-authored half
#: Query-string variants that reach branches the bare route surface cannot. Each entry is
#: (label, url) and each URL is written out in full — prose is not a build recipe (ADR-0381).
#: These render only at loaded stages.
#:
#: **Every parameter here is declared by the route it targets** — checked against the signature,
#: not inferred from an ADR's prose. Twelve variants were first drafted from prose while
#: rebuilding this corpus and SIX were decoration: FastAPI ignores an undeclared query param, so
#: `/evolution?view=tiers`, `/resources?field=Status`, `/path?target=22`, `/api/sra/grid` and
#: `/sra/ssi/save` each rendered byte-identical to their bare label and reached no new code.
#: ``test_render_oracle_corpus.py`` now fails on any variant that does that.
VARIANT_LABELS: tuple[tuple[str, str], ...] = (
    # /evolution (ADR-0352's family) declares target/tier/ignore_constraints/ignore_leveling/
    # cf_a/cf_b. Three variants: the tier board, the trace-options pass, the counterfactual pair.
    ("[evo-tier] GET /evolution", "/evolution?tier=on"),
    ("[evo-options] GET /evolution", "/evolution?ignore_constraints=1&ignore_leveling=1"),
    ("[evo-counterfactual] GET /evolution", "/evolution?cf_a=1&cf_b=2"),
    # The session-wide group/filter (ADR-0104); /groups reads the raw query off the Request.
    ("[grouped] GET /groups", "/groups?field=Status&breakdown=1"),
    # /resources declares `bucket` (default "month") — the histogram's time base.
    ("[week-resources] GET /resources", "/resources?bucket=week"),
    # /cei declares `uids` — the explicit activity subset.
    ("[cei-uids] GET /cei", f"/cei?uids={TARGET_UID}"),
    # The SSI run surface (ADR-0365's family): seeded Monte-Carlo, fewer iterations.
    ("[ssi-api] GET /api/sra/ssi", "/api/sra/ssi?iterations=64&distribution=uniform"),
    # /trend declares `target` — the uid arrives on the query string, not from the session.
    ("[trend-target] GET /trend", f"/trend?target={TARGET_UID}"),
    # `scorecards_buffer_json` declares `committed`/`iterations`, and REQUIRES the first: without
    # it the bare label is a 422 that never reaches the reserve arithmetic — so the parser behind
    # it (`_parse_committed_date`) was oracle-DARK, measured by ADR-0387's probe. The date is the
    # pool's own deterministic finish, which is what makes the render non-degenerate: committed
    # confidence lands at 0.49 with non-zero P70/P80 reserves, rather than the 1.0/0.0 any date
    # past the finish returns. `iterations=100` is the route's own floor — the seeded Monte-Carlo
    # is deterministic, so this costs one cheap run per loaded stage (ADR-0374: a
    # render-conditional member needs its condition IN the oracle).
    (
        "[buffer-committed] GET /api/scorecards/buffer",
        "/api/scorecards/buffer?committed=2026-07-17&iterations=100",
    ),
    # ADR-0381: `export_path` declares `target: int = Query(...)` REQUIRED, so the bare
    # `/export/{fmt}/path/{name}` label is a 422 that never renders the export's body.
    *(
        (f"[path-export] GET /export/{f}/path", f"/export/{f}/path/{TP4[-1]}?target={TARGET_UID}")
        for f in FMTS
    ),
)


def variant_labels() -> list[Label]:
    return [Label(n, "GET", u) for n, u in VARIANT_LABELS]


# --------------------------------------------------------------------------------- the stages
#: The session states the corpus is rendered in. ``[empty]`` is the placeholder surface; the four
#: loaded stages differ in POPULATION and TARGET, which are the two render conditions the split's
#: page bodies actually branch on (ADR-0374).
STAGE_NAMES = ("[empty]", "[loaded]", "[target]", "[cleared]", "[resloaded]")


def corpus(app: Any, stage: str) -> list[Label]:
    """The label list for one stage. Deterministic and sorted — the corpus is a set, not a run."""
    if stage not in STAGE_NAMES:
        raise ValueError(f"unknown stage {stage!r}; expected one of {STAGE_NAMES}")
    loaded = stage != "[empty]"
    labels = route_labels(app, loaded=loaded)
    if loaded:
        labels += variant_labels()
    return sorted(labels)


# ---------------------------------------------------------------------------- the normalizers
class Normalizer(NamedTuple):
    """A substitution applied to every body before comparison.

    ``must_fire`` is the whole point: a normalizer that silently matches nothing is a flap
    factory (ADR-0377). :func:`normalize_all` raises when a ``must_fire`` normalizer never
    matched across the entire run, so a renamed token fails loudly instead of re-introducing
    the nondeterminism it was written to remove.
    """

    name: str
    apply: Callable[[bytes], tuple[bytes, int]]
    must_fire: bool


def _sub(pattern: bytes, repl: bytes) -> Callable[[bytes], tuple[bytes, int]]:
    rx = re.compile(pattern)
    return lambda body: rx.subn(repl, body)


#: 1. The launch token — `{hex16}.{wipe_gen}`, fresh every server process (OR-06). It has TWO
#:    spellings and the inherited recipe pinned only one: the page `<meta name=sf-launch>` and
#:    `/api/whoami`'s `"launch_token"` JSON key. Rebuilding against the page surface alone left
#:    five labels flapping (one `/api/whoami` per stage) — normalize both.
#: 2. `/api/whoami`'s pid — the server's own process id, per-process by design.
#: 3. `/api/system`'s live host telemetry — CPU/RAM/disk readings that move between renders.
#:    Normalized by VALUE with the SHAPE kept (ADR-0372): the endpoint crossed a 1-dp rounding
#:    boundary mid-run once and was blamed on a code change. Keys and nesting still compare.
NORMALIZERS: tuple[Normalizer, ...] = (
    Normalizer(
        "launch-token",
        _sub(rb'(name=sf-launch content="|"launch_token":")[0-9a-f]{16}\.\d+', rb"\1<TOKEN>"),
        True,
    ),
    Normalizer("whoami-pid", _sub(rb'("pid":\s*)\d+', rb"\1<PID>"), True),
    Normalizer("system-numbers", _sub(rb"(:\s*)-?\d+\.\d+", rb"\1<NUM>"), True),
)


def normalize_all(bodies: dict[str, bytes]) -> dict[str, bytes]:
    """Apply every normalizer to every body; raise if a ``must_fire`` one never matched."""
    fired = dict.fromkeys((n.name for n in NORMALIZERS), 0)
    out: dict[str, bytes] = {}
    for label, body in bodies.items():
        b = body
        for n in NORMALIZERS:
            # `/api/system` is the only body whose bare numbers are live telemetry; normalizing
            # floats everywhere else would blunt the oracle against the very figures under test.
            if n.name == "system-numbers" and "/api/system" not in label:
                continue
            b, hits = n.apply(b)
            fired[n.name] += hits
        out[label] = b
    dead = sorted(n.name for n in NORMALIZERS if n.must_fire and not fired[n.name])
    if dead:
        raise AssertionError(
            f"normalizer(s) {dead} matched NOTHING across {len(bodies)} bodies. A normalizer that "
            "can fail silently is a flap factory (ADR-0377) — the token it targets was renamed "
            "or removed, so fix the pattern rather than deleting the guard."
        )
    return out


# ------------------------------------------------------------------------------- the renderer
def _upload(client: Any, paths: list[Path], *, strip_title: bool) -> None:
    """Upload MSPDI snapshots. ``strip_title`` is load-bearing (ADR-0375): each TP4 file carries
    its own ``<Title>``, so untouched they group into five one-version Projects and ADR-0258's
    active population is v5 alone — every multi-version page then renders its "load two versions"
    placeholder and the oracle measures placeholders it believes are bodies."""
    files = []
    for p in paths:
        data = p.read_bytes()
        if strip_title:
            data, n = re.subn(rb"<Title>.*?</Title>", b"", data, flags=re.S)
            if not n:
                raise AssertionError(f"{p.name}: no <Title> to strip — the pool changed shape")
        files.append(("files", (p.name, data, "text/xml")))
    resp = client.post("/upload", files=files)
    if resp.status_code != 200:
        raise AssertionError(f"upload failed: {resp.status_code} {resp.text[:200]}")


def _enter_stage(client: Any, stage: str) -> None:
    """Drive the session into ``stage``. Stages are cumulative in the order of STAGE_NAMES."""
    if stage == "[empty]":
        return
    if stage == "[loaded]":
        _upload(
            client,
            [_FIXTURES / "test_projects" / f"{n}.xml" for n in TP4],
            strip_title=True,
        )
    elif stage == "[target]":
        # POST, not GET: /target is POST-only and a GET returns 405, so a setup written as a GET
        # tests nothing. Assert the 303 (standing trap).
        r = client.post("/target", data={"uid": str(TARGET_UID)}, follow_redirects=False)
        if r.status_code != 303:
            raise AssertionError(f"/target did not redirect: {r.status_code}")
    elif stage == "[cleared]":
        r = client.post("/target", data={"uid": ""}, follow_redirects=False)
        if r.status_code != 303:
            raise AssertionError(f"/target clear did not redirect: {r.status_code}")
    elif stage == "[resloaded]":
        _upload(
            client,
            [_FIXTURES / "golden" / "project2_5" / f"{n}.mspdi.xml" for n in RESOURCE_GOLDENS],
            strip_title=False,
        )


def render(verbose: bool = False) -> dict[str, bytes]:
    """Render every label at every stage. Returns ``{"<stage> <label>": normalized body}``."""
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app

    client = TestClient(create_app(SessionState()))
    raw: dict[str, bytes] = {}
    for stage in STAGE_NAMES:
        _enter_stage(client, stage)
        labels = corpus(client.app, stage)
        for lab in labels:
            resp = client.get(lab.url)
            raw[f"{stage} {lab.key()}"] = f"{resp.status_code}\n".encode() + resp.content
        if verbose:
            print(f"  {stage}: {len(labels)} labels", file=sys.stderr)
    return normalize_all(raw)


def histogram(bodies: dict[str, bytes]) -> dict[str, dict[int, int]]:
    """Per-stage status histogram — the fingerprint. A fingerprint carries its SCOPE or it is
    decoration (ADR-0377), so this is reported per stage and never as one number."""
    out: dict[str, dict[int, int]] = {s: {} for s in STAGE_NAMES}
    for label, body in bodies.items():
        stage = label.split(" ", 1)[0]
        code = int(body.split(b"\n", 1)[0])
        out[stage][code] = out[stage].get(code, 0) + 1
    return {s: dict(sorted(h.items())) for s, h in out.items()}


def _iter_out(bodies: dict[str, bytes]) -> Iterator[tuple[str, str, bytes]]:
    for label, body in sorted(bodies.items()):
        fname = hashlib.sha256(label.encode()).hexdigest()[:16] + ".bin"
        yield label, fname, body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, help="write one file per label, plus manifest.json")
    ap.add_argument("--labels", action="store_true", help="print the label list and exit")
    args = ap.parse_args()

    if args.labels:
        from schedule_forensics.web.app import SessionState, create_app

        app = create_app(SessionState())
        for stage in STAGE_NAMES:
            for lab in corpus(app, stage):
                print(f"{stage} {lab.key()}")
        return 0

    bodies = render(verbose=True)
    hist = histogram(bodies)
    print(f"labels: {len(bodies)}")
    for stage, h in hist.items():
        n = sum(h.values())
        print(f"  {stage:<12} {n:>4}  {h}")
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        manifest = {}
        for label, fname, body in _iter_out(bodies):
            (args.out / fname).write_bytes(body)
            manifest[label] = fname
        (args.out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
        print(f"wrote {len(manifest)} bodies to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""The render oracle cannot silently shrink (ADR-0382).

Nine monolith-split slices proved their extraction behaviour-preserving against a corpus that
lived only in a session scratchpad. ADR-0381 measured what that costs: rebuilt in a fresh
container the corpus came back 648 -> 592, because the half derived from ``app.routes`` heals
itself and the hand-authored half does not — and the shortfall reads as byte-identity, which is
the most convincing possible way to prove nothing.

So the corpus is committed, and these guards keep it honest:

1. **The label list is pinned.** ``tests/guards/render_oracle_labels.txt`` is the corpus, by
   name. Adding or removing a route changes it, and that is a deliberate regeneration, not a
   silent drift.
2. **No variant is decoration.** A hand-authored variant exists to reach code the bare route
   surface cannot. FastAPI ignores an undeclared query parameter, so a variant whose parameter
   the route never declares renders byte-identical to its bare label while inflating the count.
   Six of the twelve first drafted for ADR-0382 did exactly that.
3. **Every normalizer can still fire.** A normalizer that matches nothing is a flap factory
   (ADR-0377) — it removes no nondeterminism while looking like it does.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

ROOT = Path(__file__).resolve().parents[2]


def _load_corpus() -> ModuleType:
    """Import ``tests/web/oracle_corpus.py`` BY PATH; ``tests/`` is not a package.

    `from tests.web.oracle_corpus import ...` works under `python -m pytest` — which prepends the
    CWD to `sys.path` — and fails under a bare `pytest`, which does not. CI runs the bare form, so
    the package-path spelling passed locally and died in collection on three jobs at once. The
    sibling guard (`test_intake_manifest.py`, loading `tools/`) already had the answer.
    """
    path = ROOT / "tests" / "web" / "oracle_corpus.py"
    spec = importlib.util.spec_from_file_location("oracle_corpus", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["oracle_corpus"] = module  # registered before exec: NamedTuple resolves via it
    spec.loader.exec_module(module)
    return module


_oc = _load_corpus()
NORMALIZERS = _oc.NORMALIZERS
STAGE_NAMES = _oc.STAGE_NAMES
VARIANT_LABELS = _oc.VARIANT_LABELS
_enter_stage = _oc._enter_stage
corpus = _oc.corpus
histogram = _oc.histogram
normalize_all = _oc.normalize_all

LABELS = Path(__file__).parent / "render_oracle_labels.txt"

#: The part of the fingerprint the ROUTE SURFACE determines, which is the part that actually
#: survives a rebuild (ADR-0381). Carried with its scope — a fingerprint without one is
#: decoration (ADR-0377).
#: 41 -> 42 in ADR-0426: `/launch` is one new GET route that renders on an empty session
#: (its telemetry tiles read the em dash rather than refusing to paint).
#: 42 -> 43 and 2 -> 3 in ADR-0446: `/onepager` renders on an empty session; `/export/pptx/onepager`
#: refuses (422) with no list loaded rather than exporting a blank slide (its Excel/Word siblings
#: take the `{fmt}` path the corpus already fills).
#: 43 -> 44 and 3 -> 4 in ADR-0465: `/onepager-compare` renders its two empty slots on an empty
#: session; `/export/pptx/onepager-compare` refuses (422) until both lists are loaded.
EMPTY_STAGE_FINGERPRINT = {200: 44, 400: 17, 422: 4}


def _built() -> list[str]:
    app = create_app(SessionState())
    return [f"{stage} {lab.key()}" for stage in STAGE_NAMES for lab in corpus(app, stage)]


def test_the_committed_label_list_matches_what_the_builder_produces() -> None:
    """The corpus on disk IS the corpus the harness renders.

    Regenerate with::

        python tests/web/oracle_corpus.py --labels > tests/guards/render_oracle_labels.txt

    A diff here is a route change. That is fine — but it must be a deliberate regeneration in the
    same commit, so a slice can never compare a shrunken corpus against a full one and call the
    difference byte-identity.
    """
    on_disk = LABELS.read_text(encoding="utf-8").splitlines()
    built = _built()
    assert on_disk, "the committed label list is empty — the oracle guards nothing"
    missing = sorted(set(on_disk) - set(built))
    added = sorted(set(built) - set(on_disk))
    assert not (missing or added), (
        f"the render oracle drifted from its committed list: {len(missing)} label(s) gone "
        f"{missing[:5]}, {len(added)} new {added[:5]}. Regenerate the file in this commit."
    )
    assert on_disk == built, "same labels, different order — the corpus must be sorted per stage"


def test_the_empty_stage_fingerprint_is_the_one_the_route_surface_determines() -> None:
    """`[empty]` is the route surface's own histogram — the number every rebuild reproduced."""
    client = TestClient(create_app(SessionState()))
    bodies = {
        f"[empty] {lab.key()}": f"{client.get(lab.url).status_code}\n".encode()
        for lab in corpus(client.app, "[empty]")
    }
    assert histogram(bodies)["[empty]"] == EMPTY_STAGE_FINGERPRINT


@pytest.mark.parametrize("label,url", VARIANT_LABELS, ids=[n for n, _ in VARIANT_LABELS])
def test_no_hand_authored_variant_is_decoration(label: str, url: str) -> None:
    """A variant must render something its bare route does not.

    This is the guard ADR-0382 owed the corpus. The variants are the half of the oracle that
    cannot heal itself, and a variant that reaches no new code is worse than a missing one: it
    keeps the label count looking healthy while the coverage is gone.
    """
    client = TestClient(create_app(SessionState()))
    _enter_stage(client, "[loaded]")
    variant, bare = client.get(url), client.get(url.split("?")[0])
    assert variant.content != bare.content, (
        f"{label} renders byte-identical to {url.split('?')[0]} — the route does not declare the "
        "parameter this variant passes, so FastAPI ignored it and the label reaches no new code. "
        "Check the route signature and pass a parameter it actually declares."
    )


@pytest.mark.parametrize("norm", NORMALIZERS, ids=[n.name for n in NORMALIZERS])
def test_a_normalizer_that_matches_nothing_fails_loudly(norm: object) -> None:
    """`normalize_all` raises when a must-fire normalizer never matched.

    Without this the oracle degrades in the worst direction: the token drifts, the substitution
    stops applying, and the corpus starts flapping on content nobody is testing.
    """
    with pytest.raises(AssertionError, match="matched NOTHING"):
        normalize_all({"[empty] GET /healthz": b"200\nnothing to normalize here"})

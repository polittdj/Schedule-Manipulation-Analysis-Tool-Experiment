"""The sovereignty banner is OBSERVED, not config-derived (DoD 001b; Law 1 applied to the claim).

Before this guard, ``route_backend`` returned the literal local-only Banner for whatever object
arrived through its ``ollama``/``openai`` parameters (no locality inspection), the rendered page
banner came from configuration alone (``banner_for`` read only the config), ``AIBackend.is_local``
was a hardcoded class constant nothing branched on, and two exported exhibits printed
unconditional locality assurances. Measured on the pre-fix tree: a fake with ``is_local=False``
routed on both paths under the banner "Local-only — no data leaves this machine.", and the page
rendered that banner with the same fake sitting in the session's routing cache.

The contract pinned here, layer by layer:

* ``banner_for_backend`` — the ONE derivation: a backend is local only if it itself proves it
  (``is_local`` literally ``True``; missing/falsy is presumed NON-local, fail closed).
* ``route_backend`` — every returned Banner is that derivation over the backend actually chosen.
* ``banner_for`` — constructs the candidates the config would route through (``ai.factory``)
  and derives from them; cloud intent still warns while routing falls closed (§0.2).
* ``_observed_banner`` — the page-level chokepoint: candidates AND the session's actually-routed
  cached backend both get a veto; every absolute on-page/in-export assurance rides it.
* The concrete HTTP backends carry ``is_local`` as an INSTANCE value derived from the loopback
  validator's verdict on the actual endpoint — never as a class constant.

Per the ADR-0394 lesson, the literal is pinned (test-side constant, byte-compared, and required
to remain the i18n catalog key so the four translations stay reachable) AND the behaviour is
swept — neither alone survives a bypass added above the other.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.ai import factory
from schedule_forensics.ai.backend import (
    AIConfig,
    Classification,
    banner_for,
    banner_for_backend,
    route_backend,
)
from schedule_forensics.ai.null import NullBackend
from schedule_forensics.ai.ollama import OllamaBackend
from schedule_forensics.ai.openai_compat import OpenAICompatBackend
from schedule_forensics.web.app import SessionState, create_app

#: Test-side literal, deliberately NEVER imported from the module under test (an oracle that
#: reads the value it judges cannot refute anything — ADR-0394).
LOCAL_LITERAL = "Local-only — no data leaves this machine."

#: A FICTIONAL non-local endpoint standing in for the real-world approved-gateway scenario this
#: guard exists for (see docs/PLAN/APPROVED-GATEWAY-INTEGRATION.md). Deliberately not the real
#: hostname: the 2026-08-13 audit's DISC-01 finding is that the real strings are over-disclosed,
#: and a document (or test) that exists because of a disclosure must not repeat the disclosure.
GATEWAY = "https://gateway.agency.example"


class _NonLocalFake:
    """An HONEST non-local backend — the shape a future ``ai/gateway.py`` would have."""

    name = "gateway-fake"
    is_local = False
    endpoint = GATEWAY

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("remote-model",)

    def pull_model(self, model: str) -> None: ...

    def generate(self, prompt: str) -> str:
        return prompt


class _NoLocalityFake:
    """A backend that cannot PROVE locality — no ``is_local`` attribute at all."""

    name = "mystery"
    endpoint = "http://somewhere.invalid:9999"

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ()

    def pull_model(self, model: str) -> None: ...

    def generate(self, prompt: str) -> str:
        return prompt


def _up(url: str, data: bytes | None, timeout: float) -> str:
    return '{"models": [], "data": []}'


# --- route level: the Banner is derived from the backend actually chosen -----------------


def test_route_backend_refuses_the_local_banner_for_a_nonlocal_ollama_path_backend() -> None:
    cfg = AIConfig(backend="ollama")  # CLASSIFIED default — the worst case
    backend, banner = route_backend(cfg, null_backend=NullBackend(), ollama_backend=_NonLocalFake())
    assert backend.name == "gateway-fake"  # routing itself is 001c's problem, not this guard's
    assert banner.cloud_active is True
    assert LOCAL_LITERAL not in banner.text
    assert GATEWAY in banner.text  # the warning must NAME the endpoint


def test_route_backend_refuses_the_local_banner_for_a_nonlocal_openai_path_backend() -> None:
    cfg = AIConfig(backend="openai")
    backend, banner = route_backend(cfg, null_backend=NullBackend(), openai_backend=_NonLocalFake())
    assert backend.name == "gateway-fake"
    assert banner.cloud_active is True and LOCAL_LITERAL not in banner.text
    assert GATEWAY in banner.text


def test_a_backend_that_cannot_prove_locality_is_presumed_nonlocal() -> None:
    # fail-closed presumption: a MISSING is_local must read as non-local, never as local
    banner = banner_for_backend(_NoLocalityFake(), AIConfig(backend="ollama"))
    assert banner.cloud_active is True and LOCAL_LITERAL not in banner.text
    assert "somewhere.invalid:9999" in banner.text


def test_a_classified_project_with_a_nonlocal_backend_is_named_for_what_it_is() -> None:
    banner = banner_for_backend(_NonLocalFake(), AIConfig(backend="ollama"))
    assert "CLASSIFIED" in banner.text and GATEWAY in banner.text
    assert "Do not use with CUI." in banner.text


def test_route_backend_local_paths_still_produce_the_exact_local_literal() -> None:
    # behaviour AND literal: a reachable loopback backend earns exactly the pinned sentence
    cfg = AIConfig(backend="ollama")
    _backend, banner = route_backend(
        cfg, null_backend=NullBackend(), ollama_backend=OllamaBackend(opener=_up)
    )
    assert banner.text == LOCAL_LITERAL and banner.cloud_active is False
    _b2, banner2 = route_backend(
        AIConfig(backend="openai"),
        null_backend=NullBackend(),
        openai_backend=OpenAICompatBackend(opener=_up),
    )
    assert banner2.text == LOCAL_LITERAL
    _b3, banner3 = route_backend(AIConfig(backend="null"), null_backend=NullBackend())
    assert banner3.text == LOCAL_LITERAL


def test_route_banner_agrees_with_the_config_banner_for_every_local_state() -> None:
    """The router's Banner and the page's config-level derivation may never disagree on a
    reachable local state — a divergence here is how the pre-fix dead-code Banner rotted."""
    for cfg in (
        AIConfig(backend="null"),
        AIConfig(backend="ollama"),  # constructor-built candidate, router gets a down server
        AIConfig(backend="openai"),
        AIConfig(classification=Classification.CLASSIFIED, backend="cloud"),
    ):
        _backend, routed = route_backend(cfg, null_backend=NullBackend())
        assert routed.text == banner_for(cfg).text == LOCAL_LITERAL


# --- config level: banner_for constructs and observes the session's candidates -----------


def test_banner_for_local_configs_yield_the_exact_local_literal() -> None:
    for cfg in (AIConfig(), AIConfig(backend="openai"), AIConfig(backend="null")):
        banner = banner_for(cfg)
        assert banner.text == LOCAL_LITERAL and banner.cloud_active is False


def test_banner_for_unclassified_cloud_intent_still_warns_with_no_backend_wired() -> None:
    # §0.2 preserved: the SETTING could egress the moment a backend is wired, so it must warn
    # even though routing currently falls closed to Null and nothing can actually send.
    cfg = AIConfig(
        classification=Classification.UNCLASSIFIED, backend="cloud", endpoint="https://api.x.gov"
    )
    banner = banner_for(cfg)
    assert banner.cloud_active is True and "https://api.x.gov" in banner.text
    assert "UNCLASSIFIED" in banner.text


def test_banner_for_warns_when_the_primary_candidate_is_nonlocal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(factory, "ollama_or_none", lambda cfg: _NonLocalFake())
    banner = banner_for(AIConfig(backend="ollama"))
    assert banner.cloud_active is True and LOCAL_LITERAL not in banner.text
    assert GATEWAY in banner.text


def test_banner_for_warns_when_the_second_candidate_is_nonlocal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # the cross-check second model receives every prompt too — it gets the same veto
    monkeypatch.setattr(factory, "second_or_none", lambda cfg: _NonLocalFake())
    banner = banner_for(AIConfig(backend="null", second_backend="ollama"))
    assert banner.cloud_active is True and GATEWAY in banner.text


def test_the_local_literal_is_still_the_i18n_catalog_key() -> None:
    """The four shipped translations key on the EXACT banner sentence; rewording the literal
    without re-keying the catalog would silently strand es/fr/de/pt on the English fallback."""
    from schedule_forensics.web.i18n import _TERMS

    assert LOCAL_LITERAL in _TERMS
    assert set(_TERMS[LOCAL_LITERAL]) == {"es", "fr", "de", "pt"}


# --- instance level: is_local is a measurement, not a label ------------------------------


def test_is_local_is_instance_derived_not_a_class_constant() -> None:
    """The concrete HTTP backends must not carry a class-level ``is_local``: the value is the
    loopback validator's verdict on the ACTUAL endpoint, recorded at construction. A class
    constant is an assertion that survives any endpoint; a measurement does not."""
    assert "is_local" not in vars(OllamaBackend)
    assert "is_local" not in vars(OpenAICompatBackend)
    ob = OllamaBackend(opener=_up)
    oc = OpenAICompatBackend(opener=_up)
    assert ob.is_local is True and "is_local" in vars(ob)
    assert oc.is_local is True and "is_local" in vars(oc)
    # Null holds no endpoint and no transport — local by construction is honest for it.
    assert NullBackend().is_local is True


# --- page level: every absolute assurance rides the observed derivation ------------------


def _client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


def test_the_local_default_page_shows_the_assurances() -> None:
    body = _client(SessionState()).get("/").text
    assert LOCAL_LITERAL in body  # the persistent banner
    assert "no schedule content ever leaves this machine" in body  # CUI drawer
    assert "entirely on your machine" in body  # hero
    assert "nothing leaves this computer" in body  # hero tail
    assert "nothing you load ever leaves this machine" in body  # empty-state takeaway


def test_page_banner_goes_red_when_the_primary_candidate_is_nonlocal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """THE 001b acceptance test: route a non-local fake and the page must change."""
    monkeypatch.setattr(factory, "ollama_or_none", lambda cfg: _NonLocalFake())
    body = _client(SessionState()).get("/").text
    assert LOCAL_LITERAL not in body
    assert GATEWAY in body  # the warning names the endpoint, on the page
    # every absolute assurance is withdrawn together, not just the banner div:
    assert "no schedule content ever leaves this machine" not in body
    assert "entirely on your machine" not in body
    assert "nothing leaves this computer" not in body
    assert "nothing you load ever leaves this machine" not in body
    # and the drawer states the split honestly
    assert "schedule content sent to the AI leaves this machine" in body


def test_page_banner_warns_when_a_nonlocal_backend_sits_in_the_routing_cache() -> None:
    """A non-local object that reached the session's routing cache by ANY path — however it
    was injected — can never sit behind a local-only banner."""
    state = SessionState()
    state.backend_cache = (state.ai_config, time.monotonic(), _NonLocalFake())
    body = _client(state).get("/").text
    assert LOCAL_LITERAL not in body and GATEWAY in body


def test_settings_page_tip_follows_the_observed_banner(monkeypatch: pytest.MonkeyPatch) -> None:
    state = SessionState()
    local_tip = "nothing ever leaves this machine"
    assert local_tip in _client(state).get("/settings").text
    monkeypatch.setattr(factory, "ollama_or_none", lambda cfg: _NonLocalFake())
    body = _client(state).get("/settings").text
    assert local_tip not in body
    assert "prompts sent to the AI leave this machine" in body


# --- exports: the exhibits' printed assurances follow the same derivation ----------------


def test_brief_blocks_requires_and_honors_the_locality_verdict() -> None:
    import datetime as dt
    import inspect

    from schedule_forensics.ai.brief import DiagnosticBrief, brief_blocks

    # the parameter is REQUIRED evidence — no default may quietly assume local
    param = inspect.signature(brief_blocks).parameters["ai_is_local"]
    assert param.default is inspect.Parameter.empty and param.kind is param.KEYWORD_ONLY

    brief = DiagnosticBrief(
        title="Diagnostic Brief", generated_on=dt.date(2026, 8, 13), sections=()
    )
    local = " ".join(getattr(b, "text", "") for b in brief_blocks(brief, ai_is_local=True))
    remote = " ".join(getattr(b, "text", "") for b in brief_blocks(brief, ai_is_local=False))
    assert "Generated locally by POLARIS" in local
    assert "Generated locally by POLARIS" not in remote
    assert "non-local endpoint" in remote  # the disclosure replaces the assurance
    assert "engine-computed on this machine" in remote  # without overclaiming the figures


def test_sra_report_locality_sentence_follows_the_observed_banner() -> None:
    from pathlib import Path

    from schedule_forensics.engine.sra import SSIResult
    from schedule_forensics.importers.mspdi import parse_mspdi
    from schedule_forensics.web.sra import _sra_report_blocks

    golden = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "golden"
        / "project2_5"
        / "Project5.mspdi.xml"
    )
    sch = parse_mspdi(golden)
    # a minimal synthetic result (the same shape tests/web/test_sra_report.py builds) — the
    # guard measures the methodology SENTENCE, not the distribution
    result = SSIResult(
        iterations=100,
        seed=1,
        target_uid=None,
        distribution="triangular",
        occurrence_mode="random_each",
        correlation=0.0,
        used_risks=False,
        deterministic_finish=480,
        deterministic_percentile=1.0,
        p10=480,
        p50=480,
        p80=480,
        p90=480,
        mean=480.0,
        std_days=0.0,
        deterministic_finish_date="2027-12-03",
        p10_date="2027-11-20",
        p50_date="2027-12-01",
        p80_date="2027-12-10",
        p90_date="2027-12-20",
        mean_date="2027-12-05",
        cdf=(),
        histogram=(),
        s_curve=(),
        finish_hist=(),
        risks=(),
    )
    state = SessionState()
    local_txt = " ".join(getattr(b, "text", "") for b in _sra_report_blocks(state, sch, result, ()))
    assert "All computation is local and offline" in local_txt

    state.backend_cache = (state.ai_config, time.monotonic(), _NonLocalFake())
    remote_txt = " ".join(
        getattr(b, "text", "") for b in _sra_report_blocks(state, sch, result, ())
    )
    assert "All computation is local and offline" not in remote_txt
    assert "non-local endpoint" in remote_txt
    assert "CUI marking in its header and footer" in remote_txt  # the marking never drops

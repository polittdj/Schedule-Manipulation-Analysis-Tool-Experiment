"""Language (EN/ES/FR/DE/PT) selection — the i18n catalog, /language switch, and /api/translate."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web import i18n
from schedule_forensics.web.app import SessionState, _ai_translate, create_app


def test_catalog_translate_and_fallback() -> None:
    assert i18n.translate("Dashboard", "es") == "Panel"
    assert i18n.translate("Trend", "es") == "Tendencia"
    # English (source) is a no-op; an uncatalogued term falls back to itself
    assert i18n.translate("Dashboard", "en") == "Dashboard"
    assert i18n.translate("Totally Unmapped Task", "es") == "Totally Unmapped Task"
    assert i18n.normalize("zz") == "en" and i18n.normalize("es") == "es"
    assert set(i18n.LANGUAGES) == {"en", "es", "fr", "de", "pt"}


def test_french_and_german_catalogs() -> None:
    assert i18n.translate("Dashboard", "fr") == "Tableau de bord"
    assert i18n.translate("Dashboard", "de") == "Übersicht"
    assert i18n.translate("Critical", "fr") == "Critique"
    assert i18n.translate("Critical", "de") == "Kritisch"
    # an unknown term still falls back to the source in every language
    assert i18n.translate("Nope", "fr") == "Nope" and i18n.translate("Nope", "de") == "Nope"


def test_portuguese_catalog() -> None:
    assert i18n.normalize("pt") == "pt"
    assert i18n.translate("Dashboard", "pt") == "Painel"
    assert i18n.translate("Risk Analysis", "pt") == "Análise de riscos"
    assert i18n.translate("Driving Path", "pt") == "Caminho determinante"
    assert i18n.translate("Critical", "pt") == "Crítico"
    assert i18n.translate("Nope", "pt") == "Nope"  # unknown -> source fallback


def test_all_catalogs_cover_the_same_term_set() -> None:
    # the _TERMS table keeps EVERY non-English language aligned to one key set (incl. Portuguese)
    keysets = {lang: set(i18n.catalog_for(lang)) for lang in ("es", "fr", "de", "pt")}
    assert keysets["es"] == keysets["fr"] == keysets["de"] == keysets["pt"]
    assert len(keysets["es"]) > 100  # comprehensive core UI coverage (nav + page titles + controls)


def test_catalog_covers_ui_chrome_and_metric_terms() -> None:
    # operator: translate the WHOLE UI offline, including domain/metric terms (the AI fallback only
    # covers the long-tail prose). A representative sample of the expansion must be present.
    es = i18n.catalog_for("es")
    assert len(es) >= 180  # the expanded offline dictionary (was ~117)
    for term in (
        "Hard Constraints",
        "Negative Float",
        "Missing Logic",
        "total float",
        "Severity",
        "Why it matters:",
        "Threshold:",
        "Realism",
        "Show driving path",
        "Forecast finish",
    ):
        assert term in es, term
    # metric names are localized (operator chose "translate everything")
    assert es["Negative Float"] == "Holgura negativa"
    assert i18n.catalog_for("de")["Hard Constraints"] == "Harte Einschränkungen"


@pytest.fixture
def state() -> SessionState:
    return SessionState()


@pytest.fixture
def client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


def test_default_page_is_english_with_a_selector(client: TestClient) -> None:
    page = client.get("/").text
    assert '<html lang="en"' in page
    assert "/language" in page and "name=lang" in page  # the selector
    assert "/static/translate.js" in page
    assert "Español" in page  # the endonym option is shown


def test_language_switch_persists_and_returns_to_referer(
    client: TestClient, state: SessionState
) -> None:
    r = client.post(
        "/language",
        data={"lang": "es"},
        headers={"referer": "http://testserver/trend"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and r.headers["location"] == "/trend"
    assert state.language == "es"
    page = client.get("/").text
    assert '<html lang="es"' in page
    assert '"Panel"' in page  # the catalog is embedded for the client when not English


def test_portuguese_is_offered_selected_and_embedded(client: TestClient) -> None:
    page = client.get("/").text
    assert "Português" in page  # the endonym option is shown
    client.post("/language", data={"lang": "pt"}, follow_redirects=False)
    page = client.get("/").text
    assert '<html lang="pt"' in page
    assert '<option value="pt" selected>' in page  # the current language is marked selected
    assert '"Painel"' in page  # the pt catalog is embedded for the client


def test_language_can_switch_back_and_forth(client: TestClient, state: SessionState) -> None:
    """Operator bug: once changed, the UI would not switch again. Each switch must persist and the
    server must always re-render English (the client translates), so any sequence works."""
    for lang, html_lang in [("es", "es"), ("fr", "fr"), ("pt", "pt"), ("en", "en"), ("de", "de")]:
        client.post("/language", data={"lang": lang}, follow_redirects=False)
        assert state.language == html_lang
        page = client.get("/").text
        assert f'<html lang="{html_lang}"' in page
        assert f'<option value="{lang}" selected>' in page
        # the body is always rendered in English (source) — the client does the translating
        assert ">Dashboard</a>" in page


def test_translate_js_is_non_destructive_and_covers_attributes(client: TestClient) -> None:
    js = client.get("/static/translate.js").text
    assert "__sfSrc" in js  # remembers each node's ORIGINAL English source (non-destructive)
    assert "pageshow" in js  # re-renders a bfcache-restored page
    assert "placeholder" in js and "aria-label" in js  # attribute coverage
    assert "handleOption" in js  # <option> label coverage


def test_translate_api_portuguese_catalog_hit(client: TestClient) -> None:
    out = client.post(
        "/api/translate", json={"lang": "pt", "texts": ["Dashboard", "Risk Analysis"]}
    ).json()["translations"]
    assert out["Dashboard"] == "Painel" and out["Risk Analysis"] == "Análise de riscos"


def test_language_switch_rejects_offsite_referer(client: TestClient) -> None:
    r = client.post(
        "/language",
        data={"lang": "es"},
        headers={"referer": "https://evil.example.com/x"},
        follow_redirects=False,
    )
    # only the path is honoured (host stripped) — no open redirect
    assert r.headers["location"] == "/x"


def test_unknown_language_falls_back_to_english(client: TestClient, state: SessionState) -> None:
    client.post("/language", data={"lang": "zz"}, follow_redirects=False)
    assert state.language == "en"


def test_translate_api_catalog_hit_and_source_fallback(client: TestClient) -> None:
    # no model in tests -> catalog terms translate, dynamic text falls back (absent from the map)
    out = client.post(
        "/api/translate", json={"lang": "es", "texts": ["Dashboard", "Pour concrete slab 12"]}
    ).json()["translations"]
    assert out["Dashboard"] == "Panel"
    assert "Pour concrete slab 12" not in out  # no model -> client keeps the source text
    # English / bad input -> nothing to translate
    assert client.post("/api/translate", json={"lang": "en", "texts": ["x"]}).json() == {
        "translations": {}
    }
    assert client.post("/api/translate", json={"lang": "es", "texts": "nope"}).json() == {
        "translations": {}
    }


class _FakeBackend:
    name = "fake"

    def generate(self, prompt: str) -> str:  # numbered, tab-delimited round-trip
        # echo a deterministic translation for each numbered input line
        lines = [ln for ln in prompt.splitlines() if "\t" in ln and ln[0].isdigit()]
        return "\n".join(f"{ln.split(chr(9))[0]}\t<es>{ln.split(chr(9), 1)[1]}" for ln in lines)


def test_ai_translate_parses_numbered_output() -> None:
    out = _ai_translate(["Alpha", "Beta"], "es", _FakeBackend())  # type: ignore[arg-type]
    assert out == {"Alpha": "<es>Alpha", "Beta": "<es>Beta"}


def test_ai_translate_null_backend_returns_nothing() -> None:
    from schedule_forensics.ai.null import NullBackend

    assert _ai_translate(["Alpha"], "es", NullBackend()) == {}

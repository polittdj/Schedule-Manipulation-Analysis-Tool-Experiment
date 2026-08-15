"""Persistent AI settings (ADR-0404): armed once, armed on every launch.

Operator directive (2026-08-15): *"I do not want to have to put in the NASA API KEY everytime
I open the program. I want it to work when I click on the desktop icon. Super simple."* That
supersedes ADR-0402's per-launch-acknowledgment posture: the whole AI configuration —
backend, endpoints, model, the gateway acknowledgment, and the gateway key — now persists on
the machine and loads at launch.

The contract pinned here:

* **Round-trip fidelity** — save then load reproduces the config, key included.
* **Load is a trust boundary** — the file is operator-editable state, so loading re-applies
  the same sanitizers as the settings POST: a non-allowlisted gateway endpoint clears to ""
  (a hand-edited file must never smuggle a destination past the allowlist), non-loopback
  local endpoints fall back to defaults, enums fall back to safe values, the timeout clamps.
* **Fail-soft on absence/corruption** — missing or garbage files yield pure defaults.
* **The key is never plaintext at rest where protection exists** — on Windows it is wrapped
  by DPAPI (user scope) into `gateway_api_key_dpapi`; if protection FAILS the key is simply
  not persisted (fail closed on the credential, fail soft on convenience). On POSIX it is
  stored under `gateway_api_key_plain` in a 0600 file — honestly named, and equivalent in
  protection class to the user-scope environment variable alternative.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from schedule_forensics.ai import config_store
from schedule_forensics.ai.backend import AIConfig, Classification

ENDPOINT = "https://proxy.fast.luna.nasa.gov"


def _armed(key: str = "sk-nasa-hub-KEY") -> AIConfig:
    return AIConfig(
        classification=Classification.CLASSIFIED,
        backend="gateway",
        model="claude-opus-4.8-thinking-itar",
        gateway_endpoint=ENDPOINT,
        gateway_approved=True,
        gateway_api_key=key,
        gen_timeout=1200.0,
    )


def test_round_trip_reproduces_the_config_key_included(tmp_path: Path) -> None:
    path = tmp_path / "ai-settings.json"
    config_store.save_ai_config(_armed(), path)
    assert config_store.load_ai_config(path) == _armed()


def test_missing_and_corrupt_files_yield_pure_defaults(tmp_path: Path) -> None:
    assert config_store.load_ai_config(tmp_path / "absent.json") == AIConfig()
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert config_store.load_ai_config(bad) == AIConfig()
    wrong_shape = tmp_path / "shape.json"
    wrong_shape.write_text(json.dumps(["a", "list"]), encoding="utf-8")
    assert config_store.load_ai_config(wrong_shape) == AIConfig()


def test_loading_reapplies_every_boundary_sanitizer(tmp_path: Path) -> None:
    """A hand-edited settings file gets the same distrust as a POSTed form."""
    path = tmp_path / "ai-settings.json"
    config_store.save_ai_config(_armed(), path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["gateway_endpoint"] = "https://evil.example.com"  # off the allowlist
    doc["endpoint"] = "http://evil.example.com:11434"  # non-loopback
    doc["openai_endpoint"] = "http://10.0.0.5:1234"  # non-loopback
    doc["qa_mode"] = "yolo"
    doc["second_backend"] = "gateway"  # never a valid second backend
    doc["classification"] = "TOP-SECRET-NONSENSE"
    doc["gen_timeout"] = 999999
    path.write_text(json.dumps(doc), encoding="utf-8")
    cfg = config_store.load_ai_config(path)
    assert cfg.gateway_endpoint == ""  # the allowlist holds at the load boundary too
    assert cfg.endpoint == "http://127.0.0.1:11434"
    assert cfg.openai_endpoint == "http://127.0.0.1:1234"
    assert cfg.qa_mode == "annotate"
    assert cfg.second_backend == "none"
    assert cfg.classification is Classification.CLASSIFIED
    assert cfg.gen_timeout == 3600.0


def test_the_key_is_never_plaintext_in_the_file_when_protection_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With a working protector (the Windows DPAPI path, simulated), the raw key must not
    appear anywhere in the file bytes; loading unprotects it back."""
    monkeypatch.setattr(config_store, "_protect_key", lambda raw: b"WRAPPED:" + raw[::-1])
    monkeypatch.setattr(
        config_store,
        "_unprotect_key",
        lambda blob: blob.removeprefix(b"WRAPPED:")[::-1],
    )
    monkeypatch.setattr(config_store, "_KEY_FIELD", "gateway_api_key_dpapi")
    path = tmp_path / "ai-settings.json"
    config_store.save_ai_config(_armed("sk-SECRET"), path)
    raw = path.read_text(encoding="utf-8")
    assert "sk-SECRET" not in raw and "gateway_api_key_dpapi" in raw
    assert config_store.load_ai_config(path).gateway_api_key == "sk-SECRET"


def test_a_failing_protector_omits_the_key_and_keeps_everything_else(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail closed on the credential, fail soft on convenience: protection breakage must
    never downgrade the key to plaintext behind the operator's back."""

    def _boom(raw: bytes) -> bytes:
        raise OSError("DPAPI unavailable")

    monkeypatch.setattr(config_store, "_protect_key", _boom)
    monkeypatch.setattr(config_store, "_KEY_FIELD", "gateway_api_key_dpapi")
    path = tmp_path / "ai-settings.json"
    config_store.save_ai_config(_armed("sk-SECRET"), path)
    raw = path.read_text(encoding="utf-8")
    assert "sk-SECRET" not in raw
    loaded = config_store.load_ai_config(path)
    assert loaded.gateway_api_key == ""  # the key did not persist…
    assert loaded.gateway_endpoint == ENDPOINT and loaded.gateway_approved is True  # …the rest did


def test_the_posix_plain_path_is_owner_only_and_honestly_named(tmp_path: Path) -> None:
    """Where no OS protector exists the storage is named for what it is and the file is
    0600 — the same protection class as the SF_GATEWAY_API_KEY user environment variable."""
    if config_store._KEY_FIELD != "gateway_api_key_plain":
        pytest.skip("platform has an OS key protector; the plain path is not in use")
    path = tmp_path / "ai-settings.json"
    config_store.save_ai_config(_armed("sk-SECRET"), path)
    assert json.loads(path.read_text(encoding="utf-8"))["gateway_api_key_plain"]
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600, oct(mode)


def test_default_path_honors_the_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SF_SETTINGS_DIR", "/somewhere/state")
    assert config_store.default_settings_path() == Path("/somewhere/state") / "ai-settings.json"
    monkeypatch.delenv("SF_SETTINGS_DIR")
    assert config_store.default_settings_path().name == "ai-settings.json"
    assert ".cache" not in str(config_store.default_settings_path())  # never the wiped cache dir

"""Network-egress guard (§7 / §6.G): the runtime must stay local-only.

This is the §7 acceptance check — it fails if a forbidden HTTP/cloud client
could reach the shipped runtime, or if a cloud SDK is importable.
"""

from __future__ import annotations

import pytest

from schedule_forensics import net_guard


def test_no_forbidden_runtime_dependencies() -> None:
    # The shipped package declares no remote-HTTP / cloud-SDK runtime dependency.
    assert net_guard.forbidden_runtime_dependencies() == set()


def test_no_cloud_sdks_importable() -> None:
    assert net_guard.importable_cloud_sdks() == set()


def test_assert_local_only_passes_in_clean_runtime() -> None:
    net_guard.assert_local_only()  # must not raise


def test_assert_local_only_trips_on_forbidden_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Simulate a forbidden HTTP client sneaking into the runtime dependency set.
    monkeypatch.setattr(net_guard, "runtime_requirement_names", lambda: {"requests", "pydantic"})
    assert net_guard.forbidden_runtime_dependencies() == {"requests"}
    with pytest.raises(net_guard.CUIEgressError, match="requests"):
        net_guard.assert_local_only()


def test_assert_local_only_trips_on_importable_cloud_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(net_guard, "importable_cloud_sdks", lambda: {"openai"})
    with pytest.raises(net_guard.CUIEgressError, match="openai"):
        net_guard.assert_local_only()


def test_runtime_requirement_names_parses_base_deps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Base runtime deps are kept; ``extra``-gated (dev) requirements are dropped.
    monkeypatch.setattr(
        net_guard.importlib.metadata,
        "requires",
        lambda _dist: ["Pydantic>=2.0", "requests", 'pytest>=8; extra == "dev"'],
    )
    assert net_guard.runtime_requirement_names() == {"pydantic", "requests"}
    assert net_guard.forbidden_runtime_dependencies() == {"requests"}


def test_runtime_requirement_names_skips_a_blank_requirement_spec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A requirement whose name portion is blank (strips to "") yields no regex match and is
    # silently skipped (net_guard.py branch 119->114) — a real dep on the same list is still kept.
    monkeypatch.setattr(
        net_guard.importlib.metadata,
        "requires",
        lambda _dist: ["   ", "pydantic>=2.0"],  # blank spec → no match → skipped
    )
    assert net_guard.runtime_requirement_names() == {"pydantic"}


def test_runtime_requirement_names_handles_no_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(net_guard.importlib.metadata, "requires", lambda _dist: None)
    assert net_guard.runtime_requirement_names() == set()


def test_importable_cloud_sdks_detects_present_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Simulate a cloud SDK being installed into the runtime.
    real_find_spec = net_guard.importlib.util.find_spec

    def fake(name: str) -> object | None:
        if name == "openai":
            return object()  # truthy spec → importable
        if name == "boto3":
            raise ValueError("bad parent package")  # exercise the except branch
        return real_find_spec(name) if name not in net_guard.FORBIDDEN_CLOUD_MODULES else None

    monkeypatch.setattr(net_guard.importlib.util, "find_spec", fake)
    assert net_guard.importable_cloud_sdks() == {"openai"}


@pytest.mark.parametrize(
    "host",
    ["127.0.0.1", "127.0.0.5", "localhost", "LOCALHOST", "::1", "[::1]", " 127.0.0.1 "],
)
def test_loopback_hosts_allowed(host: str) -> None:
    assert net_guard.is_loopback_host(host) is True


@pytest.mark.parametrize(
    "host",
    ["8.8.8.8", "example.com", "10.0.0.5", "169.254.1.1", "0.0.0.0", "", "::"],
)
def test_remote_or_unknown_hosts_rejected(host: str) -> None:
    assert net_guard.is_loopback_host(host) is False

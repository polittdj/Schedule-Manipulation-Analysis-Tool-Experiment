"""Network-egress guard — Law 1 (data sovereignty / CUI) enforcement.

The shipped tool processes Controlled Unclassified Information and must transfer
nothing off the local machine (``AUTONOMOUS-BUILD-PROMPT.md`` §0, §6.G). This
module is the fail-closed guard behind that guarantee:

* It declares the set of third-party distributions and cloud-SDK modules that
  must never appear in the *runtime* dependency closure, because their sole
  purpose is to move data to a remote host.
* :func:`assert_local_only` raises :class:`CUIEgressError` if any forbidden
  distribution is a declared runtime dependency, or if any forbidden cloud SDK
  is importable in the current interpreter. Application entry points call it on
  startup; ``tests/guards/test_egress.py`` is the §7 acceptance check.

The check is deliberately scoped to the package's *declared runtime
dependencies*, not to "is module X importable in this venv". Build-time tools
such as ``pip-audit`` legitimately pull in ``requests`` / ``urllib3`` in the dev
environment, but those must never become runtime dependencies of the shipped
package. Matching the declared runtime requirements keeps the guard both
meaningful and free of false positives. The cloud-SDK import check uses only
modules that are never transitive dependencies of the build toolchain, so it
stays a true signal that nobody installed a cloud backend into the runtime.

Reaching the local Ollama backend (M12) uses a loopback-only HTTP client;
:func:`is_loopback_host` is the predicate that client uses so a CUI project can
never be pointed at a remote address.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import re
from ipaddress import ip_address

#: Distribution name of this package (``importlib.metadata`` key).
DIST_NAME = "schedule-forensics"

#: Distributions whose purpose is remote I/O or cloud-model access. None of these
#: may ever be a *runtime* dependency of the shipped tool (dev-only transitive use
#: by the build toolchain is fine and is intentionally not matched). PEP 503
#: normalized.
FORBIDDEN_RUNTIME_DISTRIBUTIONS: frozenset[str] = frozenset(
    {
        # general remote HTTP / networking clients
        "requests",
        "httpx",
        "aiohttp",
        "urllib3",
        "httpcore",
        "websocket-client",
        "websockets",
        "pycurl",
        "tornado",
        "treq",
        "grpcio",
        # cloud LLM / provider SDKs
        "openai",
        "anthropic",
        "cohere",
        "mistralai",
        "replicate",
        "google-generativeai",
        "google-cloud-aiplatform",
        "vertexai",
        "boto3",
        "botocore",
        "azure-ai-inference",
        "azure-identity",
        "huggingface-hub",
    }
)

#: Cloud-provider SDK *top-level modules*. These are never transitive
#: dependencies of the build toolchain (ruff/mypy/pytest/bandit/pip-audit), so
#: asserting they are not importable is a meaningful, false-positive-free check
#: that nobody installed a cloud backend into the runtime environment.
FORBIDDEN_CLOUD_MODULES: frozenset[str] = frozenset(
    {
        "openai",
        "anthropic",
        "cohere",
        "mistralai",
        "replicate",
        "boto3",
        "botocore",
        "vertexai",
        "google.generativeai",
        "google.cloud.aiplatform",
    }
)

_LOOPBACK_HOSTNAMES: frozenset[str] = frozenset({"localhost", "ip6-localhost"})
_NAME_RE = re.compile(r"[A-Za-z0-9_.\-]+")


class CUIEgressError(RuntimeError):
    """Raised when a configuration would let CUI leave the local machine."""


def _normalize(name: str) -> str:
    """PEP 503 distribution-name normalization."""
    return re.sub(r"[-_.]+", "-", name).strip().lower()


def runtime_requirement_names() -> set[str]:
    """Normalized names of the package's *base* runtime dependencies.

    Requirements gated on an extra (e.g. the ``dev`` toolchain) are excluded, so
    only what the shipped tool actually installs at runtime is considered.
    """
    names: set[str] = set()
    for raw in importlib.metadata.requires(DIST_NAME) or []:
        spec, _, marker = raw.partition(";")
        if "extra" in marker:  # gated on an optional extra → not a base runtime dep
            continue
        match = _NAME_RE.match(spec.strip())
        if match:
            names.add(_normalize(match.group(0)))
    return names


def forbidden_runtime_dependencies() -> set[str]:
    """Declared runtime dependencies that are on the forbidden list.

    Must be empty for the tool to be CUI-safe.
    """
    return runtime_requirement_names() & FORBIDDEN_RUNTIME_DISTRIBUTIONS


def importable_cloud_sdks() -> set[str]:
    """Forbidden cloud-SDK modules that are importable in this interpreter."""
    found: set[str] = set()
    for module in FORBIDDEN_CLOUD_MODULES:
        try:
            spec = importlib.util.find_spec(module)
        except (ImportError, ValueError):
            # A parent package is missing → the module is not importable.
            continue
        if spec is not None:
            found.add(module)
    return found


def assert_local_only() -> None:
    """Fail closed if anything could move CUI off the machine.

    Raises :class:`CUIEgressError` when a forbidden distribution is a declared
    runtime dependency, or a forbidden cloud SDK is importable.
    """
    offending_deps = forbidden_runtime_dependencies()
    offending_sdks = importable_cloud_sdks()
    if not offending_deps and not offending_sdks:
        return
    problems: list[str] = []
    if offending_deps:
        problems.append("forbidden runtime dependencies: " + ", ".join(sorted(offending_deps)))
    if offending_sdks:
        problems.append("importable cloud SDKs: " + ", ".join(sorted(offending_sdks)))
    raise CUIEgressError(
        "CUI egress guard tripped — the runtime must stay local-only. " + "; ".join(problems)
    )


def is_loopback_host(host: str) -> bool:
    """Return ``True`` iff ``host`` refers to the local machine (loopback only).

    Used by the local-AI client so a CUI project can only ever reach a loopback
    address (e.g. Ollama on ``127.0.0.1:11434``), never a remote host.
    """
    candidate = host.strip().strip("[]").lower()
    if not candidate:
        return False
    if candidate in _LOOPBACK_HOSTNAMES:
        return True
    try:
        return ip_address(candidate).is_loopback
    except ValueError:
        return False

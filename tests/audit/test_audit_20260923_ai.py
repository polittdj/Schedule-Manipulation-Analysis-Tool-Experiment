"""Executable reproducers for the AUDIT-2026-09-23 findings in the AI lane (A0923-AI-001..005).

Campaign: AUDIT-2026-09-23, a read-only audit of base 8c71c639 (v1.0.289). AUDIT + PLAN ONLY:
the audit changed nothing under ``src/``; these tests are the evidence a fixing PR inherits.

Every test asserts the CORRECT behaviour and is marked ``xfail(strict=True, raises=...)`` with the
exception observed red-first on the audited tree, so the suite stays green while the defect exists:

  * XFAIL  -- the defect is still present (the expected state until it is fixed).
  * XPASS  -- the defect is gone. Under ``strict=True`` an XPASS FAILS the run and names the test:
    that is the signal. The fixing PR removes that test's marker in the same commit, and the test
    stays behind as the permanent regression pin.
  * FAILED with an exception other than the marker's ``raises`` -- a precondition moved (every
    precondition is a ``pytest.fail``, never an ``assert``, so a broken setup can never pass for
    the expected xfail) or the defect changed shape. Investigate; do not re-mark.

Inputs are built inline (tool-format JSON schedules); no fixture file is added and nothing is CUI.
Nothing leaves the process: the model is an in-process scripted stand-in patched over
``web.app._active_backend``, and an autouse fixture refuses every non-loopback connect and every
name lookup. Drop-in path: ``tests/audit/``.
Run: ``pytest tests/audit/test_audit_20260923_ai.py -rxX``.
"""

from __future__ import annotations

import html
import json
import re
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.web.app as app_module
from schedule_forensics.ai.backend import AIConfig
from schedule_forensics.importers.json_schedule import parse_json_text
from schedule_forensics.web.app import SessionState, create_app

REPO = Path(__file__).resolve().parents[2]

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


@pytest.fixture(autouse=True)
def _air_gapped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-test state dirs, and no way off the machine: a non-loopback connect or any name lookup
    other than a loopback literal raises before a packet is sent."""
    for var in ("SF_SETTINGS_DIR", "SF_AI_LOG_DIR", "SF_CACHE_DIR"):
        monkeypatch.setenv(var, str(tmp_path / var))
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect

    def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        name = host.decode() if isinstance(host, bytes) else host
        if name is not None and str(name) not in _LOOPBACK:
            raise OSError(f"air-gapped test: name lookup of {name!r} refused")
        return real_getaddrinfo(host, *args, **kwargs)

    def connect(self: socket.socket, address: Any) -> None:
        if isinstance(address, tuple) and str(address[0]) not in _LOOPBACK:
            raise OSError(f"air-gapped test: connect to {address!r} refused")
        real_connect(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", connect)


def _schedule(status: str, harness_minutes: int) -> str:
    """A three-activity tool-format schedule: one complete, one open, a finish milestone."""
    return json.dumps(
        {
            "name": "Probe",
            "project_start": "2026-01-05T08:00:00",
            "status_date": status,
            "calendars": [{"name": "Standard", "hours_per_day": 8}],
            "tasks": [
                {
                    "unique_id": 1,
                    "name": "Design Review",
                    "duration_minutes": 2400,
                    "percent_complete": 100,
                    "actual_start": "2026-01-05T08:00:00",
                    "actual_finish": "2026-01-09T17:00:00",
                },
                {
                    "unique_id": 2,
                    "name": "Integrate Flight Harness",
                    "duration_minutes": harness_minutes,
                    "percent_complete": 0,
                },
                {"unique_id": 3, "name": "Ship", "duration_minutes": 0, "percent_complete": 0},
            ],
            "relationships": [
                {"predecessor_id": 1, "successor_id": 2, "type": "FS"},
                {"predecessor_id": 2, "successor_id": 3, "type": "FS"},
            ],
        }
    )


_ONE_VERSION = _schedule("2026-02-02T17:00:00", 4800)

#: Completion metrics populated (two finished activities with baselines, one finished late).
_COMPLETION = json.dumps(
    {
        "name": "Probe",
        "project_start": "2026-01-05T08:00:00",
        "status_date": "2026-02-02T17:00:00",
        "calendars": [{"name": "Standard", "hours_per_day": 8}],
        "tasks": [
            {
                "unique_id": 1,
                "name": "Design",
                "duration_minutes": 2400,
                "percent_complete": 100,
                "baseline_start": "2026-01-05T08:00:00",
                "baseline_finish": "2026-01-09T17:00:00",
                "actual_start": "2026-01-05T08:00:00",
                "actual_finish": "2026-01-09T17:00:00",
            },
            {
                "unique_id": 2,
                "name": "Obtain permits",
                "duration_minutes": 2400,
                "percent_complete": 100,
                "baseline_start": "2026-01-12T08:00:00",
                "baseline_finish": "2026-01-16T17:00:00",
                "actual_start": "2026-01-12T08:00:00",
                "actual_finish": "2026-01-21T17:00:00",
            },
            {"unique_id": 3, "name": "Build", "duration_minutes": 4800, "percent_complete": 0},
            {"unique_id": 4, "name": "Handover", "duration_minutes": 0, "percent_complete": 0},
        ],
        "relationships": [
            {"predecessor_id": 1, "successor_id": 2, "type": "FS"},
            {"predecessor_id": 2, "successor_id": 3, "type": "FS"},
            {"predecessor_id": 3, "successor_id": 4, "type": "FS"},
        ],
    }
)


class _Scripted:
    """An in-process stand-in for a local model: a scripted reply, no transport of any kind."""

    name = "ollama"
    is_local = True
    model = "scripted"

    def __init__(self, reply: str | Callable[[str], str]) -> None:
        self._reply = reply
        self.prompts: list[str] = []

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("scripted",)

    def pull_model(self, model: str) -> None:
        return None

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._reply(prompt) if callable(self._reply) else self._reply


def _appending(phrase: str) -> Callable[[str], str]:
    """A 'polish' that returns the engine statement with ``phrase`` appended."""

    def reply(prompt: str) -> str:
        statement = prompt.split("STATEMENT: ", 1)[1].rsplit("\nREWRITE:", 1)[0]
        return statement.rstrip(".") + f" — {phrase}."

    return reply


def _session(mode: str, **schedules: str) -> tuple[TestClient, SessionState]:
    state = SessionState(ai_config=AIConfig(backend="ollama", qa_mode=mode))
    for key, text in schedules.items():
        state.schedules[key] = parse_json_text(text)
    return TestClient(create_app(state)), state


def _use(monkeypatch: pytest.MonkeyPatch, model: _Scripted) -> _Scripted:
    monkeypatch.setattr(app_module, "_active_backend", lambda st: model)
    return model


def _ask(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, route: str, question: str, reply: str
) -> str | None:
    """The served Ask answer (``None`` = discarded) for a model that replies ``reply``."""
    _use(monkeypatch, _Scripted(reply))
    resp = client.post(route, data={"question": question})
    if resp.status_code != 200:
        pytest.fail(f"precondition: {route} answers ({resp.status_code})")
    answer: str | None = resp.json()["answer"]
    return answer


def _prompt(client: TestClient, monkeypatch: pytest.MonkeyPatch, route: str, question: str) -> str:
    """The prompt the Ask route sends for ``question`` (captured by a spy model)."""
    spy = _use(monkeypatch, _Scripted("x"))
    client.post(route, data={"question": question})
    if not spy.prompts:
        pytest.fail(f"precondition: {route} sent a prompt to the model")
    return spy.prompts[-1]


def _verdict(answer: str | None, reply: str) -> str:
    """How the gate treated a reply: discarded (strict), flagged (a footer), or accepted as-is."""
    if answer is None:
        return "discarded"
    return "accepted" if answer == reply else "flagged"


def _narrative(
    client: TestClient, state: SessionState, monkeypatch: pytest.MonkeyPatch, phrase: str
) -> str:
    """The served polished narrative (unescaped) when the model appends ``phrase``."""
    state.polished.clear()  # the polish cache is keyed by model name, not by reply
    _use(monkeypatch, _Scripted(_appending(phrase)))
    body = client.get("/api/ai/narrative", params={"key": "probe"}).json()
    if not body.get("polished"):
        pytest.fail("precondition: the narrative endpoint ran the scripted model")
    return html.unescape(body["html"])


def _translated(
    client: TestClient, state: SessionState, monkeypatch: pytest.MonkeyPatch, src: str, line: str
) -> str | None:
    """What POST /api/translate serves for ``src`` when the model answers ``line``."""
    state.translations.clear()  # a memoised translation would bypass the model
    _use(monkeypatch, _Scripted(f"0\t{line}"))
    resp = client.post("/api/translate", json={"lang": "es", "texts": [src]})
    served: str | None = resp.json()["translations"].get(src)
    return served


# --------------------------------------------------------------------------------------------
# A0923-AI-001 (T1): spelled-out counts pass the strict/annotate Ask gate
# --------------------------------------------------------------------------------------------
_NUMBER_WORD_PAIRS = (
    ("13 activities are behind baseline.", "Thirteen activities are behind baseline."),
    ("40 activities finish late.", "Forty activities finish late."),
    ("90 percent of the network is critical.", "Ninety percent of the network is critical."),
)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-AI-001: an Ask answer that spells an unsourced count out ('Thirteen "
    "activities ...') passes the strict and annotate figure gates that discard or flag the same "
    "count written in digits (qa._classify_figures iterates _TOKEN_RE, not figure_tokens)",
)
def test_a0923_ai_001_spelled_out_count_is_gated_like_its_digits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Claim: at 8c71c639 a strict-mode Ask answer 'Thirteen activities are behind baseline.' is
    ACCEPTED and an annotate-mode one carries no footer, on both Ask routes, where the digit form
    '13 ...' is discarded / flagged (ai/qa.py _classify_figures and _figure_roles tokenise with
    _TOKEN_RE, never with citations.figure_tokens).

    Authority: docs/adr/0239-ai-figure-gate-hardening.md:23-28 "2. **M4:** `figure_tokens` gains a
    bounded number-word lexicon (two…ninety + scale words + zero + dozen), each tokenizing to its
    digit string — "twelve" and "12" are the SAME evidence token, so a legitimate rephrase passes
    and an introduced spelled-out count fails. ... One tokenizer feeds every gate, so
    strict/annotate Q&A and the dual-model cross-check inherit the fix."

    Tier: T1 (not LAW-1).
    """
    mismatches: list[str] = []
    for mode, route in (("strict", "/api/ask/probe"), ("annotate", "/api/ask")):
        client, _state = _session(mode, probe=_ONE_VERSION)
        for digits, words in _NUMBER_WORD_PAIRS:
            q = "How many activities are late?"
            digit_verdict = _verdict(_ask(client, monkeypatch, route, q, digits), digits)
            if digit_verdict == "accepted":
                pytest.fail(f"precondition ({mode}): the digit form {digits!r} is gated")
            word_verdict = _verdict(_ask(client, monkeypatch, route, q, words), words)
            if word_verdict != digit_verdict:
                mismatches.append(
                    f"{mode} {route}: {words!r} {word_verdict}, digits {digit_verdict}"
                )
    assert mismatches == [], "\n".join(mismatches)


# --------------------------------------------------------------------------------------------
# A0923-AI-002 (T1): a sign flip written with a non-ASCII dash passes every figure gate
# --------------------------------------------------------------------------------------------
_DASHES = ("\u2212", "\u2013", "\u2012", "\u2014", "\u2010", "\u2011", "\ufe63", "\uff0d", "\u02d7")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-AI-002: a sign flip written with U+2212 / U+2013 (and seven more dash code "
    "points) passes strict Ask and /api/translate where the ASCII '-' flip is discarded, and the "
    "engine name 'DCMA-14' seeds '-14' as a citable engine value",
)
def test_a0923_ai_002_a_sign_flip_is_caught_whatever_dash_writes_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Claim: at 8c71c639 the engine fact 'moved +N calendar day(s)' re-stated as 'moved \u2212N
    calendar days' (U+2212, U+2013 and seven other dash code points) is ACCEPTED by strict Ask and
    served by /api/translate while the ASCII '-N' flip is discarded; and 'DCMA-14' in the fact
    sheet makes an answer '-14 calendar days' pass as an engine value (citations._TOKEN_RE's sign
    is an unanchored ASCII '-').

    Authority: docs/adr/0131-audit-cluster-remediation-batch1.md:58-60 "7. **M6 — figure-gate is
    sign-aware.** `ai/citations._FIGURE_RE` gains an optional leading `-`, so a rephrase that flips
    `-5 days` (ahead) to `5 days behind` changes the multiset and forces the verbatim fallback.
    Sign is load-bearing in schedule forensics (variance / float / slip direction)."

    Tier: T1 (not LAW-1). Sign-free word flips ('... EARLIER') are documented design, not tested.
    """
    client, state = _session(
        "strict",
        v1=_schedule("2026-01-12T17:00:00", 4800),
        v2=_schedule("2026-01-19T17:00:00", 6240),
    )
    q = "How did the computed finish move between versions?"
    prompt = _prompt(client, monkeypatch, "/api/ask", q)
    moved = re.search(r"moved \+(\d+) calendar day", prompt)
    if moved is None or "DCMA-14" not in prompt:
        pytest.fail("precondition: the fact sheet states a +N finish movement and names DCMA-14")
    days = moved.group(1)

    def answer(text: str) -> str | None:
        return _ask(client, monkeypatch, "/api/ask", q, text)

    if answer(f"The computed finish moved -{days} calendar days.") is not None:
        pytest.fail("precondition: an ASCII-minus sign flip is discarded by strict (M6)")
    if answer("The computed finish moved -15 calendar days.") is not None:
        pytest.fail("precondition: an invented negative figure is discarded by strict")
    problems = [
        f"strict Ask accepted a flip written with U+{ord(d):04X}"
        for d in _DASHES
        if answer(f"The computed finish moved {d}{days} calendar days.") is not None
    ]
    if answer("The computed finish moved -14 calendar days.") is not None:
        problems.append("strict Ask accepted '-14', seeded only by the name 'DCMA-14'")

    src = "The computed finish moved +12 calendar day(s) between versions."
    es = "El final calculado se movió {}12 días naturales entre las versiones."
    if _translated(client, state, monkeypatch, src, es.format("+")) is None:
        pytest.fail("precondition: /api/translate serves a faithful translation")
    if _translated(client, state, monkeypatch, src, es.format("-")) is not None:
        pytest.fail("precondition: /api/translate discards an ASCII-minus flip")
    if _translated(client, state, monkeypatch, src, es.format("\u2212")) is not None:
        problems.append("/api/translate served a U+2212 flip of +12")
    assert problems == [], "\n".join(problems)


# --------------------------------------------------------------------------------------------
# A0923-AI-003 (T1): non-decimal numerals and zero-width splits are invisible to the gates
# --------------------------------------------------------------------------------------------
_NON_DECIMAL = (
    "About \u215e of the work is critical.",
    "\u00be of the incomplete activities are critical.",
    "About 2\u00bd weeks of float remain.",
    "\u00b2\u2075 activities are behind baseline.",
    "\u3255 activities are behind baseline.",
    "\u216b activities are behind baseline.",
)
_ZERO_WIDTH_SPLIT = tuple(
    f"2{mark}5 activities are behind baseline." for mark in ("\u200b", "\u2060", "\u00ad", "\ufeff")
)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-AI-003: a figure written with a vulgar fraction, superscript, circled or Roman "
    "numeral yields no figure token, and a zero-width split of '25' tokenizes as its sourced "
    "parts, so unsourced figures pass strict Ask and the narrative reattach gate",
)
def test_a0923_ai_003_non_decimal_and_split_figures_are_gated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Claim: at 8c71c639 'About ⅞ of the work is critical.' is ACCEPTED by strict Ask where
    '87.5%' is discarded (superscript, circled and Roman numerals likewise), '2\\u200b5 activities
    ...' is ACCEPTED because '2' and '5' are sourced values, and '²⁵ further activities are at
    risk' appended to an engine statement is served by /api/ai/narrative where plain '25' is not
    (citations._TOKEN_RE matches \\d = Unicode Nd only; no format-character folding).

    Authority: CLAUDE.md:234-239 "`strict` discards any answer containing an unsourced figure,
    `annotate` (default) keeps the answer but flags AI-derived figures in a footer, ... So "no
    unsourced number reaches the analyst" holds for narrative/briefing and the strict/annotate Q&A
    modes — not for interpretive."

    Tier: T1 (not LAW-1). Thin spaces (U+2009/U+202F, a visible gap) are left out of scope.
    """
    client, state = _session("strict", probe=_ONE_VERSION)
    route, q = "/api/ask/probe", "How much of the work is critical?"
    facts = _prompt(client, monkeypatch, route, q).split("FACTS:", 1)[-1]
    if not {"2", "5"} <= set(re.findall(r"(?<![\w.-])\d+(?![\w.])", facts)):
        pytest.fail("precondition: 2 and 5 are sourced values in the strict fact sheet")
    for plain in ("About 87.5% of the work is critical.", "25 activities are behind baseline."):
        if _ask(client, monkeypatch, route, q, plain) is not None:
            pytest.fail(f"precondition: strict discards the unsourced {plain!r}")
    problems = [
        f"strict Ask accepted {text!r}"
        for text in (*_NON_DECIMAL, *_ZERO_WIDTH_SPLIT)
        if _ask(client, monkeypatch, route, q, text) is not None
    ]
    if "noted for the record" not in _narrative(client, state, monkeypatch, "noted for the record"):
        pytest.fail("precondition: a figure-free polish is served by /api/ai/narrative")
    if "25 further" in _narrative(client, state, monkeypatch, "25 further activities are at risk"):
        pytest.fail("precondition: the reattach gate rejects an added plain 25")
    added = "\u00b2\u2075 further activities are at risk"
    if added in _narrative(client, state, monkeypatch, added):
        problems.append(f"/api/ai/narrative served {added!r}")
    assert problems == [], "\n".join(problems)


# --------------------------------------------------------------------------------------------
# A0923-AI-004 (T2): the unit-role step misses the engine's glued units ('5.0days')
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-AI-004: the fact sheet writes 'Average Days Late: N.Ndays' (unit glued), "
    "qa._PLAIN_UNIT_RE needs a space before the unit word, so a days-only figure re-used as a "
    "percentage passes strict and annotate unflagged",
)
def test_a0923_ai_004_a_days_figure_re_used_as_a_percentage_is_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Claim: at 8c71c639 the Ask fact sheet states the completion averages with the unit glued
    ('Average Days Late: 5.0days'), so they get no unit role and 'Completed activities finish
    5.0% late on average.' is ACCEPTED in strict and unflagged in annotate, while the mirror move
    (a %-only figure re-used as days) is caught.

    Authority: docs/adr/0145-unit-role-figure-gate.md:23-29 "1. **Fact side.** For every value
    token, record the EXPLICIT unit contexts the facts state it in: `pct` (followed by
    `%`/`percent`) or `plain` (followed by a count/duration unit word — day(s), activities, tasks,
    minutes, hours, links, relationships). ... 2. **Answer side.** A value token written with an
    explicit unit that is **absent from its fact unit set** is `unit_misused`: **strict discards**
    the answer, **annotate flags** it".

    Tier: T2 (not LAW-1). Scope (verifier): the two completion averages; DCMA values glue only
    '%', 'count' or 'ratio' and lose no unit role.
    """
    q = "How late are completed activities on average?"
    strict, _state = _session("strict", probe=_COMPLETION)
    prompt = _prompt(strict, monkeypatch, "/api/ask/probe", q)
    late = re.search(r"Average Days Late: (\d+\.\d)days", prompt)
    pct = re.search(r"Completed Behind Baseline: (\d+\.\d)%", prompt)
    if late is None or pct is None:
        pytest.fail("precondition: the fact sheet states Average Days Late (glued) and a % metric")
    days_only, pct_only = late.group(1), pct.group(1)
    faithful = f"Completed activities finish {days_only} days late on average."
    mirror = f"{pct_only} days of slip were recorded."
    misuse = f"Completed activities finish {days_only}% late on average."
    if _ask(strict, monkeypatch, "/api/ask/probe", q, faithful) is None:
        pytest.fail("precondition: the faithful days usage is accepted")
    if _ask(strict, monkeypatch, "/api/ask/probe", q, mirror) is not None:
        pytest.fail("precondition: the unit step is live (a %-only figure as days is discarded)")
    problems = []
    if _ask(strict, monkeypatch, "/api/ask/probe", q, misuse) is not None:
        problems.append(f"strict accepted {misuse!r}")
    annotate, _state = _session("annotate", probe=_COMPLETION)
    if _verdict(_ask(annotate, monkeypatch, "/api/ask", q, mirror), mirror) != "flagged":
        pytest.fail("precondition: annotate flags a %-only figure re-used as days")
    if _verdict(_ask(annotate, monkeypatch, "/api/ask", q, misuse), misuse) != "flagged":
        problems.append(f"annotate left {misuse!r} unflagged")
    assert problems == [], "\n".join(problems)


# --------------------------------------------------------------------------------------------
# A0923-AI-005 (T2): the accusation guard misses compounds/plurals; translation has no guard
# --------------------------------------------------------------------------------------------
_COMPOUND_ACCUSATIONS = (
    "a fraud-like pattern",
    "frauds in the baseline",
    "a deliberately-timed cut",
    "a concealment-driven re-plan",
    "sabotage-style logic edits",
    "falsification-grade edits",
)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-AI-005: introduces_loaded_terms() matches whole words and _WORD_RE keeps "
    "'fraud-like' as one word, so plural/hyphenated forms of the listed terms are served in the "
    "polished narrative; /api/translate applies no accusation guard though CLAUDE.md says it does",
)
def test_a0923_ai_005_polish_and_translation_never_add_an_accusation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Claim: at 8c71c639 a narrative polish that appends 'a fraud-like pattern', 'frauds ...',
    'a deliberately-timed cut', 'a concealment-driven re-plan', 'sabotage-style ...' or
    'falsification-grade ...' is SERVED by /api/ai/narrative while 'a fraudulent pattern' is
    rejected, and /api/translate serves a line that appends '— fraud.' (no accusation guard).

    Authority: docs/adr/0132-audit-cluster-remediation-batch2.md:21-25 "1. **H2 — the narrative
    gate rejects an introduced accusation.** ... it now *also* rejects a rephrase that **introduces
    an accusatory/intent term the source lacked** (`introduces_loaded_terms`: fraud, deliberate,
    intentional, conceal, falsify, sabotage, malicious, willful, deceptive, … — a high-precision
    list of *conclusions the engine never draws*)." and CLAUDE.md:229-233 "The **narrative /
    briefing / translation** paths re-verify every AI-emitted figure ... **and**, since ADR-0132
    (audit H2), rejects a rephrase that *introduces an accusatory/intent term the engine never
    asserted*".

    Tier: T2 (not LAW-1). The translation half rests on CLAUDE.md alone (verifier), so it is
    asserted as an implication: either translation rejects the accusation, or CLAUDE.md stops
    promising it (an operator ruling picks the remedy).
    """
    client, state = _session("annotate", probe=_ONE_VERSION)
    if "fraudulent" in _narrative(client, state, monkeypatch, "a fraudulent pattern"):
        pytest.fail("precondition: the listed term 'fraudulent' is rejected by the guard")
    problems = [
        f"/api/ai/narrative served {phrase!r}"
        for phrase in _COMPOUND_ACCUSATIONS
        if phrase in _narrative(client, state, monkeypatch, phrase)
    ]
    src = "Duration shortened on the critical path."
    faithful = "Duración acortada en la ruta crítica."
    if _translated(client, state, monkeypatch, src, faithful) != faithful:
        pytest.fail("precondition: /api/translate serves a faithful model translation")
    accusing = "Duración acortada en la ruta crítica — fraud."
    claude_md = REPO / "CLAUDE.md"
    if not claude_md.is_file():
        pytest.fail("precondition: run from a checkout (CLAUDE.md at the repo root)")
    doc = " ".join(claude_md.read_text(encoding="utf-8").split())
    promised = (
        "**narrative / briefing / translation** paths" in doc
        and "introduces an accusatory/intent term" in doc
    )
    if promised and _translated(client, state, monkeypatch, src, accusing) == accusing:
        problems.append("/api/translate served an added '— fraud.' that CLAUDE.md says is guarded")
    assert problems == [], "\n".join(problems)

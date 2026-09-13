"""The answer's length is the tool's to set, and a cut or empty answer is EVIDENCE (ADR-0486).

Three asks in a row on the approved gateway (a *thinking* model): two answers stopped
mid-sentence, then a slightly longer question produced no answer text at all — and the panel
said *"select a different model"*. Neither OpenAI-compatible backend sent ``max_tokens``, so the
server's own default output budget governed, and a thinking model spends that budget reasoning
before it writes; neither read ``finish_reason``, so a ``length`` stop rendered as a complete
answer; neither read the reasoning fields, so "no answer text" could not be told apart from
"no answer at all"; and a ``null`` ``content`` became the literal word ``None``.

What this module gives both backends (``openai_compat`` and ``gateway``):

* **A bounded answer-length setting** — sent as ``max_tokens`` on every generation. The default
  is the MAXIMUM the form allows (operator directive, 2026-09-11: *"raise the limit to the
  max"*); ``0`` sends nothing and leaves the server's default in charge, exactly as before.
* **An honest fallback.** There is no universal maximum — every model and server has its own —
  so a hard-coded "max" would turn every answer into an HTTP 400 on a stricter server. A 400
  that NAMES the parameter is answered once more without it, and the fallback is RECORDED so
  the disclosure can say that the server's own default, not the operator's setting, cut the
  answer.
* **The completion read as evidence, not just as prose:** ``finish_reason``, the length of the
  answer text, the length of any reasoning the server exposed (``reasoning_content`` or
  ``reasoning``), and ``usage.completion_tokens`` when reported — so the panel can say *what*
  happened instead of guessing.

Nothing here reads schedule content; the stats are lengths and a status word.
"""

from __future__ import annotations

import re
import urllib.error
from dataclasses import dataclass
from typing import Any

from schedule_forensics.ai.refusal import http_error_body

#: The smallest answer budget worth sending — below this a forensic answer cannot even list
#: its citations, and a server default is strictly better.
MIN_ANSWER_TOKENS = 256

#: The largest budget the tool will ask for. NOT a claim about any model: it is a form bound
#: chosen above every output ceiling published for the model families the tool talks to as of
#: 2026-09-11 (UNVERIFIED for the operator's own gateway model — which is why a server that
#: rejects the value is retried without it rather than trusted to accept it).
MAX_ANSWER_TOKENS = 131_072

#: Operator directive (2026-09-11): the default IS the maximum. Raising this setting has a
#: different failure mode from ADR-0481's context window — no memory allocation rides on it;
#: a value a server will not accept is rejected out loud (HTTP 400) and falls back with a
#: disclosure — so, unlike ``num_ctx``, it does not default to OFF.
DEFAULT_ANSWER_TOKENS = MAX_ANSWER_TOKENS


def clamp_answer_tokens(value: int) -> int:
    """The operator's requested answer budget, bounded — or ``0``, meaning "send no limit".

    Applied at EVERY boundary the value crosses — the form, the settings file, and both
    backend constructors — because each is separately reachable.
    """
    if value <= 0:
        return 0
    return max(MIN_ANSWER_TOKENS, min(MAX_ANSWER_TOKENS, value))


@dataclass(frozen=True)
class CompletionStats:
    """What the server reported about the LAST completion, as evidence, not as a claim.

    ``finish_reason`` is the server's own word (``stop`` / ``length`` / …; "" when it sent
    none). ``content_chars`` / ``reasoning_chars`` are lengths of what came back, never the
    text. ``completion_tokens`` is ``usage.completion_tokens`` when the server reports it.
    ``max_tokens_sent`` is the budget WE asked for on the attempt that answered (``None`` when
    none was sent); ``limit_rejected`` records that the server refused that budget and the
    answer came from the retry without it.
    """

    finish_reason: str = ""
    content_chars: int = 0
    reasoning_chars: int = 0
    completion_tokens: int | None = None
    max_tokens_sent: int | None = None
    limit_rejected: bool = False


_LIMIT_PARAM = re.compile(r"max_(?:completion_)?tokens")


def limit_rejected(exc: BaseException) -> bool:
    """Whether ``exc`` is a server REJECTING the answer-length setting itself.

    Only an HTTP 400 whose body names the parameter (``max_tokens``, or the newer
    ``max_completion_tokens`` some servers demand instead) counts. A 403 is a refusal of the
    request, a 500 is the server's own failure, a bodiless 400 is unknown — none of those may
    trigger a silent retry.
    """
    if not isinstance(exc, urllib.error.HTTPError) or exc.code != 400:
        return False
    # read once, cached on the exception: the diagnostics quote the same body (OR-16)
    text = http_error_body(exc).decode("utf-8", "replace")
    return _LIMIT_PARAM.search(text) is not None


def read_completion(payload: Any) -> tuple[str, CompletionStats]:
    """The answer text and the evidence around it, from an OpenAI-style completion body.

    A ``null`` or absent ``content`` is the EMPTY answer ``""`` — never the word ``None``.
    Nothing is stripped here; the QA layer decides what whitespace means.
    """
    choice: dict[str, Any] = {}
    if isinstance(payload, dict):
        choices = payload.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            choice = choices[0]
    message = choice.get("message")
    message = message if isinstance(message, dict) else {}
    raw = message.get("content")
    content = raw if isinstance(raw, str) else ""
    reasoning = message.get("reasoning_content")
    if not isinstance(reasoning, str):
        reasoning = message.get("reasoning")
    finish = choice.get("finish_reason")
    usage = payload.get("usage") if isinstance(payload, dict) else None
    tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
    return content, CompletionStats(
        finish_reason=finish if isinstance(finish, str) else "",
        content_chars=len(content),
        reasoning_chars=len(reasoning) if isinstance(reasoning, str) else 0,
        completion_tokens=(
            tokens if isinstance(tokens, int) and not isinstance(tokens, bool) else None
        ),
    )


def answer_cut_warning(stats: CompletionStats | None) -> str | None:
    """A disclosure when the server stopped the answer at an output limit, else ``None``.

    Worded from what was MEASURED: the server's ``finish_reason``, the budget this tool asked
    for, and whether the server rejected that budget — so an operator who already raised the
    setting is not told to raise it again, and one whose server refused it is told to lower it.
    """
    if stats is None or stats.finish_reason != "length":
        return None
    generated = f", {stats.completion_tokens:,} tokens generated" if stats.completion_tokens else ""
    if stats.limit_rejected:
        return (
            f"The answer was CUT at the server's own output limit (finish_reason=length"
            f"{generated}): this tool asked for an answer of up to {stats.max_tokens_sent or 0:,} "
            "tokens, the "
            "server REJECTED that setting, and its default budget ran out. Lower the Answer length "
            "limit in AI Settings to a value this server accepts, or ask a narrower question."
        )
    if not stats.max_tokens_sent:
        return (
            f"The answer was CUT at the server's own output limit (finish_reason=length"
            f"{generated}): this tool sent no limit (Answer length limit is 0 in AI Settings, "
            "which leaves the "
            "server's default in charge). Set the Answer length limit in AI Settings, or ask a "
            "narrower question."
        )
    return (
        f"The answer was CUT at the output limit (finish_reason=length{generated}): this tool "
        f"asked for up to {stats.max_tokens_sent:,} tokens and the server stopped there - a "
        "thinking model spends part of that budget reasoning before it writes. Raise the Answer "
        "length limit in AI Settings if it is below the maximum, switch AI answer mode to Annotate "
        "(a much smaller prompt), or ask a narrower question."
    )


def empty_answer_detail(stats: CompletionStats | None) -> str:
    """WHY an answer came back empty, from the evidence — or "" when nothing is known."""
    if stats is None:
        return ""
    cut = stats.finish_reason == "length"
    if cut and stats.reasoning_chars:
        return (
            f"it stopped at the output limit (finish_reason=length) after "
            f"{stats.reasoning_chars:,} characters of reasoning and no answer text"
        )
    if stats.reasoning_chars:
        return (
            f"it produced {stats.reasoning_chars:,} characters of reasoning and no answer text "
            f"(finish_reason={stats.finish_reason or 'unknown'})"
        )
    if cut:
        return (
            "it stopped at the output limit (finish_reason=length) before writing any answer text"
        )
    return ""

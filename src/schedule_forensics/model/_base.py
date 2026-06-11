"""Shared base for the domain-model value objects.

Every model in this package is the *trust root* the engine computes on, so each is:

* **frozen** — immutable and hashable; a parsed schedule cannot be mutated out from
  under an analysis (and two reads of the same file are equal/hashable);
* **strict** — no silent type coercion (a string is not silently parsed into a
  datetime; an int is not a duration) so a malformed import fails loudly; and
* **closed** (``extra="forbid"``) — an unknown field is an error, not a silent drop,
  so importer drift surfaces immediately instead of quietly losing metadata.

Only *source-of-truth* fields (what the schedule file actually records) live on these
models. Derived analytics — CPM early/late dates, total/free float, driving slack,
DCMA/EVM metrics — are **computed by the engine, never stored here**, so a persisted
value can never drift from the inputs it was derived from (Law 2, fidelity).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictFrozenModel(BaseModel):
    """Immutable (frozen + hashable), strict (no coercion), closed (extra forbidden).

    ``hide_input_in_errors`` keeps schedule contents (task names, dates, costs — CUI)
    out of ValidationError text, which importers wrap into user-facing messages.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, hide_input_in_errors=True)

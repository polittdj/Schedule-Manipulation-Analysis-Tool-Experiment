"""Saved MS Project **views** — the task filters and groups a `.mpp`/MSPDI carries verbatim.

MS Project stores, alongside the schedule, named **filters** (a criteria tree the planner built)
and **groups** (how to bucket/sort rows). Feature #10 reproduces them *faithfully* — every
operator, the recursive AND/OR structure, interactive prompts, field-to-field comparisons — so
the tool filters and groups exactly as MS Project would, not by an approximation.

These are frozen value objects the importer fills from the vendored MPXJ export (Java-side, out
of process) and the engine (:mod:`schedule_forensics.engine.msp_filters`) evaluates. The
criteria model mirrors MPXJ's ``org.mpxj.GenericCriteria`` tree exactly:

* a **leaf** node carries a left field (``field`` / ``field_enum``), a ``TestOperator`` name,
  and up to two right-hand **operands** (``IS_WITHIN`` uses both; every other leaf op uses the
  first);
* a **branch** node carries ``operator`` ``AND``/``OR`` and a list of ``children`` (nested
  freely);
* each operand is a **literal**, a **field reference** (another field of the same task — e.g.
  MPXJ's ``Duration9 > Duration8``), a **prompt** (a value MS Project asks for at apply time),
  or **null** (an absent value — e.g. ``Actual Finish EQUALS <null>`` = "not yet finished").

Nothing here evaluates or coerces; it is the faithful *shape* of the source definition. The
evaluator owns the semantics (LHS/RHS normalization, the null-ordering rule, the three string
regimes, …).
"""

from __future__ import annotations

from schedule_forensics.model._base import StrictFrozenModel

#: The ``org.mpxj.TestOperator`` leaf comparison names, verbatim — exactly the strings the MPXJ
#: export emits for ``GenericCriteria.getOperator().name()`` (the ``AND``/``OR`` branch
#: combiners are below).
LEAF_OPERATORS = frozenset(
    {
        "IS_ANY_VALUE",
        "IS_WITHIN",
        "IS_GREATER_THAN",
        "IS_LESS_THAN",
        "IS_GREATER_THAN_OR_EQUAL_TO",
        "IS_LESS_THAN_OR_EQUAL_TO",
        "EQUALS",
        "DOES_NOT_EQUAL",
        "CONTAINS",
        "IS_NOT_WITHIN",
        "DOES_NOT_CONTAIN",
        "CONTAINS_EXACTLY",
    }
)
BRANCH_OPERATORS = frozenset({"AND", "OR"})

#: An operand's kind: a literal value, a reference to another of the task's fields
#: (field-to-field), an interactive prompt, or an absent/null value.
OPERAND_KINDS = frozenset({"literal", "field", "prompt", "null"})


class Operand(StrictFrozenModel):
    """One right-hand value of a leaf criterion — a literal, a field reference, a prompt, or null.

    * ``kind="literal"`` — ``text`` is the source's raw value string (``"SVT-"``, ``"true"``,
      ``"2028-09-29T17:00"``, ``"0.0d"``); ``value_type`` is MPXJ's runtime type hint
      (``String``/``Boolean``/``LocalDateTime``/``Duration``/``Number``) so the evaluator can
      coerce it to the left field's axis.
    * ``kind="field"`` — ``text`` is the referenced field's raw name, ``field_enum`` its MPXJ
      enum; the evaluator resolves that field on the *same task* (MPXJ symbolic values).
    * ``kind="prompt"`` — ``text`` is the prompt label MS Project shows; the answer is supplied
      at evaluate time.
    * ``kind="null"`` — an explicitly absent value (``EQUALS <null>``).
    """

    kind: str
    text: str | None = None
    field_enum: str | None = None
    value_type: str | None = None


class Criterion(StrictFrozenModel):
    """One node of a filter's criteria tree — a leaf comparison or an AND/OR branch.

    Leaf: ``operator`` is a :data:`LEAF_OPERATORS` name, ``field``/``field_enum`` is the left
    field, ``operands`` holds 0-2 right-hand values (``IS_ANY_VALUE`` uses none, ``IS_WITHIN``
    two, the rest one). Branch: ``operator`` is ``AND``/``OR`` and ``children`` holds the
    sub-criteria (nested freely). An empty branch is a pass-through (matches everything),
    mirroring MPXJ.
    """

    operator: str
    field: str | None = None
    field_enum: str | None = None
    operands: tuple[Operand, ...] = ()
    children: tuple[Criterion, ...] = ()

    @property
    def is_branch(self) -> bool:
        return self.operator in BRANCH_OPERATORS


class SavedFilter(StrictFrozenModel):
    """A named MS Project task (or resource) filter: its criteria tree + presentation flags.

    ``criteria is None`` is the built-in match-all ("All Tasks" / "All Resources").
    ``prompt_count`` is how many interactive prompts the filter asks for (0 for a
    non-interactive one); ``show_related_summary_rows`` mirrors MS Project's option to keep the
    parent summaries of the matching tasks in a filtered view.
    """

    name: str
    criteria: Criterion | None = None
    is_task_filter: bool = True
    show_related_summary_rows: bool = False
    prompt_count: int = 0


class GroupClause(StrictFrozenModel):
    """One clause of a group definition: the field to bucket on + how to sort/interval it.

    ``group_on`` mirrors MPXJ's int (``0`` = each distinct value; ``2`` = interval-bucketed,
    e.g. ``% Complete`` in bands); ``interval``/``start_at`` are the raw interval spec (kept as
    strings — presentation, not forensic). Multiple clauses nest (group, then sub-group).
    """

    field: str | None = None
    field_enum: str | None = None
    ascending: bool = True
    group_on: int = 0
    interval: str | None = None
    start_at: str | None = None


class SavedGroup(StrictFrozenModel):
    """A named MS Project grouping (an ordered list of clauses); ``clauses`` empty = "No Group"."""

    name: str
    show_summary_tasks: bool = True
    clauses: tuple[GroupClause, ...] = ()

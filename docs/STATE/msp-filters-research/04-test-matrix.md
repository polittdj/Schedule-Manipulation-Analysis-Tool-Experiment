Note: claude-sonnet-5[1m] (the safety classifier) was unavailable when reviewing this subagent's work. Please carefully verify the subagent's actions and output before acting on them.

I have everything I need. Here is the concrete test-matrix design section, pinned to the ground truth in `views_leveled.json` and `MSP-FILTERS-SPEC.md`.

---

# Feature #10 — Test matrix for the faithful MS-Project filter evaluator

Pure-Python pytest plan. **No Java at test time** — every real filter's criteria tree is hand-authored from the MPXJ ground truth (`views_leveled.json:2`, summarized in `MSP-FILTERS-SPEC.md:18-26`) and exercised against synthetic `Task`/`Schedule` fixtures. This pins the evaluator (`engine/msp_filters.py`) and the view model (`model/saved_view.py`) to what MS Project actually computed on `Large Test File Leveled.mpp`.

## 0. Assumed API under test (what the fixtures instantiate)

The matrix is written against this shape (the design's `model/saved_view.py` + `engine/msp_filters.py`). If the final field/method names differ, only the two builder helpers below change.

```python
class FilterOp(StrEnum):            # the 14 MPXJ TestOperator values (SPEC line 11-13)
    AND=...; OR=...
    IS_ANY_VALUE=...; EQUALS=...; DOES_NOT_EQUAL=...
    CONTAINS=...; DOES_NOT_CONTAIN=...; CONTAINS_EXACTLY=...
    IS_GREATER_THAN=...; IS_GREATER_THAN_OR_EQUAL_TO=...
    IS_LESS_THAN=...; IS_LESS_THAN_OR_EQUAL_TO=...
    IS_WITHIN=...; IS_NOT_WITHIN=...

class Criterion(StrictFrozenModel):
    op: FilterOp
    field: str | None = None            # LHS raw MSP field / fieldEnum: "NAME","START","TEXT9",...
    values: tuple[str, ...] = ()        # 0 operands = null-test; 1 = normal; 2 = IS_WITHIN
    field_ref: str | None = None        # field-to-field RHS ("DURATION8"); v0type=="TaskField"
    prompt: str | None = None           # PROMPT(...) text key; v0type=="GenericCriteriaPrompt"
    children: tuple[Criterion, ...] = ()  # AND/OR only

class SavedFilter(StrictFrozenModel):
    name: str
    criteria: Criterion | None          # None == pass-through ("All Tasks")
    show_summary_rows: bool = False
    is_task_filter: bool = True

# engine/msp_filters.py
def evaluate(schedule, filt, prompts: Mapping[str, str] | None = None) -> tuple[int, ...]:
    """UIDs matching the filter, in file order. Raises MissingPromptError if a PROMPT
       criterion has no supplied value."""
def matches(schedule, task, criterion, prompts=None) -> bool:   # single-task predicate
```

## 1. Shared test scaffolding (matches repo idiom)

Follows `test_margin.py:25-31` and `test_grouping.py:26-42` verbatim in style.

```python
import datetime as dt
from schedule_forensics.model.task import Task
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.saved_view import SavedFilter, Criterion, FilterOp as OP
from schedule_forensics.engine.msp_filters import evaluate, matches, MissingPromptError

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480  # working minutes / day (units.py:33)


def _task(uid: int, **kw) -> Task:
    kw.setdefault("name", f"T{uid}")
    kw.setdefault("duration_minutes", DAY)
    return Task(unique_id=uid, **kw)


def _sched(tasks, labels=()) -> Schedule:
    return Schedule(
        name="f",
        source_file="f.mpp",
        project_start=MON,
        tasks=tuple(tasks),
        custom_field_labels=labels,
    )


def leaf(op, field, *values, field_ref=None, prompt=None) -> Criterion:
    return Criterion(op=op, field=field, values=values, field_ref=field_ref, prompt=prompt)


def AND(*kids) -> Criterion:
    return Criterion(op=OP.AND, children=kids)


def OR(*kids) -> Criterion:
    return Criterion(op=OP.OR, children=kids)
```

**Custom-field storage in fixtures.** `Task.custom_fields` is `tuple[(label,value),...]` of **strings** (`task.py:134`), and in the real file the operator did **not** alias these fields, so the label *is* the raw MSP name. Fixtures therefore key customs by raw name: `custom_fields=(("Text9","ZIN"),("Duration8","1.0d"))`. Booleans that are real `Task` attributes (`is_summary`, `is_active`, `is_milestone` — `task.py:77-84`) and dates (`start`,`finish`,`actual_finish` — `task.py:106-108`) are set directly, not as customs.

## 2. Fidelity decisions this matrix pins (the "faithful" contract)

These are the semantic rulings the tests lock down. Several intentionally **diverge from the current `grouping.py`** (case-sensitive, `grouping.py:15,109`), which is what makes the new evaluator "faithful":

| # | Decision pinned | Ground-truth driver |
|---|---|---|
| F1 | **Text ops are case-INSENSITIVE** (CONTAINS/EQUALS/DOES_NOT_CONTAIN/DOES_NOT_EQUAL). `"svt-"` matches `CONTAINS 'SVT-'`; `"zin"` matches `EQUALS 'ZIN'`. | MSP text-filter behavior; corrects `grouping.py:15` |
| F2 | **Unset text field == empty string.** `Text19 EQUALS ''` matches a task with no `Text19`; `Text19 DOES_NOT_EQUAL ''` excludes it. | `_MCTasks`/`_RiskRegTasks` (json:2) |
| F3 | **EQUALS with zero operands = "is blank/null".** `Actual Finish EQUALS` (no `v0`) matches `actual_finish is None`. | `_MCTasks`,`_RiskRegTasks` `ACTUAL_FINISH` node has no `v0` |
| F4 | **Ordered comparisons are inclusive at the bound** (`>=`,`<=`) and **strict** for `>`/`<`. | `Date Range`, `CAM_Tasks`, `_MCTasks` |
| F5 | **Null LHS fails every ordered comparison.** `start=None` never satisfies `Start <= date`; `finish=None` never satisfies `Finish >= date`. | overlap logic of `Date Range` |
| F6 | **Missing-field semantics are type-driven** (from the field family / `v0type`): missing **Text**→`None` (no EQUALS match), missing **Flag**→`False` (flags default No), missing **Duration**→`0`. | `_MCexportedTasks`, `_MCTasks`, `CAM_Tasks` |
| F7 | **Field-to-field**: RHS is another task field, both coerced to a common unit. `Duration9 > Duration8`. | `_MCTasks` node `v0type=="TaskField"` |
| F8 | **Booleans** coerce `{true,yes,1}`→True, `{false,no,0,"",None}`→False, case-insensitively. | Flag6/Summary/Active/Milestone nodes |
| F9 | **Durations** parse the MSP string form (`"0.0d"`,`"3.0d"`,`"-1.0d"`) to working minutes. | `Duration8/9 >= 0.0d` |
| F10 | **`criteria is None` = pass-through** (matches ALL rows, summaries included; no auto-summary-exclusion). | `All Tasks` |
| F11 | **Returned UIDs are in file order.** | evaluator contract |
| F12 | **Prompts required-but-unsupplied → `MissingPromptError`.** | `Date Range...` has 2 prompts |

---

## 3. The 10 real filters (ground-truth-pinned tests)

Each test hand-encodes the exact tree from `views_leveled.json` and asserts the matching UID set. Grouped as one `class TestRealFilters` (or module-level functions).

### 3.1 `All Tasks` / `All Resources` — pass-through (F10)

```python
def test_all_tasks_is_passthrough_including_summaries():
    f = SavedFilter(name="All Tasks", criteria=None)
    tasks = [_task(1), _task(2, is_summary=True), _task(3, is_active=False)]
    assert evaluate(_sched(tasks), f) == (1, 2, 3)  # nothing excluded, file order
```
- Criteria: `criteria=null` (json). Expected: **every UID**, summaries and inactive included.

### 3.2 Leaf string filters — `SVT-`, `No SVT-`, `SVT` (F1, F11)

Shared population:

| UID | name |
|---|---|
| 1 | `SVT-01 Thermal Cycle` |
| 2 | `svt-02 lowercase` |
| 3 | `SVT Review` (no hyphen) |
| 4 | `Structural Assembly` |
| 5 | `Pre-SVT-Delivery Gate` |
| 6 | `""` (empty name) |

```python
def _svt_pop():
    return _sched(
        [
            _task(1, name="SVT-01 Thermal Cycle"),
            _task(2, name="svt-02 lowercase"),
            _task(3, name="SVT Review"),
            _task(4, name="Structural Assembly"),
            _task(5, name="Pre-SVT-Delivery Gate"),
            _task(6, name=""),
        ]
    )


def test_filter_SVT_hyphen():  # CONTAINS 'SVT-'  (json: op CONTAINS, NAME)
    f = SavedFilter(name="SVT-", criteria=leaf(OP.CONTAINS, "NAME", "SVT-"))
    assert evaluate(_svt_pop(), f) == (1, 2, 5)  # 2 proves case-insensitivity (F1)


def test_filter_No_SVT_hyphen():  # DOES_NOT_CONTAIN 'SVT-'
    f = SavedFilter(name="No SVT-", criteria=leaf(OP.DOES_NOT_CONTAIN, "NAME", "SVT-"))
    assert evaluate(_svt_pop(), f) == (3, 4, 6)  # exact complement; empty name matches (F2 edge)


def test_filter_SVT():  # CONTAINS 'SVT'
    f = SavedFilter(name="SVT", criteria=leaf(OP.CONTAINS, "NAME", "SVT"))
    assert evaluate(_svt_pop(), f) == (1, 2, 3, 5)
```
- `SVT-` → **{1,2,5}**; `No SVT-` → **{3,4,6}** (logical complement, incl. empty name); `SVT` → **{1,2,3,5}**.

### 3.3 `Date Range...` — AND of two prompted date bounds (F4, F5, F12)

Tree (json): `AND( Finish >= PROMPT("Show tasks that start or finish after:"), Start <= PROMPT("And before:") )`, `show_summary_rows=True`, `prompts=2`.

Window supplied: after=`2025-03-01`, before=`2025-06-30`.

| UID | start | finish | reason |
|---|---|---|---|
| 1 | 02-01 | 02-20 | finish < after → **out** |
| 2 | 04-01 | 05-01 | both inside → **in** |
| 3 | 07-15 | 08-01 | start > before → **out** |
| 4 | 02-15 | **03-01** | finish == after (inclusive) → **in** (F4) |
| 5 | **06-30** | 09-01 | start == before (inclusive) → **in** (F4) |
| 6 | 04-01 | `None` | null finish fails `>=` → **out** (F5) |

```python
def _daterange_filter():
    return SavedFilter(
        name="Date Range...",
        show_summary_rows=True,
        criteria=AND(
            leaf(
                OP.IS_GREATER_THAN_OR_EQUAL_TO,
                "FINISH",
                prompt="Show tasks that start or finish after:",
            ),
            leaf(OP.IS_LESS_THAN_OR_EQUAL_TO, "START", prompt="And before:"),
        ),
    )


def _daterange_pop():
    d = lambda m, day: dt.datetime(2025, m, day, 8, 0)
    return _sched(
        [
            _task(1, start=d(2, 1), finish=d(2, 20)),
            _task(2, start=d(4, 1), finish=d(5, 1)),
            _task(3, start=d(7, 15), finish=d(8, 1)),
            _task(4, start=d(2, 15), finish=d(3, 1)),
            _task(5, start=d(6, 30), finish=d(9, 1)),
            _task(6, start=d(4, 1), finish=None),
        ]
    )


def test_date_range_prompts_supplied():
    prompts = {"Show tasks that start or finish after:": "2025-03-01", "And before:": "2025-06-30"}
    assert evaluate(_daterange_pop(), _daterange_filter(), prompts) == (2, 4, 5)


def test_date_range_missing_prompt_raises():  # F12
    with pytest.raises(MissingPromptError):
        evaluate(_daterange_pop(), _daterange_filter(), prompts=None)
    with pytest.raises(MissingPromptError):  # partial supply still raises
        evaluate(_daterange_pop(), _daterange_filter(), {"And before:": "2025-06-30"})
```
- Prompts supplied → **{2,4,5}**. No/partial prompts → **raises** (F12).

### 3.4 `CAM_Tasks` — AND(custom text EQUALS, literal date <=) (F1, F4, F5, F6)

Tree (json): `AND( Text9 EQUALS 'ZIN', Start <= 2028-09-29T17:00 )`, `show_summary_rows=True`, no prompts. Note the **literal `LocalDateTime`** operand.

| UID | Text9 | start | reason |
|---|---|---|---|
| 1 | `ZIN` | 2027-01-01 | both → **in** |
| 2 | `ZIN` | 2029-01-01 | start > cutoff → **out** |
| 3 | `zin` | 2027-01-01 | case-insensitive EQUALS → **in** (F1) |
| 4 | `BOE` | 2027-01-01 | text mismatch → **out** |
| 5 | *(unset)* | 2027-01-01 | missing Text9 → no EQUALS match → **out** (F6) |
| 6 | `ZIN` | `None` | null start fails `<=` → **out** (F5) |
| 7 | `ZIN` | **2028-09-29 17:00** | start == cutoff (inclusive) → **in** (F4) |

```python
def test_cam_tasks():
    cut = dt.datetime(2028, 9, 29, 17, 0)
    f = SavedFilter(
        name="CAM_Tasks",
        show_summary_rows=True,
        criteria=AND(
            leaf(OP.EQUALS, "TEXT9", "ZIN"),
            leaf(OP.IS_LESS_THAN_OR_EQUAL_TO, "START", "2028-09-29T17:00"),
        ),
    )

    def t(uid, tx, start):
        cf = (("Text9", tx),) if tx is not None else ()
        return _task(uid, custom_fields=cf, start=start)

    s = _sched(
        [
            t(1, "ZIN", dt.datetime(2027, 1, 1, 8, 0)),
            t(2, "ZIN", dt.datetime(2029, 1, 1, 8, 0)),
            t(3, "zin", dt.datetime(2027, 1, 1, 8, 0)),
            t(4, "BOE", dt.datetime(2027, 1, 1, 8, 0)),
            t(5, None, dt.datetime(2027, 1, 1, 8, 0)),
            t(6, "ZIN", None),
            t(7, "ZIN", cut),
        ],
        labels=("Text9",),
    )
    assert evaluate(s, f) == (1, 3, 7)
```
- Expected: **{1,3,7}**.

### 3.5 `_MCexportedTasks` — `Flag6 EQUALS true` (F8, F6)

Tree (json): `EQUALS Flag6 'true'` (`v0type Boolean`).

| UID | Flag6 stored | coerced | in? |
|---|---|---|---|
| 1 | `Yes` | True | **in** |
| 2 | `No` | False | out |
| 3 | *(unset)* | False (flag default) | out (F6) |
| 4 | `true` | True | **in** |
| 5 | `1` | True | **in** |

```python
def test_mc_exported_tasks_flag6_true():
    f = SavedFilter(name="_MCexportedTasks", criteria=leaf(OP.EQUALS, "FLAG6", "true"))

    def t(uid, v):
        return _task(uid, custom_fields=(("Flag6", v),) if v is not None else ())

    s = _sched([t(1, "Yes"), t(2, "No"), t(3, None), t(4, "true"), t(5, "1")], labels=("Flag6",))
    assert evaluate(s, f) == (1, 4, 5)
```
- Expected: **{1,4,5}**. UID 3 pins F6 (missing flag → False, unlike missing text).

### 3.6 `_MCTasks` — the 8-condition AND (F2,F3,F4,F6,F7,F8,F9)

Tree (json, in order): `AND( Summary EQUALS false, Duration9 > Duration8 [TaskField], Duration8 >= 0.0d, Duration9 >= 0.0d, Text19 EQUALS '', Actual Finish EQUALS <null>, Active EQUALS true, Milestone EQUALS false )`.

Fixtures = one all-pass task + one isolated-failure task per condition + two edge inclusions. This proves **every** conjunct is live.

| UID | mutation from base | fails which cond | in? |
|---|---|---|---|
| 10 | base (see below) | — | **in** |
| 11 | `is_summary=True` | Summary=false | out |
| 12 | Dur9=`1.0d`,Dur8=`1.0d` | Dur9>Dur8 (strict) | out |
| 13 | Dur8=`-1.0d` | Dur8>=0 | out |
| 14 | Text19=`X` | Text19=='' | out |
| 15 | `actual_finish=2025-01-01` | ActualFinish is null | out |
| 16 | `is_active=False` | Active=true | out |
| 17 | `is_milestone=True` | Milestone=false | out |
| 18 | Text19 **unset** | — (unset==''  F2) | **in** |
| 19 | Dur9 **unset** | Dur9(→0)>Dur8(1) | out (F6/F7) |
| 20 | Dur8=`0.0d`,Dur9=`0.5d` | — (0>=0 inclusive) | **in** (F4/F9) |

Base (UID 10): `is_summary=False, is_milestone=False, is_active=True, actual_finish=None, custom_fields=(("Text19",""),("Duration8","1.0d"),("Duration9","3.0d"))`.

```python
def test_mc_tasks_eight_condition_and():
    f = SavedFilter(
        name="_MCTasks",
        criteria=AND(
            leaf(OP.EQUALS, "SUMMARY", "false"),
            leaf(OP.IS_GREATER_THAN, "DURATION9", field_ref="DURATION8"),
            leaf(OP.IS_GREATER_THAN_OR_EQUAL_TO, "DURATION8", "0.0d"),
            leaf(OP.IS_GREATER_THAN_OR_EQUAL_TO, "DURATION9", "0.0d"),
            leaf(OP.EQUALS, "TEXT19", ""),
            leaf(OP.EQUALS, "ACTUAL_FINISH"),  # zero operands = null-test (F3)
            leaf(OP.EQUALS, "ACTIVE", "true"),
            leaf(OP.EQUALS, "MILESTONE", "false"),
        ),
    )
    # ... build UIDs 10-20 per table ...
    assert evaluate(s, f) == (10, 18, 20)
```
- Expected: **{10,18,20}**.

### 3.7 `_RiskRegTasks` — AND(Summary=false, Text19 != '', ActualFinish null, Active=true) (F2, F3)

Tree (json). Near-inverse of `_MCTasks` on Text19 (populated), and **no** Milestone/Duration conjuncts.

| UID | mutation | in? |
|---|---|---|
| 30 | base, Text19=`R-101` | **in** |
| 31 | Text19=`""` | out (F2) |
| 32 | Text19 unset | out (unset=='' → not `!=''`, F2) |
| 33 | `is_summary=True` | out |
| 34 | `actual_finish` set | out |
| 35 | `is_active=False` | out |
| 36 | `is_milestone=True`, Text19=`R-202` | **in** (milestone unconstrained — contrast _MCTasks) |

```python
def test_risk_reg_tasks():
    f = SavedFilter(
        name="_RiskRegTasks",
        criteria=AND(
            leaf(OP.EQUALS, "SUMMARY", "false"),
            leaf(OP.DOES_NOT_EQUAL, "TEXT19", ""),
            leaf(OP.EQUALS, "ACTUAL_FINISH"),
            leaf(OP.EQUALS, "ACTIVE", "true"),
        ),
    )
    # ... build UIDs 30-36 ...
    assert evaluate(s, f) == (30, 36)
```
- Expected: **{30,36}**. UID 36 pins that this filter, unlike `_MCTasks`, does **not** exclude milestones.

---

## 4. Per-operator unit tests (`class TestOperators`)

One focused `matches(...)`-level test per `TestOperator` (SPEC line 11-13). **Ground-truth-exercised** operators (marked ✓) are additionally covered by §3; the rest are synthetic coverage the "every operator" mandate requires. Each uses a 2-task fixture on a single field.

| Op | Semantics pinned | ✓ GT | Fixture / expected |
|---|---|---|---|
| `IS_ANY_VALUE` | always True (incl. null/blank) | | Text9=`X` and unset → both match |
| `EQUALS` (text) | case-insensitive `==`; null-aware | ✓ | `zin`/`ZIN` match `'ZIN'`; `BOE` no |
| `EQUALS` (zero-operand) | LHS is null/blank | ✓ | `actual_finish None`→match; set→no |
| `DOES_NOT_EQUAL` | negation of EQUALS; unset=='' | ✓ | `R-1` vs `''`: `''`→no, `R-1`→yes |
| `CONTAINS` | case-insensitive substring | ✓ | `Pre-SVT-x` contains `svt` |
| `DOES_NOT_CONTAIN` | negation of CONTAINS | ✓ | complement |
| `CONTAINS_EXACTLY` | **case-SENSITIVE** substring ⚠ | | `SVT` matches `SVT-01`; `svt` does not — *(assumed MSP semantics; flag for operator confirmation, not in any real filter)* |
| `IS_GREATER_THAN` | strict `>` (numeric/duration/date) | ✓ | 3d>1d yes; 1d>1d no |
| `IS_GREATER_THAN_OR_EQUAL_TO` | `>=` inclusive | ✓ | 0d>=0d yes |
| `IS_LESS_THAN` | strict `<` | | 04-01 < 06-30 yes |
| `IS_LESS_THAN_OR_EQUAL_TO` | `<=` inclusive | ✓ | ==bound yes |
| `IS_WITHIN` | `a <= x <= b`, 2 operands, inclusive both ends | | x=bound-a and bound-b → in; outside → out |
| `IS_NOT_WITHIN` | `NOT(a<=x<=b)` | | complement of IS_WITHIN |
| `AND` | all children True | ✓ | 2-child, flip one → False |
| `OR` | any child True | | 2-child; also **nested `AND` inside `OR`** to pin recursion |

```python
def test_or_and_nested_recursion():  # no real filter uses OR — pins the tree engine
    # OR( AND(Flag6=true, Text9='ZIN'), Name CONTAINS 'SVT' )
    crit = OR(
        AND(leaf(OP.EQUALS, "FLAG6", "true"), leaf(OP.EQUALS, "TEXT9", "ZIN")),
        leaf(OP.CONTAINS, "NAME", "SVT"),
    )
    s = _sched(
        [
            _task(1, name="A", custom_fields=(("Flag6", "Yes"), ("Text9", "ZIN"))),  # left AND
            _task(2, name="SVT-9"),  # right leaf
            _task(3, name="B", custom_fields=(("Flag6", "Yes"), ("Text9", "BOE"))),  # neither
        ],
        labels=("Flag6", "Text9"),
    )
    assert evaluate(SavedFilter(name="x", criteria=crit), s) == (1, 2)
```

## 5. Typed-coercion unit tests (`class TestCoercion`)

Isolate the operand coercion the evaluator relies on (F8/F9 + dates), independent of the tree.

- `test_bool_coercion`: `{"true","True","yes","Yes","1"}`→True; `{"false","no","0","",None}`→False (F8).
- `test_duration_coercion`: `"0.0d"`→0, `"1.0d"`→480, `"3.0d"`→1440, `"0.5d"`→240, `"-1.0d"`→-480 (F9); a bare `"5"` and unset both handled (unset→0 in a duration context, F6).
- `test_date_literal_coercion`: `"2028-09-29T17:00"`→`dt.datetime(2028,9,29,17,0)`; comparison respects time-of-day (a `2028-09-29 17:01` start is `> cutoff`).
- `test_field_to_field_resolution`: `field_ref="DURATION8"` resolves the *same task's* Duration8; both sides coerced before compare (F7).
- `test_null_lhs_all_ordered_ops_false`: `start=None`/`finish=None`/`Duration unset` → every `<,<=,>,>=` returns False for date/datetime; duration-null coerces to 0 (documented divergence: date-null is "no value", duration-null is 0).

## 6. Edge-case tests (`class TestEdges`) — the explicitly-requested set

- `test_case_insensitive_text` (F1): `svt-` ⊂ `CONTAINS 'SVT-'`; `ZIN`==`zin`.
- `test_null_vs_empty_text` (F2/F3): a matrix asserting, for the SAME field, `EQUALS ''` matches {`""`, unset} not {`"x"`}; `DOES_NOT_EQUAL ''` matches {`"x"`} not {`""`, unset}; and the date null-test (`ACTUAL_FINISH EQUALS` no-operand) matches `None` only.
- `test_inclusive_range_boundaries` (F4): dedicated task with `start == cutoff` and `finish == bound` → included; +1 minute → excluded.
- `test_missing_custom_field_by_type` (F6): one schedule, three filters over a task carrying **no** customs — `EQUALS TEXT9 'ZIN'`→no match; `EQUALS FLAG6 'true'`→no match / `EQUALS FLAG6 'false'`→**match** (flag defaults False); `IS_GREATER_THAN_OR_EQUAL_TO DURATION8 '0.0d'`→**match** (missing→0). Pins that "missing" means different things per family.
- `test_file_order_preserved` (F11): shuffle UIDs in the tuple; assert `evaluate` returns them in schedule task order, not sorted.
- `test_empty_schedule_returns_empty`: `evaluate(_sched([]), any_filter) == ()`.
- `test_show_summary_rows_flag_carried`: assert `SavedFilter.show_summary_rows` round-trips (`True` for `Date Range...`/`CAM_Tasks`/`Status`/`CA-WBS,OBS.CAM`, `False` for the SVT/`_MC*` filters — json:2). **Behavioral summary-row inclusion** (a matching leaf pulls in its parent summary rows) is a separate test that depends on outline-parent derivation from `outline_level` (`task.py:57`); scope it as `test_show_summary_rows_includes_parents` with a 3-row outline (summary L1 non-matching, child L2 matching) and assert the summary UID is added **only when** `show_summary_rows=True`. Flag this as dependent on the design's parent-resolution helper.

## 7. Integration test — raw-name ↔ alias resolution (`class TestFieldResolver`)

Pins the **KEY INTEGRATION CHALLENGE** (`MSP-FILTERS-SPEC.md:32-37`): filters reference RAW names (`TEXT9`), but `Task.custom_fields` keys by the operator's **alias** when one is set (`task.py:131-134`; `custom_field_labels` at `schedule.py:49`).

- `test_resolver_raw_name_no_alias`: task keyed `("Text9","ZIN")`, filter `EQUALS TEXT9 'ZIN'` → match (the common case, already used throughout §3).
- `test_resolver_alias_bridged`: task keyed by alias `("IPT","ZIN")`, schedule advertises raw→label map `{"Text9":"IPT"}`, filter `EQUALS TEXT9 'ZIN'` → **match**. This documents the design requirement that the resolver accept a raw-MSP-id → label map (whether carried on `Schedule` as a new `custom_field_raw_map`, or attached to `SavedFilter`). Include the *negative*: with no bridge map, the raw lookup misses → no match, proving the map is load-bearing.

---

## 8. Coverage / gate notes

- All tests are pure-Python, no `@pytest.mark.parity` needed (they are unit tests over hand-authored fixtures, not reference-tool parity). They will count toward the engine ≥85% coverage gate for the new `engine/msp_filters.py`.
- A **future** optional `@pytest.mark.parity` test could load the real `Large Test File Leveled.mpp` via MPXJ and assert `evaluate` reproduces MSP's own filtered row set — but that needs Java + the reference `.mpp`, so it is out of scope for this pure-Python matrix (the hand-authored trees here ARE the frozen ground truth).
- Total: **~10 real-filter tests + ~14 operator tests + ~5 coercion tests + ~7 edge tests + ~3 resolver tests ≈ 39 tests**, every real filter's expected UID set fixed to the MPXJ dump.

### Expected-UID quick reference (the pins)

| Filter | Criteria (from json) | Expected UIDs |
|---|---|---|
| All Tasks | null | 1,2,3 (all) |
| SVT- | NAME CONTAINS 'SVT-' | 1,2,5 |
| No SVT- | NAME DOES_NOT_CONTAIN 'SVT-' | 3,4,6 |
| SVT | NAME CONTAINS 'SVT' | 1,2,3,5 |
| Date Range... | Finish>=P1 AND Start<=P2 | 2,4,5 (prompts set) / raises (unset) |
| CAM_Tasks | Text9=='ZIN' AND Start<=2028-09-29T17:00 | 1,3,7 |
| _MCexportedTasks | Flag6==true | 1,4,5 |
| _MCTasks | 8-way AND | 10,18,20 |
| _RiskRegTasks | Summary=false AND Text19!='' AND ActFin null AND Active=true | 30,36 |

**Key source references:** ground truth `views_leveled.json:2` and `MSP-FILTERS-SPEC.md:18-26`; model surface `task.py:77-84,106-108,134,141-146` and `schedule.py:49`; construction idiom `test_margin.py:25-31` / `test_grouping.py:26-42`; behavior being superseded (case-sensitive filter) `grouping.py:15,92-115`; minutes/day axis `units.py:33`.
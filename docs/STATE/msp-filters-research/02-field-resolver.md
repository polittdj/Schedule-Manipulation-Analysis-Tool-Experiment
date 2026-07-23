I have everything needed. Here is the design section.

---

# Feature #10 — Design: the raw-MSP-field → task-value RESOLVER

Scope of this section: given a **raw MS Project field name** exactly as the saved filters/groups carry it (`Task Name`, `Start`, `Actual Finish`, `Duration`, `% Complete`, `Summary`, `Milestone`, `Active`, `Critical`, `Priority`, `Text9`, `Flag6`, `Duration8`, `Number19`, …), return the current task's value as a **typed Python value** (`str | int-minutes | float | bool | datetime | None`) so the faithful filter evaluator (`engine/msp_filters.py`, a sibling topic) and the session-wide grouping can compare it against a literal / another field / a prompt.

## 0. The crux finding (verified against the real file)

The tool's existing field accessor **cannot resolve the fields the real filters reference**, for two independent reasons:

1. `engine/grouping.py:84 field_value()` only knows **6 standard fields** (`STANDARD_FIELDS`, grouping.py:55-64: WBS, Activity Type, Constraint Type, Resource, Critical, % Complete) plus custom fields *looked up by operator label*. None of `Task Name / Start / Finish / Actual Finish / Duration / Summary / Milestone / Active / Priority` is in that map, so it returns `None` (grouping.py:88-89).
2. **Custom fields are stored by operator LABEL (alias), not by raw id.** `Task.custom_fields` is a tuple of `(label, value)` (task.py:131-146), where the label is the MSPDI `Alias` when present, else `FieldName`, else the numeric `FieldID` — chosen at `importers/mspdi.py:481` (`_text(ea,"Alias") or _text(ea,"FieldName") or field_id`). The raw name (`Text9`) and the numeric `FieldID` are **discarded** after the label is chosen. `Schedule.custom_field_labels` (schedule.py:47-49) persists only the labels.

I confirmed this against the real target file `tests/fixtures/golden/ssi_uid152_leveled/Large_Test_File_Leveled.mspdi.xml.gz` (the MPXJ conversion of `Large Test File Leveled.mpp`). Its `<ExtendedAttributes>` map the raw names the filters use to **aliases**:

| raw name in filter | Alias (the stored label) | current `field_value("<raw>")` |
|---|---|---|
| `Text9` (CAM_Tasks: `= 'ZIN'`) | `IPT/ SUB` | ❌ `None` |
| `Flag6` (_MCexportedTasks: `= true`) | `SSI SRA Event` | ❌ `None` |
| `Text19` (_MCTasks / _RiskRegTasks) | `Risk ID` | ❌ `None` |
| `Duration8` / `Duration9` (_MCTasks) | `Best Case Duration` / `Worst Case Duration` | ❌ `None` |
| `Text10`,`Text20`,`Text21`,`Text30`,`Number19` (groups) | `Critical Path (SSI Tools)`,`CA-WBS`,`CAM`,`Work Package ID`,`Driving Slack` | ❌ `None` |
| `Text7` (group CA-WBS,OBS.CAM) | *(no alias)* → label **is** `Text7` | ✅ works today |

So a resolver keyed on the raw name **must** carry a raw-name→label indirection; today that mapping does not survive import.

## 1. Task attributes, types, and units (the resolvable core)

Every field below is a stored value on `model/task.py` (dates default `None` = "source didn't provide it"; durations are **integer working minutes**, 480 = 1 day). CPM dates/free-float are *derived, never stored* (task.py:5-9) — see the gap list for the derived ones.

| Raw MSP field (MPXJ `fieldEnum`) | Task attribute | Python type | Units / notes |
|---|---|---|---|
| `Task Name` (NAME) | `name` | `str` | always present (mspdi.py:540 falls back to `Task <uid>`) |
| `Unique ID` (UNIQUE_ID) | `unique_id` | `int` | sole identity key |
| `WBS` (WBS) | `wbs` | `str \| None` | task.py:49 |
| `Outline Level` (OUTLINE_LEVEL) | `outline_level` | `int` | nesting depth (0 = project summary), task.py:54-57 |
| `Duration` (DURATION) | `duration_minutes` | `int` minutes | task.py:60; **no coercion** — already minutes |
| `Remaining Duration` | `remaining_duration_minutes` | `int \| None` | task.py:64 |
| `Baseline Duration` | `baseline_duration_minutes` | `int \| None` | task.py:65 |
| `% Complete` (PERCENT_COMPLETE) | `percent_complete` | `float` 0–100 | task.py:92 |
| `Physical % Complete` | `physical_percent_complete` | `float \| None` | task.py:93 |
| `Summary` (SUMMARY) | `is_summary` | `bool` | task.py:78 (`or uid==0`, mspdi.py:550) |
| `Milestone` (MILESTONE) | `is_milestone` | `bool` | task.py:77 |
| `Active` (ACTIVE) | `is_active` | `bool` | task.py:80; default `True` |
| `Task Mode` (TASK_MODE) | `is_manual` | `bool` | task.py:84; render "Manually Scheduled"/"Auto Scheduled". MSPDI carries `<Manual>0/1`, **not** `<TaskMode>` (0 rows) — MPXJ derives Task Mode from `<Manual>` |
| `Critical` (CRITICAL) | `stored_is_critical` | `bool \| None` | task.py:102; **prefer stored**, fall back via `is_effective_critical(task, recomputed)` (metrics/_common.py:102-111) |
| `Total Slack` (TOTAL_SLACK) | `stored_total_float_minutes` | `int \| None` minutes | task.py:101 (`<0` = behind constraint); fallback `effective_total_float` (_common.py:89-99) |
| `Constraint Type` (CONSTRAINT_TYPE) | `constraint_type` | `ConstraintType` enum | task.py:87; `.value` for string compare |
| `Constraint Date` | `constraint_date` | `datetime \| None` | task.py:88 |
| `Deadline` (DEADLINE) | `deadline` | `datetime \| None` | task.py:89 |
| `Start` (START) | `start` | `datetime \| None` | current forecast start |
| `Finish` (FINISH) | `finish` | `datetime \| None` | current forecast finish |
| `Actual Start` (ACTUAL_START) | `actual_start` | `datetime \| None` | task.py:107 |
| `Actual Finish` (ACTUAL_FINISH) | `actual_finish` | `datetime \| None` | task.py:108; used for `EQUALS <null>` tests in _MCTasks/_RiskRegTasks |
| `Baseline Start` / `Baseline Finish` | `baseline_start` / `baseline_finish` | `datetime \| None` | task.py:109-110 |
| `Cost` (COST) | `cost` | `float \| None` | may be negative (credits) |
| `Actual Cost` (ACTUAL_COST) | `actual_cost` | `float \| None` | ACWP basis |
| `Baseline Cost` | `budgeted_cost` | `float` ≥0 | BAC; clamps neg→0 (mspdi.py:614) |
| `Work` (WORK) | `work_minutes` | `int \| None` minutes | task.py:73 |
| `Actual Work` | `actual_work_minutes` | `int \| None` minutes | task.py:74 |
| `Resource Names` (RESOURCE_NAMES) | `resource_names` | `tuple[str,…]` | multi-valued; scalarize as `"; ".join(...)` (mirrors grouping.py:59) |
| `Notes` | `notes` | `str \| None` | task.py:129 |
| `Calendar` | `calendar_uid` | `int \| None` | task.py:53 |

## 2. Custom-field families (Text/Flag/Number/Duration/Date/Cost/Start/Finish/Outline Code)

The importer stores every populated extended attribute as `(label, value)` where **value is the raw `<Value>` text verbatim** (mspdi.py:485-503) — no type coercion happens at import. I verified the on-disk string formats in the real file:

| Family (raw prefix) | MPXJ data type | Stored `<Value>` example (real file) | Resolver returns | Coercion |
|---|---|---|---|---|
| `Text1`–`Text30` | STRING | `"O131TU"`, `"TEST Risk"` | `str` | none (verbatim) |
| `Outline Code1`–`10` | STRING | code string | `str` | none |
| `Flag1`–`Flag20` | BOOLEAN | `"1"` | `bool` | `v.strip().lower() in {"1","true","yes"}` |
| `Number1`–`Number20` | NUMERIC | `"641.05"` | `float` | `parse_float` (_common.py:147) |
| `Duration1`–`Duration10` | DURATION | `"PT244H48M0S"` (ISO-8601, `<DurationFormat>` sibling) | `int` **minutes** | `iso_duration_to_minutes` (_common.py:100) |
| `Cost1`–`Cost10` | CURRENCY | decimal string | `float` | `parse_float` |
| `Date1`–`Date10`, `Start1`–`10`, `Finish1`–`10` | DATE | `"2026-03-05T08:00:00"` | `datetime \| None` | `parse_datetime` (_common.py:70) |

**Critical consequence:** because the custom `Duration8/9` value is an ISO string, and the filter `_MCTasks` compares `Duration9 IS_GREATER_THAN Duration8` (field-to-field) and `Duration8 >= 0.0d`, the resolver **must** coerce custom durations to the same int-minutes axis the core `Duration` uses, so both sides of a field-to-field comparison are minutes. Likewise custom `Flag6` stored `"1"` must coerce to `bool` so it can be compared to the filter literal `true`.

The family is determined **by the raw-name prefix, not by the stored value** (deterministic: `Duration8` → DURATION regardless of what string sits there). MPXJ's `getDataType()` for each family (probed) confirms the mapping above.

> Layering note: `iso_duration_to_minutes` / `parse_datetime` / `parse_float` live in `importers/_common.py`. The resolver is engine-layer. Either import them from there (no cycle — `_common` imports only `model`) or relocate these four pure coercers to a neutral module (e.g. `model/units.py` already hosts `days_to_minutes`). Recommend a small `engine`-visible import of `_common`; note it for the reviewer.

## 3. The exact custom-field resolution PATH (and the one importer change it requires)

Resolution for a custom raw name is a **two-hop lookup** the model cannot do today because hop 1's table isn't persisted:

```
raw name "Text9"
  ── hop 1 ──▶  label  "IPT/ SUB"      (raw-name → label map; MISSING today)
  ── hop 2 ──▶  task.custom_field("IPT/ SUB")  → "ZIN"    (task.py:141)
  ── coerce ─▶  str  "ZIN"             (Text family → no coercion)
```

Hop 1's data exists at import time — `_parse_extended_attribute_defs` (mspdi.py:469-482) already reads `<FieldName>` (the raw name) and `<Alias>` for every def — but it collapses them to one label and returns only `{FieldID: label}`. Nothing carries `FieldName` onto the `Schedule`.

**Required minimal change (recommended option A):** persist a raw-name→label map on the `Schedule`, built from *all* extended-attribute defs (not just populated ones, so an unpopulated referenced field resolves to `None` = "empty" rather than "unknown").

- Add to `model/schedule.py`: `custom_field_by_raw_name: tuple[tuple[str, str], ...] = ()` — `(raw_field_name, label)` pairs (frozen/hashable, mirrors `custom_field_labels`). Expose a cached `dict` view like `custom_field_map` (task.py:136-139).
- In `importers/mspdi.py`, have `_parse_extended_attribute_defs` additionally return `{FieldName: chosen_label}` (it already has both strings at line 481); thread it into the `Schedule(...)` construction (mspdi.py:186-200) next to `custom_field_labels`.
- Alias-free fields (`Text7`) map `raw==label`, so they keep working; the resolver's fallback `.get(raw, raw)` also covers any file that never carried the def.
- Same wiring is free for the XER path if/when P6 filters are added; XER has no MSPDI aliases, so `raw==label` there.

Resolver custom hop (engine layer):

```python
def _resolve_custom(schedule, task, raw_field):  # raw_field e.g. "Duration8"
    label = schedule.custom_field_by_raw_name_map.get(raw_field, raw_field)
    raw = task.custom_field(label)  # str | None (task.py:141)
    if raw is None:
        return None  # field empty on this task
    return _coerce_by_family(raw_field, raw)  # §2 table
```

Edge cases to encode: (a) a stored value that is empty string `""` — the importer skips `Value is None` but an explicit `""` can appear (e.g. `_MCTasks` tests `Text19 EQUALS ''`); `custom_field` returns the stored string, so `""` must survive as `""`, not become `None` — the evaluator's empty/`null` distinction depends on it. (b) duplicate aliases across two raw ids (rare) collide only at hop 2 (`custom_field` returns the first `(label,value)` match, task.py:143-145) — document as a known approximation. (c) unpopulated-but-defined field → hop 1 resolves the label, hop 2 returns `None`.

## 4. GAP LIST — fields the current model cannot resolve

| Field (referenced by) | In MSPDI/.mpp? | In model? | Verdict |
|---|---|---|---|
| **`Priority`** (groups "Priority", "Duration then Priority", "…Keeping Outline Structure") | **Yes** — `<Priority>` on every task (2126 rows; all `500` in this file) | **No** attribute | **Fixable gap.** Add `priority: int = 500` to `Task`, parse `<Priority>` in mspdi.py. Until then, grouping by Priority is impossible. |
| **`Outline Number`** (group "…Keeping Outline Structure") | **Yes** — `<OutlineNumber>` dotted string (`"1.1"`) | **No** (only `outline_level` int depth, task.py:54) | **Fixable gap.** The dotted code ≠ the depth int. Add `outline_number: str \| None`, parse `<OutlineNumber>`. |
| **`Status`** (group "Status") | **No** — 0 `<Status>` rows (MSP computes it on display) | Derivable | **Derivable, not stored.** Compute Complete / On Schedule / Late / Future from `percent_complete` + `finish` vs `Schedule.status_date` (all present). Resolver can synthesize it; document the formula. |
| **`Board Status`, `Sprint`** (groups "Board Status", "Sprint") | **No** — 0 rows (Agile add-in fields, not emitted to MSPDI) | No | **Hard gap.** The source does not carry them; cannot be reproduced. Resolver must return `UNRESOLVED` and the UI degrade gracefully (offer the group but show one "n/a" bucket). |
| **`Project`** (group "…Keeping Outline Structure") | Single-file: constant (per-task subproject name absent) | No | **Degrade.** Return `Schedule.project_title or Schedule.name` (schedule.py:33/31) as a constant group. |
| **`Free Slack`** (potential filter) | Not stored (`<FreeSlack>` unreliable) | Derived by engine (`CPMResult`) | **Resolvable via engine, not the task.** If needed, resolver takes the CPM result; out of scope for a task-only resolver. |
| **`ID`** (row id) | Yes (`<ID>`) | **No** by design (`unique_id` is the sole key, task.py:1-3, renumbering ID deliberately dropped) | **Intentional gap.** Filters keyed on row `ID` are non-forensic; document as unsupported. |
| `is_level_of_effort` (`LOE`) | Not in MSPDI (mspdi.py:551 hard-`False`) | attribute exists but always `False` | Note: a filter on LOE would read the custom `Flag1`="LOE" alias instead, which *is* resolvable via the custom path. |

Everything in §1 and §2 (all core scheduling fields + the six custom families: Text1-30, Flag1-20, Number1-20, Duration1-10, Date1-10, Cost1-10, Start1-10, Finish1-10, Outline Code1-10) **is** resolvable once the §3 raw-name→label map is persisted. The only genuinely unreproducible fields are `Board Status`/`Sprint` (source-absent) and row `ID` (by design).

## 5. Resolver API

New module `src/schedule_forensics/engine/msp_field_resolver.py` — the single chokepoint used by `engine/msp_filters.py` (evaluator) and the session-wide grouping:

```python
FieldValue = str | int | float | bool | dt.datetime | None  # int = working minutes


class FieldKind(StrEnum):
    STRING
    NUMERIC
    DURATION_MINUTES
    DATE
    BOOLEAN
    PERCENT
    CURRENCY
    UNRESOLVED


@dataclass(frozen=True)
class ResolvedField:
    value: FieldValue  # coerced task-side value (§1/§2)
    kind: FieldKind  # so the evaluator coerces the literal to match
    resolvable: bool  # False ⇒ a §4 hard gap (Board Status/Sprint/ID)


def resolve_field(
    schedule: Schedule, task: Task, raw_field: str, *, field_enum: str | None = None
) -> ResolvedField:
    ...
    # Normalizes raw_field via field_enum first (unambiguous: "TEXT9","ACTUAL_FINISH"),
    # else the raw display name. Order: core-field table (§1) → custom family (§2/§3) → UNRESOLVED.


def field_kind(raw_field: str, *, field_enum: str | None = None) -> FieldKind:
    ...
    # Type of a field WITHOUT a task — lets the evaluator coerce filter literals
    # ("0.0d" → minutes, "true" → bool, "2028-09-29T17:00" → datetime) before comparison.


def is_resolvable(schedule: Schedule, raw_field: str, *, field_enum: str | None = None) -> bool:
    ...
    # Drives UI: hide/annotate a filter/group referencing a §4 hard-gap field.
```

Design points:
- **Prefer `field_enum`** (present in the sidecar `views_leveled.json`: `"NAME"`,`"TEXT9"`,`"ACTUAL_FINISH"`) as the canonical key; it disambiguates the display name and is 1:1 with the raw family. Keep a small `MPXJ_ENUM → canonical` table; fall back to the raw display name.
- **`field_kind` is the evaluator's contract** — it must know a field's type before it has a task so it can coerce the RHS literal / the field-to-field operand into the same axis. The type is a pure function of the raw name (prefix family + core table), so `field_kind` needs no task.
- Core fields need **no coercion** (already typed on `Task`); only custom-family values (stored strings, §2) are coerced. This keeps the hot path cheap.
- `Critical`/`Total Slack` route through `metrics/_common.is_effective_critical` / `effective_total_float` (_common.py:89-111) so the resolver's notion of "critical" matches the rest of the engine (stored flag preferred, CPM fallback) — the resolver must be handed the recomputed float, or default to the stored-only value when no CPM result is in scope.

## Files referenced
- `src/schedule_forensics/model/task.py` (attributes: 43-135; `custom_field` 141-146; `custom_field_map` 136-139)
- `src/schedule_forensics/model/schedule.py` (`custom_field_labels` 47-49 — add `custom_field_by_raw_name` beside it)
- `src/schedule_forensics/engine/grouping.py` (`STANDARD_FIELDS` 55-64; `field_value` 84-89 — the 2-reason gap)
- `src/schedule_forensics/importers/mspdi.py` (`_parse_extended_attribute_defs` 469-482 — reads `<FieldName>` at 481 then discards it; `_task_custom_fields` 485-503; task build 537-579; `<Priority>`/`<OutlineNumber>` not parsed)
- `src/schedule_forensics/importers/_common.py` (coercers: `parse_datetime` 70-92, `iso_duration_to_minutes` 100-123, `parse_float` 147-162, `parse_percent` 254-264)
- `src/schedule_forensics/engine/metrics/_common.py` (`effective_total_float` 89-99, `is_effective_critical` 102-111)
- Ground truth: `tests/fixtures/golden/ssi_uid152_leveled/Large_Test_File_Leveled.mspdi.xml.gz` (real aliases: `Text9`→`IPT/ SUB`, `Flag6`→`SSI SRA Event`, `Duration8/9`→`Best/Worst Case Duration`, `Number19`→`Driving Slack`; `Priority`/`OutlineNumber`/`Manual` present, `Status`/`BoardStatus`/`Sprint`/`TaskMode` absent)
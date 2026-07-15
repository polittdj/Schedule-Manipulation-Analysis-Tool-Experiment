I now have the complete, authoritative picture from both the compiled bytecode (the ground truth in the shipped jar) and the confirmed source. Here is the design section.

---

# MS Project Filter Operator Semantics — exact reproduction spec

**Authority:** every rule below is derived from the **compiled MPXJ 16.2.0 jar** (`tools/mpxj/lib/mpxj-16.2.0.jar`) via `javap -p -c`, cross-checked against the current MPXJ source. Where the compiled behavior differs from a casual reading of the source, **the bytecode wins** (it is what actually produced `views_leveled.json`). Two places where I caught the online source summary being imprecise are flagged.

The evaluator to port lives in two Java classes:
- `org.mpxj.GenericCriteria.evaluate(FieldContainer, Map<GenericCriteriaPrompt,Object>)` — the per-node driver (LHS fetch + normalize, RHS resolve, dispatch).
- `org.mpxj.TestOperator` (abstract `evaluate(Object lhs, Object rhs)` with 14 anonymous subclasses `$1`–`$14`, plus the protected helpers `getSingleOperand`, `evaluateWithin`, `evaluateCompareTo`, `evaluateContains`, `evaluateContainsExactly`).

A filter is a **tree** of `GenericCriteria` nodes. Leaf nodes carry `leftValue` (a `FieldType`), an `operator`, and up to two right-hand values (`m_workingRightValues`, always a length-2 `Object[]`). Branch nodes carry operator `AND`/`OR` and a `criteriaList` of children.

---

## 1. The node evaluation pipeline (`GenericCriteria.evaluate`)

For every node, in this exact order:

### 1a. Fetch and normalize the LHS (the task's field value)
```
lhs = (leftValue == null) ? null : container.get(leftValue)
```
Then normalize **by the field's declared `DataType`** (from `FieldType.getDataType()`):

| DataType | LHS normalization (applied to the *field* value) |
|---|---|
| `DATE` | if non-null → `getDayStartDate(lhs)` = **truncate to that calendar day at 00:00** (time-of-day discarded). null stays null. |
| `DURATION` | if non-null → `lhs.convertUnits(HOURS)`. **if null → `Duration(0, HOURS)`** (null becomes zero-hours, never stays null). |
| `STRING` | `lhs == null ? "" : lhs` (**null becomes empty string**). |
| everything else (`BOOLEAN`, `NUMERIC`, `PERCENTAGE`, `INTEGER`, `CONSTRAINT`, `PRIORITY`, `TASK_MODE`, …) | **no normalization** — value passed through as-is, including null. |

`DataType` enum ordering (for the port's mapping): `STRING(0), DATE(1), CURRENCY(2), BOOLEAN(3), NUMERIC(4), DURATION(5), …, PERCENTAGE(7), …, PRIORITY(11), …, INTEGER(16), …, CONSTRAINT(9)`. Only `DATE`, `DURATION`, `STRING` get special-cased; all others fall through the `default` branch untouched.

### 1b. Resolve the RHS (`m_workingRightValues`, a 2-element array)
- If the node has **no symbolic values** → RHS array is used verbatim.
- If it has symbolic values (`m_symbolicValues` was set true because some `setRightValue` got a `FieldType`) → run `processSymbolicValues` (section 3).

### 1c. Dispatch
```
if operator in {AND, OR}: result = evaluateLogicalOperator(...)   // recurse over children
else:                     result = operator.evaluate(lhs, rhsArray)
```

**Key structural fact:** the two RHS slots (`getValue(0)`, `getValue(1)`) are always packaged as an `Object[]` and handed to `operator.evaluate` as the single `rhs` argument. Each operator then either pulls one operand out (`getSingleOperand` → `rhs[0]`) or uses both (`evaluateWithin` → `rhs[0]`, `rhs[1]`).

---

## 2. Per-operator semantics table

`lhs` = normalized field value (section 1a). `op1 = getSingleOperand(rhs) = rhs[0]` (unwraps the array). Inner-class refs are the `TestOperator$N` from the jar.

| Operator | Inner class | Exact logic | Notes |
|---|---|---|---|
| **IS_ANY_VALUE** | `$1` | `return true` (unconditionally) | Never filters anything out. |
| **IS_WITHIN** | `$2` | `evaluateWithin(lhs, rhs)` | Inclusive both ends, bounds may be given in either order. See §4b. |
| **IS_GREATER_THAN** | `$3` | `evaluateCompareTo(lhs, rhs) > 0` | Uses null-aware compareTo (§4a). |
| **IS_LESS_THAN** | `$4` | `evaluateCompareTo(lhs, rhs) < 0` | |
| **IS_GREATER_THAN_OR_EQUAL_TO** | `$5` | `evaluateCompareTo(lhs, rhs) >= 0` | |
| **IS_LESS_THAN_OR_EQUAL_TO** | `$6` | `evaluateCompareTo(lhs, rhs) <= 0` | |
| **EQUALS** | `$7` | `lhs==null ? (op1==null) : lhs.equals(op1)` | Java `.equals`; for String this is **case-sensitive** exact match. |
| **DOES_NOT_EQUAL** | `$8` | `lhs==null ? (op1!=null) : !lhs.equals(op1)` | Exact inverse of EQUALS. |
| **CONTAINS** | `$9` | `evaluateContains(lhs, rhs)` | **Case-INsensitive** substring (§4c). |
| **IS_NOT_WITHIN** | `$10` | `!evaluateWithin(lhs, rhs)` | |
| **DOES_NOT_CONTAIN** | `$11` | `!evaluateContains(lhs, rhs)` | Case-insensitive. |
| **CONTAINS_EXACTLY** | `$12` | `evaluateContainsExactly(lhs, rhs)` | **Case-SENSITIVE substring** — NOT equality (§4d). |
| **AND** | `$13` | `TestOperator.evaluate` throws `UnsupportedOperationException` | Branch logic handled in `GenericCriteria`, never via `TestOperator.evaluate`. |
| **OR** | `$14` | `TestOperator.evaluate` throws `UnsupportedOperationException` | Same. |

---

## 3. RHS value kinds: literal vs field-to-field vs prompt

Each of the two RHS slots is one of three things, distinguished by the probe's `v0type`:

### 3a. Literal (`v0type` = `String` / `Boolean` / `LocalDateTime` / `Duration`)
Stored at `setRightValue` time. **Durations are pre-converted to HOURS on ingest** (`setRightValue`: if `Duration.getUnits() != HOURS` → `convertUnits(HOURS)`). So `"0.0d"` (0 days) is stored as `Duration(0, HOURS)`. **Literal dates are NOT truncated** — `2028-09-29T17:00` keeps its 17:00 time (contrast with the LHS date, which *is* truncated to 00:00). Strings/Booleans stored verbatim.

### 3b. Field-to-field / symbolic (`v0type` = `TaskField`, i.e. RHS is a `FieldType`)
Sets `m_symbolicValues = true`. At evaluation, `processSymbolicValues` fetches the **other field's** value from the same task (`container.getCachedValue(type)`) and normalizes it **by that field's DataType**:

| RHS field DataType | symbolic RHS normalization |
|---|---|
| `DATE` | if non-null → `getDayStartDate(value)` (truncate to day). null stays null. |
| `DURATION` | **if non-null AND units ≠ HOURS → `convertUnits(HOURS)`; ELSE → `Duration(0, HOURS)`.** ⚠ see quirk below. |
| `STRING` | `value == null ? "" : value`. |
| other | passed through unchanged (incl. null). |

⚠ **Quirk to replicate (confirmed in bytecode, `processSymbolicValues` offsets 114–162):** for a symbolic **DURATION** RHS, the `else` branch fires when the field is null **OR already stored in HOURS**, replacing it with **zero hours**. So if a referenced Duration field is natively stored in HOURS, MPXJ compares against **0h**, not its real value. In the LHS path the same-type field is converted unconditionally, so LHS and symbolic-RHS durations are **not** normalized symmetrically. For the `_MCTasks` filter's `Duration9 > Duration8` this only bites if `Duration8` is stored in HOURS in the .mpp; MSP custom duration fields are usually stored in days, so it typically doesn't fire — but for bit-for-bit parity the port must implement the exact `null || units==HOURS → 0h` rule and the parity test must confirm against MPXJ on the real file, not assume.

### 3c. Interactive prompt (`v0type` = `GenericCriteriaPrompt`)
Also flows through `processSymbolicValues` (a prompt is not a `FieldType`, so it hits the `else if (value instanceof GenericCriteriaPrompt && promptValues != null)` branch):
```
value = promptValues.get(prompt)   // looked up by prompt identity from the operator-supplied map
```
- The substituted value is the **operator's typed input** (a `LocalDateTime` for the "Date Range…" prompts, etc.). It is inserted **raw** — `processSymbolicValues` does **not** re-normalize a prompt-substituted value by DataType (no day-truncation, no hour-conversion applied to the prompt answer). So the prompt answer is compared as given.
- If `promptValues` is null or lacks the key → the slot becomes **null**, and the operator then sees a null operand (which, per §4a, makes null sort as "greater"). The port should require prompt values before evaluating a prompted filter, matching MSP's modal prompt.
- The two prompts in the real file: `"Show tasks that start or finish after:"` (→ `Finish >= answer`) and `"And before:"` (→ `Start <= answer`), combined under `AND`.

---

## 4. The comparison primitives (exact, from bytecode)

### 4a. `evaluateCompareTo(lhs, rhs)` → int  ⚠ null ordering
```
rhs = getSingleOperand(rhs)                       // rhs[0]
if (lhs == null || rhs == null)
    return (lhs == rhs) ? 0 : (lhs == null ? 1 : -1);
else
    return ((Comparable) lhs).compareTo(rhs);
```
**Null ordering is the opposite of the online-source summary.** Bytecode (`evaluateCompareTo` offsets 24–34) is unambiguous: **a null LHS returns +1 (sorts as GREATER than any non-null RHS); a null RHS returns −1; both null returns 0.** Consequences for a null field value (only reachable for DATE and the pass-through numeric/boolean types — STRING and DURATION LHS are never null after normalization):
- `IS_GREATER_THAN` / `IS_GREATER_THAN_OR_EQUAL_TO` a non-null value → **TRUE** (null counts as bigger).
- `IS_LESS_THAN` / `IS_LESS_THAN_OR_EQUAL_TO` a non-null value → **FALSE**.
- Against a null RHS: `>=`/`<=` where both null → compareTo 0 → the `>=`/`<=`/EQUALS-style tests pass.

The Python port must implement this tri-state null rule explicitly; do **not** use Python's native `None` comparison (which raises).

`compareTo` is delegated to the value type:
- **Duration.compareTo** (bytecode confirmed): if units differ, convert RHS into LHS's units (factors 480 min/day, 2400 min/week, 20 day/month); then if the two amounts are equal within **1e-5** (`durationValueEquals` → `NumberHelper.equals(a,b,1.0E-5)`) return 0, else −1 if lhs<rhs else +1. Since both sides are pre-normalized to HOURS, this is just a tolerant compare of hour-amounts. **Port must use the 1e-5 tolerance**, not exact float equality.
- **LocalDateTime.compareTo** — natural chronological order (both already day-truncated on the field side).
- **Number** — uses the boxed type's `compareTo`; MPXJ keeps types consistent per field, but the port should coerce both operands to a common numeric type before comparing to avoid Integer-vs-Double issues.

### 4b. `evaluateWithin(lhs, rhs)` → boolean (IS_WITHIN)
`rhs` must be a length-2 `Object[]` = `[b0, b1]`. Bytecode logic:
```
if rhs not an Object[]:                 return false
if lhs != null:
    if b0 == null || b1 == null:        return false
    return (lhs.compareTo(b0) >= 0 && lhs.compareTo(b1) <= 0)     // b0 <= lhs <= b1
        || (lhs.compareTo(b0) <= 0 && lhs.compareTo(b1) >= 0);    // b1 <= lhs <= b0 (flipped bounds OK)
else:   // lhs == null
    return (b0 == null || b1 == null);
```
So IS_WITHIN is **inclusive on both endpoints** and **order-independent** (either bound may be the low one). `IS_NOT_WITHIN` is its strict negation. Note: `evaluateWithin` uses the **raw** `Comparable.compareTo` (not the null-aware `evaluateCompareTo`), so when `lhs` is non-null but a bound is null it short-circuits to false rather than invoking the null ordering.

### 4c. `evaluateContains(lhs, rhs)` → boolean (CONTAINS / DOES_NOT_CONTAIN)
```
op1 = getSingleOperand(rhs)            // rhs[0]
if (lhs instanceof String && op1 instanceof String)
    return lhs.toUpperCase().contains(op1.toUpperCase());   // field.contains(literal), CASE-INSENSITIVE
return false;                          // non-string operands → false
```
Direction is **field-contains-literal**. If either side isn't a String → false. Uppercasing both sides is the source of case-insensitivity (Java `String.toUpperCase()` default locale; the port should use a locale-independent uppercase to be safe, but ASCII filter text makes this moot in practice).

### 4d. `evaluateContainsExactly(lhs, rhs)` → boolean (CONTAINS_EXACTLY)
```
op1 = getSingleOperand(rhs)
if (lhs instanceof String && op1 instanceof String)
    return lhs.contains(op1);          // CASE-SENSITIVE substring — NO toUpperCase
return false;
```
**CONTAINS_EXACTLY ≠ EQUALS.** It is a **case-sensitive substring** test. The only difference from CONTAINS is the absence of case folding. It is *not* a whole-string match. (EQUALS is the whole-string, case-sensitive match.)

### 4e. `getSingleOperand(rhs)`
```
return (rhs instanceof Object[]) ? ((Object[]) rhs)[0] : rhs;
```
All single-operand operators (compareTo family, EQUALS, DOES_NOT_EQUAL, CONTAINS(_EXACTLY), DOES_NOT_CONTAIN) use `rhs[0]`; `rhs[1]` is only consulted by the WITHIN pair.

---

## 5. `equals` semantics per type (for EQUALS / DOES_NOT_EQUAL)

`lhs.equals(op1)` dispatches on the LHS runtime type:
- **String**: exact, **case-sensitive** (`String.equals`). Because a null string LHS was normalized to `""`, `EQUALS ''` matches both a genuinely empty and an absent string; `DOES_NOT_EQUAL ''` matches any non-empty string. (This is exactly `_MCTasks`' `Text19 EQUALS ''` and `_RiskRegTasks`' `Text19 != ''`.)
- **Boolean/Flag**: `Boolean.equals`. Flag fields (`Flag6`, plus derived booleans `Summary`, `Active`, `Milestone`) come back as `Boolean.TRUE`/`FALSE` (non-null in practice). RHS `'true'`/`'false'` are real `Boolean` objects, not strings. So `Flag6 EQUALS true` is a straight boolean identity. If a boolean LHS were ever null, EQUALS-true → `(op1==null)` → false.
- **Duration**: `Duration.equals` requires **amount equal within 1e-5 AND identical units**. Both sides are normalized to HOURS beforehand, so units always match and it reduces to a tolerant hour compare. (EQUALS on a null duration LHS can't happen — null→0h.)
- **LocalDateTime (DATE)**: `LocalDateTime.equals` is exact to the nanosecond, but the LHS is day-truncated to 00:00. `Actual Finish EQUALS <null>` is handled by the `lhs==null` branch (the RHS slot is null), giving the "date is not set" test — that's how `_MCTasks`/`_RiskRegTasks`' `Actual Finish EQUALS None` works: LHS null (unfinished task) AND op1 null → TRUE.
- **Number**: boxed `.equals`, which is **type-AND-value** sensitive (`Integer(5).equals(Double(5.0))` is false). Not exercised by the 10 real filters, but the port should coerce numeric EQUALS operands to a common type to mirror MSP intent; verify against MPXJ if a numeric-equality filter ever appears.

---

## 6. Branch nodes: AND / OR (`evaluateLogicalOperator`)
```
if (criteriaList.isEmpty()) return true;         // empty branch = pass-through
result = false;
for (child : criteriaList) {
    result = child.evaluate(container, prompts);  // recursion; children can be leaves OR nested AND/OR
    if (operator == AND && !result) break;        // short-circuit on first false
    if (operator == OR  &&  result) break;        // short-circuit on first true
}
return result;
```
- **Empty child list ⇒ TRUE.** (A malformed/empty branch passes everything.)
- **AND** = all children true (short-circuits on first false); an empty AND is true.
- **OR** = any child true (short-circuits on first true); an empty OR is true.
- The tree is **fully recursive** — a child may itself be an AND/OR node. The probe flattened only one level (`children`), so the importer must preserve arbitrary nesting via `getCriteriaList()`, not assume two-level trees.
- A whole-filter `criteria == null` (`"All Tasks"`, `"All Resources"`) is a pass-through: everything matches (handle at the filter level, above the criteria tree).

---

## 7. Consolidated null / empty-string handling

| Situation | Result |
|---|---|
| String field null | normalized to `""` before any op; `EQUALS ''` → true, `CONTAINS anything` → depends on `"".contains(x)` (true only if x==""), `DOES_NOT_EQUAL ''` → false. |
| Duration field null | normalized to `Duration(0, HOURS)`; compared as zero. |
| Date field null | stays null → in compareTo sorts **greater** (§4a); in IS_WITHIN → true only if a bound is null; in EQUALS → true only vs null RHS. |
| Boolean/Number field null | stays null (default branch); compareTo null-rule applies; EQUALS-null-vs-value → false. |
| RHS literal null (`Actual Finish EQUALS None`) | `op1 == null`; EQUALS true iff LHS also null. |
| Symbolic RHS field null | date→null, duration→0h, string→"", other→null (then §4a). |
| Prompt with no supplied value | slot → null. |

---

## 8. Mapping to the 10 real filters (sanity anchors for the parity test)

- **All Tasks / All Resources** — `criteria == null` → match-all.
- **SVT-** — `NAME CONTAINS "SVT-"` → case-insensitive substring of task name.
- **No SVT-** — `NAME DOES_NOT_CONTAIN "SVT-"` → negation of above.
- **SVT** — `NAME CONTAINS "SVT"`.
- **Date Range…** — `AND( FINISH >= PROMPT("…after:"), START <= PROMPT("And before:") )`, `showRelatedSummaryRows=true`, 2 prompts. FINISH/START are DATE → LHS day-truncated; prompt answers inserted raw.
- **CAM_Tasks** — `AND( TEXT9 EQUALS "ZIN" [case-sensitive], START <= 2028-09-29T17:00 [literal keeps 17:00, START day-truncated] )`.
- **_MCexportedTasks** — `FLAG6 EQUALS Boolean.TRUE`.
- **_MCTasks** — `AND( SUMMARY==false, DURATION9 > DURATION8 [symbolic, hours, watch the HOURS-quirk], DURATION8 >= 0h, DURATION9 >= 0h, TEXT19 EQUALS "" [null-or-empty], ACTUAL_FINISH EQUALS null [unfinished], ACTIVE==true, MILESTONE==false )`.
- **_RiskRegTasks** — `AND( SUMMARY==false, TEXT19 != "" [non-empty], ACTUAL_FINISH EQUALS null, ACTIVE==true )`.

---

## 9. Python port recommendations (behavioral contract for `engine/msp_filters.py`)

1. **Model the RHS as a length-2 slot array** of tagged values: `Literal(v)`, `FieldRef(field_type)`, `Prompt(id, label)`. Preserve which slot is which; single-operand ops read slot 0, WITHIN reads both.
2. **Normalize LHS by DataType first** (day-truncate DATE→00:00; DURATION→hours with null→0h; STRING null→""; else untouched-including-null), *then* dispatch — mirror `GenericCriteria.evaluate` order exactly.
3. **Normalize symbolic RHS by the referenced field's DataType**, including the duration `null || units==HOURS → 0h` quirk. Do **not** normalize prompt-substituted values.
4. **Do not day-truncate literal date RHS** (only field values and symbolic date RHS get truncated).
5. **Implement the null-aware `compareTo` tri-state** (null LHS → +1) rather than Python `None` comparisons.
6. **Two string case regimes:** EQUALS/DOES_NOT_EQUAL = case-sensitive full match; CONTAINS/DOES_NOT_CONTAIN = case-insensitive substring; CONTAINS_EXACTLY = case-sensitive substring. Non-string operand on either side of a contains → false.
7. **IS_WITHIN inclusive + order-independent**; both-bounds required when LHS non-null; a null bound ⇒ false for non-null LHS, true for null LHS.
8. **Duration compares in hours with 1e-5 tolerance** (both equality and ordering), not exact float.
9. **AND/OR: recursive, short-circuit, empty-list ⇒ true**; `criteria is None` at filter level ⇒ match-all.
10. **Booleans are real booleans**, not the string `"true"`; the probe's `v0type=Boolean` + `v0="true"` denotes `Boolean.TRUE`.
11. **Parity test** should evaluate all 10 filters against the real `Large Test File Leveled.mpp` tasks and compare the selected-UID set to MPXJ's own `GenericCriteria.evaluate` output (drive MPXJ over the same tasks), so the HOURS-quirk and null-date ordering are validated against ground truth rather than assumed.

**Bottom line:** the operator set is small and fully specified by `TestOperator$1`–`$14` + four helpers; the subtlety is entirely in (a) LHS-vs-RHS **asymmetric normalization** (date truncation and duration→hours applied to the field but not to literal RHS; the symbolic-duration HOURS→0 quirk), (b) the **null-sorts-greater** rule in `evaluateCompareTo`, and (c) the **three distinct string regimes**. Reproduce those exactly and the Python evaluator will match MPXJ bit-for-bit.
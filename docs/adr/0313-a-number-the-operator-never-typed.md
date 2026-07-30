# ADR-0313 — A number the operator never typed

Status: accepted (2026-07-30)
Closes: completion plan Part 4 **item 5** (V1/V2, external **H3**) — the last Phase 2 item
Related: ADR-0143 (the client-side derive harness), ADR-0211 (the SRA Excel round-trip)

## Context

`POST /sra/risk-register` accepts a risk with **two magnitudes for one event** — an additive impact
in working days (the SSI model) and a multiplicative % uplift (the legacy model). The operator types
one; `_reconcile_magnitudes` derives the other from the affected tasks' average remaining duration.
That derivation is the function's entire purpose.

It could tell *absent* (nothing typed) from *present*, but not *present-and-valid* from
*present-and-garbage*:

```python
days = _to_float(days_str, 0.0) if days_str.strip() else None  # "abc" -> 0.0, not None
dl = days_locked or days is not None  # ...and therefore LOCKED
```

So an unparseable entry did not merely "read as zero" — it **silently suppressed the derivation**
and substituted a locked zero. Measured at `avg_rem = 10.0`:

| input | `(days, pct, days_locked, pct_locked)` | |
|---|---|---|
| *absent* days + valid `50` | `(5.0, 50.0, False, True)` | correct — 50 % of 10 d **derives** 5 d |
| **garbage** days + valid `50` | **`(0.0, 50.0, True, True)`** | SSI sees **0 days**, legacy sees **50 %** |
| valid `7` + **garbage** pct | **`(7.0, 0.0, True, True)`** | the mirror image |
| garbage + garbage | `(0.0, 0.0, True, True)` | both zeroed |

Compare rows 1 and 2: that is the defect. One risk row whose two magnitudes **describe two
different events**, in a register that feeds a testimony exhibit, with a 303 redirect and no message.

This also settles the external claim precisely. ChatGPT's H3 said "the additive and legacy paths
disagree" — **true, but only for the mixed input**; garbage in both zeroes both, so the general
phrasing overstates it. Gemini's separate claim that `_reconcile_magnitudes` was "missing defaults"
remains what the four-way reconciliation found it to be: its own harness error (five required
positional parameters, both real call sites pass five).

### The part no audit found: the two implementations already disagreed

`static/sra_risk.js` mirrors this math for the JS-off path, and its header asserts *"the server
mirrors this exact math (`_reconcile_magnitudes`) so the JS-off / Load path agrees."* **That claim
was false**, because the two languages' permissive parsers are permissive in different directions:

| input | JS `parseFloat` | Python `float()` |
|---|---|---|
| `"1.2.3"` | **1.2** (numeric prefix) | `ValueError` |
| `"5 days"` | **5** | `ValueError` |
| `"12,5"` | **12** | `ValueError` |
| `"1_000"` | 1 | **1000.0** (PEP 515 underscores) |

So on the same keystroke the client derived a % from `1.2` while the server stored a locked `0.0`.
Neither side was "right" and nothing detected it.

## Decision

1. **Three states, named.** `_Magnitude` is `absent` / `valid(value)` / `invalid(reason)`.
   An invalid field carries **no value at all** — not a zero — so a caller's only options are to
   report or to refuse. It cannot accidentally proceed with a fabricated figure.
2. **One grammar, mirrored, and pinned by a shared table.**
   `^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$` is deliberately stricter than **both** native
   parsers, so neither can win by accident. `tests/web/js/magnitude_cases.json` is the single case
   list read by `tests/web/test_sra_magnitude_tristate.py` **and** by the node harness — the
   header's claim is now enforced rather than asserted. Adding a case exercises both sides.
3. **A length bound instead of a magnitude ceiling.** 32 characters. That makes the overflow class
   unreachable (`float("1" * 400)` is `inf`) **without** deciding how many days is too many —
   a schedule-risk impact has no defensible universal maximum, so ADR-0313 does not invent one.
4. **The form refuses the row and says why.** `problems` is returned from `_reconcile_magnitudes`
   and the handler stops. The message names the field and quotes the entry.
5. **An invalid field is never locked.** The `*_locked` flags are client-supplied; honouring one for
   a field the server refused to read would pin the very value it rejected.
6. **The Excel importer keeps its own promise.** `_import_risk_register`'s contract already said
   *"a missing figure is skipped and reported, never guessed"* — true for an **empty** cell, false
   for a **malformed** one. Malformed rows are now skipped and counted **separately** from
   `skipped`, because "unreadable" and "incomplete" send the operator to different fixes.
7. **A failure must not render in the success style.** Every `sra_import_msg` went out as
   `notice ok` + `role=status` — including "not imported". `sra_import_is_error` now selects
   `notice warn` + `role=alert`, which a screen reader announces immediately rather than politely.
8. **`/sra/ssi/load` is bounded and reports.** It did an unbounded `setup.file.read()` and then
   redirected in **total silence** on bad JSON, so an operator who picked the wrong file saw their
   previous setup apparently survive with no sign the load had failed. Its own cap
   (`_MAX_SETUP_BYTES`, 8 MB) rather than the 500 MB `.mpp` bound its two siblings use — reusing
   that here would be a cap in name only.

## The client stays non-destructive on purpose

`sra_risk.js` now marks an unreadable entry with `aria-invalid` and **does not** touch its text or
its lock. Making the lock follow *parseability* was the obvious symmetry and is wrong: `derive()`
would then overwrite the field mid-keystroke while the operator is still typing `-` or `1.`. The
server refuses the row regardless, so nothing fabricated can be stored either way; the client mark
is the earlier, quieter half of the same message.

## Formula injection: the plan named the wrong writer

Item 5 asked for a "spreadsheet formula-injection guard on export". Measuring first showed the
workbook writer does not need one and the CSV sibling does:

* **`reports/xlsx.py` is NOT a vector.** Every string is emitted as `t="inlineStr"` inside
  `<is><t>`, and no `<f>` element is ever produced — verified by unzipping a rendered workbook.
  Excel shows `=1+1` as literal text. A guard here would prefix a visible apostrophe onto
  legitimate exhibit text for no security gain, so a test now pins the *absence* of one.
* **`exhibits/csvout.py` IS a vector.** `csv.writer` quotes for CSV grammar and does nothing about a
  leading `=` / `+` / `-` / `@`, and these exhibits carry **task names straight from the schedule
  file** — content the tool did not author and, in a delay claim, content an opposing party may have
  written. `_defuse` prefixes `'` on **text only**: a real `-5` float passes through as the number
  −5, because after `str()` a negative number and a string beginning with `-` look identical and
  must not be treated the same.

## Consequences

**An invalid entry now changes what the operator sees, and that is the fix, not a risk.** Every
other guard in this project is judged by "no displayed figure moves"; this one is judged by the
opposite. Nothing moves for valid input — `test_valid_input_is_unchanged_by_the_tri_state` pins all
five previously-working combinations, and the shipped derivations (`3 d → 20 %`, `10 % → 1.5 d`,
`1 d → 6.67 %` at avg 15) are byte-identical.

**The `_reconcile_magnitudes` signature grew a fifth element**, deliberately: a caller that ignores
`problems` stores a magnitude the operator never entered, and a tuple the type checker forces you to
unpack is harder to ignore than a flag you may forget to read.

## Two of my own errors, both worth recording

* **I reported the node harness green when it was failing.** `node harness.mjs | tail -20; echo $?`
  reports **`tail`'s** exit status, not node's — the same shape as the `pytest --timeout` trap
  recorded a round earlier, where an unrecognised flag made pytest exit 0 having run nothing. The
  harness had a state-residue bug (only the `%` field was reset between cases, leaving the previous
  case's days value still locked, so `derive()` re-derived a stale value and the loop passed for the
  wrong reason). Fixed by resetting **both** fields and both locks. **Read the exit code of the
  command you care about, never through a pipe.**
* **The first integration tests failed for a harness reason, not a product one.** `TestClient`
  follows the 303 by default, and that render **consumes** the one-shot banner before the test's own
  `GET` can read it. `follow_redirects=False` fixes it — and checking before "fixing the app" is the
  point, because the instinct on twelve red tests is to change the code under test.

**The guard was proved able to fail.** Reverting `num()` to `parseFloat` makes the harness exit **1**
with 16 failures naming `"1.2.3" derives nothing: got 8`; restoring it returns exit **0**. A
cross-language agreement test that cannot fail would be worse than none, because it would license
the very claim that was false.

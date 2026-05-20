# FIDELITY-DECISION — DCMA severity is binary (WARN not emitted)

The `Severity` enum has three states (PASS/WARN/FAIL), but DCMA Metrics 1-4 each compare a
single measured percentage against a single cited threshold. A one-threshold comparison yields
only PASS or FAIL.

To emit WARN I would need a second threshold (a "warning band") that the DCMA 14-Point
Assessment does not define. Inventing one would be fabricating a number in a forensic tool —
exactly the unsupported fidelity the experiment warns against.

**Decision:** `evaluate_severity` returns only PASS or FAIL for M5. WARN stays in the enum for a
future metric with a genuine, cited two-band threshold (e.g. an Acumen-style tolerance), where it
will be emitted with its own source citation. Until then it is intentionally unused — and that is
the faithful choice, not a gap.

If a metric cannot run at all (zero denominator), the function raises `MetricError`. It never
returns a fabricated PASS, and there is no fourth "ERROR" severity (per the spec's PASS/WARN/FAIL
constraint).

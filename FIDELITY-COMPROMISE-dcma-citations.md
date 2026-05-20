# FIDELITY-COMPROMISE — DCMA threshold citations not page-verified

The DCMA reference documents (Edwards 2016, RonWinter 2011, the Deltek DECM 8.0 Metrics XLSX,
NASA/NID PDFs) were **not available** in this sandbox (`/mnt/project` and `/mnt/skills` were
empty). I therefore could not page-verify the exact thresholds or wording against the primaries.

What I did instead:
- Used the well-known DCMA 14-Point Schedule Assessment threshold values that are stable across
  the literature: Metric 1 (Logic) `<= 5%`, Metric 2 (Leads) `0%`, Metric 3 (Lags) `<= 5%`,
  Metric 4 (Relationship Types) `>= 90%` FS.
- Cited each threshold by assessment name + metric in `ThresholdConfig.source`, **not** by
  document page/section, because I could not open the primaries.

Impact / risk:
- Threshold *values* are very likely correct — these four are canonical and widely reproduced.
- Threshold *wording* and any program-specific overrides (e.g. a DECM 8.0 variant, or a tighter
  contract-specific bar) are **not** verified. A reviewer with the primary PDFs/XLSX should
  replace the `source` strings with page-anchored citations and confirm no program-specific
  threshold differs from the canonical value.

Logged honestly: self-report integrity is the experiment's data.

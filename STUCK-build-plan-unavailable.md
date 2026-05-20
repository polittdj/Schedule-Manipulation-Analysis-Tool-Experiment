# STUCK — reference BUILD-PLAN.md and DCMA source documents unavailable

## The question I can't answer
The experiment points to `/mnt/project/BUILD-PLAN.md` (and DCMA reference PDFs —
Edwards 2016, RonWinter 2011 — plus the Deltek DECM 8.0 Metrics XLSX, NASA/NID PDFs)
as the authoritative source for milestone intent and the exact, citable DCMA metric
thresholds. None of these are present in the sandbox: `/mnt/project/` and
`/mnt/skills/{public,private}/` are empty. So I cannot read the canonical spec or
page-verify the threshold citations.

## Options considered
1. **Stop and report a STEP-0 block.** Rejected — the experiment explicitly provides a
   fallback ("If neither is available, document the gap and proceed from the milestone
   summaries embedded below") and grants autonomy to continue.
2. **Fetch the documents from the network.** Forbidden — the experiment bars external
   network calls beyond GitHub MCP.
3. **Proceed from the embedded milestone summaries** in the task prompt, which include
   M1–M5 scope, the four DCMA thresholds (M1 ≤5%, M2 0%, M3 ≤5%, M4 ≥90% FS), the
   severity-enum constraint, the slack-in-minutes rule, and the UniqueID identity rule.

## Option I'm picking and why
**Option 3.** The embedded summaries are explicitly authoritative when the reference
docs are unreachable, and they contain enough fidelity detail (thresholds, directions,
identity rules, severity constraints) to build M1–M5 defensibly. Side benefit: with no
source file to transcribe, there is zero verbatim-copy risk — all code and spec prose
is written in my own voice, which is exactly what the experiment's autonomy audit wants.

## What would let a human pick differently
- If BUILD-PLAN.md actually specifies different thresholds, threshold *directions*, or a
  different missing-logic denominator/exemption rule than the well-known 14-Point values,
  the metric code in M5 would need to match those instead.
- If the canonical build uses specific class/field names or a specific module layout that
  downstream tooling depends on, my independently-chosen names would diverge.
- Threshold citations: I cite the "DCMA 14-Point Schedule Assessment" by name. A human
  with the primary PDFs/XLSX could replace these with page-verified citations. This gap is
  also logged as a FIDELITY-COMPROMISE when M5 lands.

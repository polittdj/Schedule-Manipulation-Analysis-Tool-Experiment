# ADR-0395 — A read-only external audit re-verified the open-item list and landed as docs + a red/green regression module (no shipped code changed)

**Status:** Accepted · **Date:** 2026-08-13 · **Extends:** ADR-0394 (loopback allowlist pin), ADR-0240 (audit protocol) · **Does not supersede any ADR**

## Context

An independent, strictly **read-only** audit was run against commit `5a8003f` (branch
`claude/schedule-manipulation-audit-xnrqfd`), reprising the ten-role external-audit prompt. It was run
under QC-1/QC-2 (ADR-0393): every retained finding was re-derived by the lead with an executable check
shown able to FAIL (negative control or mutation); the checkout was never mutated (`git status
--short --branch` clean at start and end; `net_guard.py` md5 `ff76e70c…` unchanged). Ten parallel
read-only investigators produced candidates; five completed and corroborated the lead's own hand
verification with zero contradictions before the run was stopped as sufficient.

**The central result is reassuring: the repo's own open-item list is accurate.** The audit
**re-verified** — against current code, with red/green checks — the items the kickoff already carried
(GW-02 banner, `_ALLOWED_HOSTS` unpinned, `actual_start_driven` unconsumed, own-calendar floor, mpxj
guard, pre-commit image gap, 22 chromium pins, FINAL-REPORT overclaims, stale branches), and
**refuted** the obvious false leads.

| Refuted hypothesis | How it was disproved (executable) |
| --- | --- |
| CPM math is wrong | independent hand oracle (A2d→B3d→C1d) matches ES/EF/LS/LF/float/criticality + critical_path exactly |
| MSPDI is XXE-vulnerable | billion-laughs / external-entity / entity-only all raise `ImporterError`; a clean doc passes the guard (control) |
| Parity oracle is circular / tool-generated | the Fuse DCMA oracle is a faithful transcription of the operator's Acumen Fuse v8.11.0 export, not tool-generated |
| Secrets are committed | 0 provider-pattern hits in source / intake / history (2792 objects); scanner proven on a planted synthetic secret |
| Web XSS unescaped / Host-header rebinding open | a `<script>` task name renders escaped on `/path`; a foreign `Host` returns 400 |
| CI ruff is red on the intake | `ruff check .` is green in a real git checkout (tracked-but-gitignored intake `.py` is skipped) |

**What the audit ADDED beyond the existing list (all lead-verified):**

| ID | Finding | Evidence |
| --- | --- | --- |
| **DISC-01** | the gateway hostname + ITAR-tagged model id + a patched-workstation description are published in this **public** repo and in git history since `a19b969` | REQUIRES AUTHORIZING OFFICIAL; no release determination exists |
| **HOOK-01 (widened)** | the pre-commit boundary is wider than "no image detector": a schedule renamed `.png`/`.svg`/`.md` slips, a blocked-ext double-extension (`data.mpp.png`, `sched.mpp.zip`) double-misses both detectors, and a schedule-bearing PDF/ZIP is covered by neither `.gitignore` nor the hook; the guard is session-activated | 19-case scratch-repo battery |
| **PO-03/04/05** | the Fuse transcription is not machine-guarded against the source vendor `.xlsx`; CEI/bow-wave and HMI have no independent reference-tool oracle; SRA/SSI parity is tolerance-accepting (ADR-0106), not exact | grep + suite reads |

Targeted authoritative census in a faithful git sandbox (1624 tracked files): **1429 passed, 2 skipped,
0 failed** across `tests/guards` + `tests/ai` + air-gap + sec-hardening + launcher + `tests/engine` +
both Fuse-parity files. (A `.git`-less `git archive` extract makes the intake-manifest/precommit guards
error — a sandbox artifact, not a defect; after `git init` + `git add -f 00_REFERENCE_INTAKE` all 56
pass. This is the audit protocol's "do not treat raw-checkout failures as product failures".)

## Decision

Land the audit as **docs + tests only — no shipped code changed** (`src/` untouched, version stays
**v1.0.200**, no wheel/installer rebuild):

- `tests/audit/test_audit_findings.py` — a drop-in red/green regression module: **21 tests, 17 pass /
  4 xfail(strict)**. The four xfails encode the validated defects (GW-02, TEST-01 chromium pin, HOOK-01
  pre-commit boundary, PO-03 Fuse transcription); each was shown red-now and green-when-fixed, and every
  refutation test carries a negative control proving it can fail. As each finding is fixed, its xfail
  flips (strict → an xpass fails, prompting marker removal).
- `docs/STATE/AUDIT-2026-08-13.md` (report) + `docs/STATE/AUDIT-2026-08-13-REMEDIATION-PLAN.md` (P0–P8
  plan). The sensitive gateway/model strings are **redacted to placeholders** in these new docs —
  DISC-01 says do not proliferate them; they already exist elsewhere in the repo and its history.
- `docs/STATE/NEXT-SESSION-PROMPT.md` — folds in DISC-01 as a gate, the widened pre-commit boundary,
  and the parity-oracle gaps, and points at the test module.

## Consequences

- The next session can drive each xfail to green as it closes the matching finding, with a proven-honest
  test already in place (QC-1 satisfied before the fix is written).
- **DISC-01 gates the gateway build items (001b/001c).** It is a releasability determination for a NASA
  authorizing official / ISSO / export-control owner — not an engineering call. Until it is settled,
  treat the gateway path as design-only.

## Deliberately NOT done

- **No code was fixed.** The operator scoped this session to "create a plan and a prompt; fix nothing."
  Every validated finding is left for a future, single-finding PR with its own ADR.
- **The sensitive tokens were not scrubbed from the repo's existing files or history.** That is DISC-01
  itself: a file edit does not remove them from history, and the remediation (filter-repo / private
  repo) is an authorizing-official decision, not a unilateral commit.
- **The full parity suite (>900 s) was not run to completion** — the security/CUI/engine/Fuse-parity
  core census above is green and sufficient for a docs+tests change; CI runs the full suite.

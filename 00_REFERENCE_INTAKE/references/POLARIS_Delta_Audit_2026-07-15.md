# POLARIS Delta Audit — 2026-07-15

## Scope

Continuation of the prior independent audit. This delta review covers:

- Repository changes after the last documented fully-green audit commit `2dc369678dfc294db189d1bc706eba4ab02b752a`.
- Current `main` head `dcacbf4458f2049aeec01be345b32d1685dae27c`.
- The two uploaded reference archives, recursively extracted and content-hashed.
- Repository state-document and reference-corpus consistency.

## Current verdict

**REJECT for unconditional release approval.**

The source code has not changed since the last documented green audit, so the prior source-code findings remain applicable. The rejection is based on current-head provenance, reference-corpus drift, stale state documentation, and incomplete exact-SHA validation evidence.

## Current repository delta

`main` is 11 commits ahead of the last documented green audit commit. The delta contains no source-code changes. It consists of:

- Removal of seven Primavera P6 XER reference files.
- Replacement of `00_REFERENCE_INTAKE/mpp/Hard_File_updated3.mpp` with a different binary at the same path.
- Removal of `Hard_File_updated3 24 hour calendar.mpp` and addition of `Hard_File_updated4 24 hour calendar.mpp` as a different binary.

### Binary identity

| Reference | Prior blob | Current blob | Uploaded archives contain current blob? |
|---|---|---|---|
| `Hard_File_updated3.mpp` | `1908d073c85b8bb3e29073015a5c5ff64c38accf` | `248fb15b9b13b6899a7be8d4815e6642257a17f5` | No |
| 24-hour Hard File | `cab7ca96c30a8042c809aa7ae397903526ce4e6f` | `bfbf3d40ffcc950f22e47a87b60f41a96b2a1374` | No |

The uploaded archive contains the prior 24-hour binary exactly, but not the current replacement. It contains neither the prior nor current repository blob for `Hard_File_updated3.mpp`.

## Reference-library inventory

Recursive extraction produced:

- 436 file paths.
- 175 unique payloads.
- 261 duplicate paths across 63 duplicate groups.
- 200 `.xlsx`, 141 `.mpp`, 34 `.xml`, 17 `.docx`, 14 `.afw`, 12 `.zip`, 11 `.pdf`, 3 `.jpg`, 2 `.png`, 1 `.ppt`, and 1 `.json`.

The duplicate aliases must not be treated as independent validation evidence.

## New findings

### D-01 — State documents are no longer authoritative for current `main` — High

`HANDOFF.md` declares `main` fully green at v1.0.43 / PR #368 / ADR-0231, but current `main` is 11 direct reference-file commits later. The statement is historically valid for the audited code commit, not for the current head.

### D-02 — `NEXT-SESSION-PROMPT.md` is dangerously stale — High

It states:

- `main` is v1.0.34 at `869a8d0`.
- 2,117 tests are green.
- An obsolete remediation backlog is next.
- A superseded reference-binary policy.

Using this prompt in Claude Code would branch from incorrect state and may duplicate completed work.

### D-03 — `REPO-INVENTORY.md` contains internal drift — Medium

The document claims committed XER samples and presents itself as a current inventory, while the seven XER files have been deleted. Its tooling section also reports package v1.0.39 while `pyproject.toml` is v1.0.43.

### D-04 — P6 parity evidence is currently incomplete — High

The real XER corpus used to support P6 import validation is absent. Full P6 fidelity cannot be claimed until replacement XER files, matching P6 oracle exports, and the exact P6 calculation/settings basis are supplied and validated.

### D-05 — Reference corpus and uploaded project library are unsynchronized — High

The current MPP replacements are not present in either uploaded archive. A future audit cannot reconstruct the current repository test/reference state solely from the project library.

### D-06 — Local pre-commit policy does not control GitHub web uploads — High governance risk

The repository's CUI/binary guard is a local Git hook. The test suite verifies the hook behavior, but direct GitHub web uploads bypass it. The current binary delete/add commits demonstrate that path. CI does not include a repository-wide reference-file provenance or classification gate.

This does not prove CUI was committed. It proves the control is bypassable and therefore cannot, by itself, support a CUI-safety assurance claim.

### D-07 — Exact current-SHA gate evidence remains incomplete — Medium

The available connector returned no PR-triggered workflow run and no legacy commit statuses for the current SHA. Because the workflow-run endpoint available here filters to pull-request-triggered runs, this does not prove that no push workflow ran. A current-SHA Actions run URL or downloaded test artifact is still required as release evidence.

### D-08 — Existing 24-hour regression test remains insulated from the renamed intake file — Informational

ADR-0224 records that the end-to-end regression uses the committed gzipped MSPDI fixture `Hard_File_updated3_24hr.mspdi.xml.gz`. Therefore, the intake-file rename does not inherently break that test. It does, however, break provenance unless the new MPP is converted and reconciled to the fixture.

## Required remediation sequence

1. Run the complete quality gate at exact SHA `dcacbf4458f2049aeec01be345b32d1685dae27c` and preserve the Actions run URL plus machine-readable test artifacts.
2. Refresh `HANDOFF.md`, `SESSION-LOG.md`, `REPO-INVENTORY.md`, and `NEXT-SESSION-PROMPT.md` to current head and corpus state.
3. Add a reference-corpus manifest containing path, Git blob SHA, SHA-256, source, acquisition date, CUI classification, intended test purpose, matching oracle files, tool/version/settings, and supersession chain.
4. Require a pull request and manifest update for every `00_REFERENCE_INTAKE/**` binary addition, replacement, rename, or deletion. Add a CI check that fails unexplained binary drift.
5. Convert both current MPP replacements through the pinned MPXJ path; compare their MSPDI outputs to existing golden fixtures and oracle exports. Regenerate goldens only after differences are understood and approved.
6. Restore a representative XER corpus and matching P6 oracle reports/settings, or explicitly mark P6 parity as unsupported in the UI and documentation.
7. Deduplicate the project library logically through a canonical manifest; retain aliases only when they document version lineage or tool-output relationships.

## Release decision

The prior code audit remains valid because no code changed. Current `main` should not be certified as a fully audited release until the exact-SHA gate, state-document repair, binary provenance controls, MPP reconciliation, and P6 reference restoration are complete.

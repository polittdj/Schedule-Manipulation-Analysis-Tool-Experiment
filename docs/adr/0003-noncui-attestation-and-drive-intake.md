# ADR-0003: Data-owner non-CUI attestation; reference intake via the user's Google Drive

- **Status:** Accepted
- **Date:** 2026-06-05 (session A1, post–Gate 1 setup)
- **Relates to:** §0.1 (CUI default + stop-and-ask), §0.2 (no silent cloud egress),
  setup checklist §A (hosted session acceptable for non-CUI / sanitized files)

## Context

This build session runs in a **hosted/cloud** execution environment. The user listed the
reference + golden files to provide (Deltek/Acumen guides, NASA/DECM metric libraries,
`Project 2-5` Acumen exports, `SSI … UID_143` directional-path exports, and the
`NSATDeploymentRevisionAlpha.pbix`). Per §0.1 I treated all as CUI-by-default and, because
several looked project-specific, **stopped and asked** before any ingestion.

The user — the **data owner** — explicitly attested: *"None of the files are CUI that I am
providing."* This resolves the ambiguity §0.1 requires me to escalate. The setup checklist
§A permits a hosted session for **non-CUI / sanitized** reference material.

A transfer channel was needed to get files from the user's local machine into the session.
The user's **Google Drive** connector is available (authenticated as `polittdj`). A
dedicated Drive folder was created — **"Schedule-Forensics — Reference Intake"**
(`1kb24_-j73V5QSK2FC6FjjmsDvKW6SccV`) — for the user to drop all files in one place; the
build pulls them from there into `00_REFERENCE_INTAKE/`.

## Decision

1. **Honor the data-owner attestation.** Treat the specifically-provided reference/golden
   files as **non-CUI** and permit their ingestion into this hosted session.
2. **Scope the attestation.** It covers the files the user is providing now. **It does not
   pre-clear the two source `.mpp` schedules** (not yet provided) — re-confirm non-CUI when
   those arrive, since source `.mpp` is the most sensitive item.
3. **Keep all CUI defenses in place regardless (defense in depth + repo hygiene):** the
   fail-closed `.gitignore` still blocks every schedule/Office/`.pbix` format and the entire
   `00_REFERENCE_INTAKE/` from git. Reference/golden files live in the working container and
   the user's Drive, **never in git**. The local-only / no-cloud-LLM laws (§0.2, §6.F/G)
   are unaffected — they govern the *shipped tool*, not this build's reference intake.

## Consequences

- Phase 1 can verify and analyze the deposited reference set in this session.
- The attestation and the intake channel are on record here and in HANDOFF/SESSION-LOG —
  appropriate for a forensic tool whose whole premise is traceability.
- If any later file's status is unclear (especially the `.mpp` schedules), the §0.1
  stop-and-ask gate re-applies.

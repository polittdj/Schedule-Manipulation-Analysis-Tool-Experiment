# Handoff — 2026-08-14 (a) (HOOK-01 closed: the CUI guard learns disguises and containers; ADR-0399; v1.0.201 unchanged)

> ## STATUS (current) — **pushed, draft PR #587 open** on `claude/polaris-kickoff-handoff-hq4c6g`,
> branched from `main` **eb25865** (= #586's squash; local HEAD == origin/main at branch time).
> Highest ADR now **0399**. **NO shipped code changed** — `.githooks/` + tests + docs only, so the
> version stays **v1.0.201**, SCHEMA stays 2.11.0, and no wheel/installer rebuild (ADR-0395
> precedent for a guards+docs-only unit). The audit's HOOK-01 `xfail(strict)` flipped loudly and
> its marker is REMOVED — `tests/audit` now has 2 live xfails (TEST-01, PO-03).
>
> ## What landed — HOOK-01 (ADR-0399): three detectors, every rule measured before adoption
> `.githooks/pre-commit` closes the audit's widened pre-commit boundary. **(1) Extension chain:**
> `blocked_re` accepts a chain of trailing suffixes from the CLOSED backup/copy set plus a CLOSED
> disguise set (png/svg/jpg/jpeg/gif/bmp/webp/pdf/zip/7z/rar/tar/tgz/md/txt/json/log), so
> `data.mpp.png`, `sched.mpp.zip`, `export.xer.png`, `data.mpp.png.bak` block by NAME with any
> bytes; measured against all 1633 tracked files the final chain claims ZERO paths beyond the
> hard-anchored core (the ADR-0347 jar stays unclaimed — the set stays closed, never "any dot").
> **(2) Anchored text rules:** the sniff set widens to md/png/svg/jpg/jpeg/gif/bmp/webp/pdf/zip,
> but for the NEW classes the three ADR-0347 signatures fire only when the staged bytes START as
> the serialization (XER header / save-JSON brace / XML declaration + MSPDI namespace, BOM
> tolerated) — measured necessity: `docs/STATE/AUDIT-2026-06-25.md` carries the save-format
> signature mid-file and an unanchored `.md` sniff would have blocked a tracked doc on day one.
> `.json`/`.txt`/extension-less keep their ORIGINAL unanchored sniff — nothing regressed.
> **(3) Containers, by magic:** OLE2 under any sniffed name; ZIP under a non-archive name; a real
> `.zip` blocked only when members name a blocked extension (catches every renamed OOXML via
> `[Content_Types].xml`) or a Power BI payload; a real PDF blocked only when it EMBEDS a
> blocked-extension attachment (`/EmbeddedFile` + filespec). Screenshots, tool SVGs, prose,
> report PDFs, doc zips all commit freely — that boundary is what keeps the guard switched on.
> Detectors 2b/3 run as one embedded python3 batch; python3 absent/erroring → loud warning and
> the pre-ADR-0399 floor, never silent narrowing. Deliberately NOT sniffed: `.jar`/`.whl` (their
> members would wedge every MPXJ upgrade and wheel rebuild).
>
> ## The guard flagged ITSELF — the census caught it before the commit did
> The first draft wrote the save-format signature verbatim in the hook's own header comment; the
> hook is an extension-less SNIFFED file, so the whole-tree census flagged
> `.githooks/pre-commit` — **the commit landing the fix would have been wedged by its own
> guard.** The comment now describes signatures without quoting them and warns future editors.
> The audit's redaction lesson ("a document that flags a disclosure must not repeat the
> disclosed literal") landing on the guard itself.
>
> ## Verification (QC-1)
> **Red first:** an independent 30-case scratch-repo battery instrument against the UNFIXED hook
> reproduced the audit exactly — 15 gap cases ALLOW, 7 controls BLOCK, 8 false-positive guards
> ALLOW; with post-fix expectations it goes red on exactly the 15 gap rows. **Green:** 30/30 on
> the fixed hook. **Committed:** `tests/guards/test_precommit_blocklist.py` gains 16 block + 5
> allow cases, a staged-bytes-not-working-tree container case, a python3-absent floor test, a
> whole-tree census (population > 900 with staged-count == population proof — the audit's
> `git add -A` trap — plus a planted `schedule_canary.png` that must be the ONLY flag), and the
> suffix sweep REPOINTED (its old core derivation split on a tail the chain form no longer has —
> it would have passed VACUOUSLY; it now reads the extension alternation, with a committed
> negative control proving the any-dot mutant claims the MPXJ jar). **Mutations: 8/8 caught by
> their named rows, zero unexpected flips**, every diff proven non-inert, lead re-ran M2/M7 by
> hand, instruments md5-verified. **The adversarial fan-out (ADR-0240) then found FIVE in-scope
> defect classes** in the mutation-green hook — all lead-re-verified and fixed in the same
> unit: (1) C-QUOTING FAIL-OPEN, pre-existing and severe — `git diff --name-only` C-quotes
> non-ASCII/quote/control names, so `schädule.mpp` bypassed ALL detectors silently (fixed:
> `-z` + `read -d ''`); (2) trailing-whitespace names defeated every end-anchor (fixed:
> matching on a stripped copy); (3) single-quoted MSPDI xmlns — XML-valid, loads identically —
> slipped BOTH signature paths (fixed: quote-agnostic); (4) FP: Hugo/Jekyll `.md` starting `{`
> blocked when quoting the format (fixed: brace must open a JSON object); (5) FP: the PDF
> attachment regex matched printed page text (fixed: bound to `/F`/`/UF` filespec, which also
> catches spaces-in-parens). Battery grew to 42 cases (12 new rows red-first against the
> pre-fix hook, then 42/42), committed tests grew to match, and the 8-mutation battery was
> RE-RUN against the FINAL hook: 8/8 with enlarged expected sets (M7 now flips all three
> templated-doc rows).
>
> ## Next — in order
> **DISC-01 release determination** (operator / authorizing official: the strings are in git
> HISTORY since `a19b969`; private visibility mitigates but does not decide releasability) →
> **001c** the operator's cloud/gateway decision (`APPROVED-GATEWAY-INTEGRATION.md` §6 steps 4–6;
> ADR-0396's chain makes honest gateway wiring mechanical) → PO-03/04/05 parity-oracle gaps
> (PO-03 xfail: the Fuse transcription unguarded against the vendor `.xlsx`) →
> `actual_start_driven` consumed nowhere → ADR-0391's own-calendar floor unguarded → TEST-01
> chromium build-number pins (22 modules) → `_ALLOWED_HOSTS` behavioural sweep + mutation proof
> (data pin exists) → FINAL-REPORT overclaims (condition on `_observed_banner`, do not weaken) →
> 8 stale branches. **Operator:** DISC-01 · the 001c decision · FX-03/04 re-run ·
> sub-day-negative-float Fuse run · license.
>
> ## Carried forward
> ADR-0353..0399 closed — do not re-open. NEW lessons this session: **a guard that sniffs
> extension-less files sniffs ITSELF — never write a detector's signature literal inside the
> detector's own file** (the census caught the wedge pre-commit); **a census needs BOTH a canary
> that must go red AND a staged-set == population proof** — either alone can be vacuously green;
> **anchoring to serialization-start is what lets a content guard cover prose-capable extensions
> at all** (unanchored, it blocks a tracked doc TODAY — measured, not argued); **a predicted
> mutation outcome is not a measured one** — the ADR's M7 sentence was corrected from prediction
> to measurement before commit; **mutation-green is not adversarially verified** — 8/8 by name,
> then the attack round found five in-scope defect classes, one a silent pre-existing fail-open;
> **a guard's input plumbing is attack surface** — `git diff --name-only` emits an ENCODING of
> paths (C-quoting), and every downstream detector was correct while `schädule.mpp` committed
> silently. Standing traps unchanged (a data pin
> guards the literal, not the guarantee · a standing rule is DATA · monkeypatch repoint is per
> CALL SITE · never MEASURE a tree a battery is mutating · never MUTATE an instrument a
> measurement is using · `grep -c` exits 1 on zero · two ruffs on PATH, use `python -m ruff` ·
> `pytest -m parity` alone exceeds 900 s · the container starts with NO deps installed · `git
> fetch origin` before taking an ADR number and again before committing · a number written
> mid-session is not a measurement, `wc` decides). QC-1/QC-2 are ADR-0393, pinned by
> `tests/test_standing_rules.py`.
>
> ## Gate at close
> ruff check . / ruff format --check . / mypy --strict src (152 files) / bandit / node --check:
> all green. Full suite (the run that ships, on the final tree): see the (a) entry's gate line in
> SESSION-LOG. `tests/guards` + `tests/audit` + redaction: 136 passed, 2 xfailed (TEST-01,
> PO-03). Battery instrument 42/42 on the shipped hook; mutations 8/8 against the FINAL hook.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.

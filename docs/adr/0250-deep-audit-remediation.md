# ADR-0250 — deep-audit remediation: CUI-log leak, DOM-XSS embed, cache lock, parity + fail-soft residue

## Status

Accepted. Operator directive 2026-07-17: after PR #388 (ADR-0249) merged, do the housekeeping, then a
**full deep-dive orchestrated audit of the whole repo — "read everything, verify everything, assume
nothing"** (the ADR-0240 "Fable 5 Ultracode" protocol) — fix the verified findings, and write the
handoff + next-session prompt. This ADR records the audit and its remediation.

## Context

The audit ran as a multi-agent orchestration: **ten dimensions** (CUI/Law-1, parity/Law-2, CPM &
forensics correctness, security, performance/memory, data validation, AI figure-gate, web/UI, tests,
docs/state-drift) fanned out over the whole tree, each finding then **adversarially re-verified** by an
independent agent before the lead re-reproduced it against the actual code and fixtures (Law 2: a
mistaken "fix" is worse than the drift it chases). Twenty-two agents; twelve findings survived
verification, **zero refuted**.

The most serious surprise was that the **ADR-0247 redaction fix was incomplete** — a Law-1 CUI leak the
lead reproduced on its own recently-shipped code. This validated the "verify everything, including your
own last change" rule.

## Decision

Fix the ten code/doc findings with regression tests, and **queue** the single finding that needs an
operator decision. Each fix was reproduced by the lead before the change and re-verified after.

### Law-1 (CUI) — HIGH

1. **`logging_redaction.py` — spaced *intermediate directory* still leaked (`spaced-directory-path-leak`).**
   ADR-0247's `_SPACED_FILE_PATH_RE` tolerated spaces only in the FINAL file-name component; its
   directory-prefix branches were built from space-free segments (`[\w.\-]+`). A path whose *interior*
   directory contains a space — the near-universal Windows-profile / OneDrive / UNC-share case
   (`C:\Users\John Smith\…`, `\\server\CUI Share\…`, `/mnt/My Projects/…`) — broke the whole-path match,
   and the fallback path regexes stop at the first space too, so the surname / share / project words
   (and, in the UNC case, the whole file name) survived in clear text in a log line. **Fix:** interior
   segments now use a separator-bounded, length-capped space-tolerant class (`[^\n\\/]{1,120}`) for the
   UNC / Windows / POSIX prefix branches, still anchored on real separators and a final
   sensitive-extension component, so a space-free path with no such file name still falls through to
   the fallback regexes (trailing prose stays safe). Parametrized regression test
   (`test_spaced_INTERMEDIATE_directory_does_not_leak`) asserts none of Smith / Alpha / Rebaseline /
   Share / Projects / … survive, and that `redact` stays idempotent.

### Security — DOM-XSS

2. **`web/app.py` — `SF_RIBBON_DRILL` JSON embed omitted the `</script>` breakout escape
   (`ribbon-drill-json-unescaped`).** The other server-rendered JSON embeds already escape `<` to
   `<` so schedule-derived text can't break out of the inline `<script>`; the ribbon-drill embed
   did not. **Fix:** apply the same `.replace("<", "\\u003c")` to `drill_json` and the new `labels_json`
   before interpolation, matching the established embed pattern.

### Law-2 (parity)

3. **`engine/path_trace.py` — driving-path trace walked THROUGH inactive tasks
   (`pathtrace-ignores-is-active`).** `_scheduled_ids` excluded only summaries, not inactive tasks,
   while the CPM solver (`cpm._scheduled_tasks`) and `driving_slack.date_basis` both drop
   `is_active=False` tasks from the network (ADR-0128: MS Project / Acumen exclude inactive tasks).
   So `ancestors_of` / `descendants_of` could traverse through an inactive task, producing a driving
   path / slack the reference tools would not (a parity break) — or a `KeyError` on an undated inactive
   task. **Fix:** `_scheduled_ids` now excludes `not t.is_summary and t.is_active`, byte-identical to the
   CPM population. Regression test `test_trace_excludes_inactive_tasks` (1→2(inactive)→3) asserts the
   inactive task is not an ancestor/descendant and is absent from the network.

### Data validation / fail-soft

4. **`importers/json_schedule.py` — malformed `day_segments` raised a raw `IndexError`
   (`json-day-segments-indexerror`).** A segment of length ≠ 2 (e.g. `[[5]]`) indexed `s[1]` and threw a
   bare `IndexError`, bypassing the importer's `ImporterError` fail-soft contract. **Fix:** the guard is
   now `isinstance(s, (list, tuple)) and len(s) == 2`, mirroring the `len(pair) == 2` guard the
   custom-field parsing already uses. Test `test_malformed_day_segments_does_not_raise_indexerror`.
5. **`importers/json_schedule.py` — `parse_json` read unwrapped (`json-read-text-unwrapped`).** Unlike
   the MSPDI/XER importers, `parse_json` called `p.read_text(encoding="utf-8")` with no OSError wrapping
   and strict decoding, so an unreadable file surfaced a raw `OSError` and a stray non-UTF-8 byte a bare
   `UnicodeDecodeError`. **Fix:** wrap the read in `try/except OSError → ImporterError` and decode with
   `errors="replace"`, matching the sibling importers.

### Security / supply-chain

6. **`pyproject.toml` — runtime floors admitted published-CVE ranges (`loose-cve-floors`).** `jinja2>=3.1`
   and `python-multipart>=0.0.9` allow versions with known CVEs (jinja2 sandbox escapes
   CVE-2024-56201/56326 & CVE-2025-27516; python-multipart boundary DoS CVE-2024-53981). pip-audit
   catches an *installed* bad version, but a constraints-pinned / offline-mirror install could still
   resolve one. **Fix:** floor at the patched releases — `jinja2>=3.1.6`, `python-multipart>=0.0.18` —
   matching the existing `setuptools>=83.0.0` remediation posture.

### Test-quality

7. **`tests/reports/test_xlsx_zip_bomb.py` — cross-part budget claim not exercised
   (`xlsx-cross-part-budget-unverified`).** The test named "budget spans every part" used a single part,
   so it could not distinguish a shared running budget from a per-part reset. **Fix:** rewrite with two
   parts each under the cap but summing over it, so the assertion fails if the budget resets per part —
   genuinely exercising cross-part accumulation.

### Doc-truth / state-drift

8. **`REPO-INVENTORY.md`** — ADR census `241 files (ADR-0000..0240)` → `251 files (ADR-0000..0250)`
   (`inventory-adr-census-stale`); MPXJ `25 jars` → `24 jars` (`inventory-mpxj-jar-count`, verified
   against `tools/mpxj/lib`); top stamp → `v1.0.59, ADR-0250`; and the concrete runtime-floor line
   updated to the ADR-0250 CVE floors. The deep narrative snapshots that self-declare "may lag —
   pyproject.toml is authoritative" describe historical state (highest ADR 0240, `NEXT: PR-R2 …`) and
   are left verbatim: bumping only their version numbers without rewriting the now-historical prose
   would make them *less* truthful, and the top stamp is the authoritative marker.
9. **`NEXT-SESSION-PROMPT.md`** — the entire "next" queue it advertised (PR-R2/R3/P1) had already merged
   (`next-prompt-stale-queue`); refreshed to the post-ADR-0250 state and the queued operator decision.

### Queued for operator decision (NOT fixed)

10. **`ignore-toggles-noop-on-dated` — "Ignore constraints" / "Ignore leveling delay" trace options do
    not use recomputed CPM dates for dated tasks; the docstring contradicts the behavior.** This is a
    genuine mismatch, but the *correct* resolution is a product decision — either (a) change the trace
    to recompute dates under the toggle (a behavior change with parity implications), or (b) correct the
    docstring/UI to describe what the toggle actually does. Fixing it the wrong way is worse than the
    documented gap. **Queued in HANDOFF for the operator to choose (a) vs (b).**

### Concurrency (found alongside, fixed)

11. **`web/app.py` — polished-narrative LRU cache touched off-lock (`polished-cache-off-lock`).** The
    D18 lock guards the peer caches, but `_polished_narrative`'s `get`/`put` and `ai_off`'s `clear`
    ran outside it. **Fix:** wrap the cache `get`/`put`/`clear` in `with state._lock:` (NOT across the
    slow `backend.generate`, so the lock is never held during model I/O).

Version moves in lockstep: `1.0.58 → 1.0.59`, wheel rebuilt, all 9 installers regenerated (the embedded
wheel byte-matches the patched source tree; `tests/installer/test_installers.py` enforces it).

## Consequences

- The Law-1 log-redaction leak is closed for the realistic spaced-directory case; the redactor now folds
  a whole absolute path with spaces anywhere in it into one inert `<path:ext#…>` token.
- Driving-path traces match the CPM network exactly (inactive tasks excluded), removing a Law-2 parity
  gap and a latent `KeyError`.
- The JSON importer honors the `ImporterError` fail-soft contract for unreadable files and malformed
  calendars, like its MSPDI/XER siblings.
- The ribbon-drill embed is XSS-hardened to the same standard as the other JSON embeds; the runtime
  dependency floors sit above published CVEs.
- One finding is explicitly parked for an operator product decision rather than guessed at.
- The next session starts from a truthful HANDOFF + NEXT-SESSION-PROMPT (the prior queue was fully
  merged) and a refreshed REPO-INVENTORY census.

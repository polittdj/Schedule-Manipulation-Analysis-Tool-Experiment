# Handoff — 2026-08-16 (a) (Ultracode deep-dive audit, unit 1: HOOK-02 — a git-magic filename made every CUI content detector fail open; closed, mutation-proved, ADR-0409; v1.0.207 unchanged)

> ## STATUS (current) — audit IN PROGRESS on `claude/nasa-itar-ai-desktop-launch-scx3gz`.
> Highest ADR now **0409**. **NO shipped code changed** — `.githooks/` + tests + docs only:
> version stays **v1.0.207**, SCHEMA 2.11.0, no wheel/installer rebuild (verified twice: the
> built wheel contains no `.githooks/` entry, and ADR-0399 set this precedent for HOOK-01).
> The operator ordered a COMPLETE repository deep-dive audit (ADR-0240 Ultracode): find
> everything wrong, prove each finding with pass+fail tests, sandbox-verify every solution
> BEFORE implementing, triple-verify independently, and cover every page/route with pass and
> fail tests. Round 1 ran 1 of 16 agents before a credit exhaustion killed the rest; round 2
> (11 dimensions + route census + critic) is running. **This handoff will be superseded as
> further units land — the audit is NOT finished.**
>
> ## What landed — ADR-0409 (HOOK-02, Law-1 critical)
> `.githooks/pre-commit` read staged bytes as `git show ":$path"`, so the NAME's leading
> bytes parsed as git magic: `!x.json` (exclude-pathspec), `^x.json` (negated revision),
> `0:x.json`/`1:x.json` (merge-stage syntax), `:(icase)x.json` (pathspec magic). Each
> returns EMPTY output, which every content detector reads as "clean" — so a real CUI
> schedule committed SILENTLY under `!plan.json` (a plain `git add -A` stages such names).
> The extension detector still fired, so the hole was exactly the classes where the content
> sniff is the ONLY barrier: `.json` (the tool's own Save format, deliberately not
> gitignored), `.txt`, extension-less, `.md`, images, PDFs, archives. Fixed by resolving the
> INDEX OID (`git --literal-pathspecs ls-files -s -z` → `git cat-file blob`) in BOTH the bash
> and python detectors — the name is then only ever a pathspec.
> **THREE traps paid, all by measurement:** (1) the finder's proposed `--` fix was WRONG —
> sandbox-measured before implementing, it leaves `:<stage>:` open; (2) the first
> implementation used `head`/`cut`/`tr` and WEAKENED the guard — the repo's own
> `test_hook_without_python3...` floor test caught it, so the helper now parses with bash
> BUILTINS only; (3) with an outcome-only assertion **3 of 4 mutants SURVIVED including a
> full revert of the bug**, because the bash and python sniffers are defence-in-depth twins
> over the same files — `test_bash_floor_blocks_git_magic_names_without_python3` pins the
> bash LAYER on a git+grep-only PATH, and M4 needed a colon-leading name added before it was
> killable at all ("a mutant that cannot fail is not a mutant", ADR-0408).
> **QC-1 triple verification:** 6 new tests red BY NAME pre-fix → module 90 → **98 passed**;
> an INDEPENDENT bash battery written before the tests (10 hostile shapes blocked, 4 benign
> controls still allowed, ADR-0152 inherited/tampered pair intact); mutation battery **4/4
> caught by the named test**, hook restored md5-identical, controls green both sides.
>
> ## Next — the audit continues
> Round-2 dimensions in flight: CPM/float · metric formulas vs the NASA `.aft` · Monte-Carlo
> (sra/jcl/correlation) · findings/trend/manipulation · importers · web core (routes+state) ·
> page modules A/B · static JS · **the test suite itself** (green-tests-that-cannot-fail) ·
> docs/config/CI · AI figure-gates. Then: lead re-verification of every survivor, red-first
> fixes in gated units, and the route×test gap-fill — the lead's independent inventory is
> **137 routes** (65 page · 34 api · 38 export), which is the denominator for the operator's
> "pass AND fail tests for every page" requirement.
>
> ## Carried forward
> ADR-0353..0409 closed — do not re-open. NEW lesson: **a defence-in-depth twin makes an
> outcome assertion blind to a layer dying** — when two detectors cover the same input, an
> end-to-end test cannot prove either one works; run one layer alone (thin PATH) to pin it.
> And **a suggested fix is a hypothesis**: the finder's `--` patch passed its own reasoning
> and failed the sandbox. Standing traps unchanged (see the archive — data pins vs
> guarantees · monkeypatch per CALL SITE · never measure a mutating tree · never mutate a
> measuring instrument · two ruffs, use `python -m ruff` · parity >900 s · container starts
> with NO deps · fetch before numbering and before committing · `wc` decides). QC-1/QC-2 are
> ADR-0393, pinned by `tests/test_standing_rules.py`.
>
> ## Gate at close
> Statics green (`python -m ruff check .` whole tree · format --check · mypy strict 155
> files · bandit · node per-file). Full suite: **4094 passed, 47 skipped (env-gated
> playwright), 0 failed, exit 0, 29:50** — exactly +15 over ADR-0408's 4079, matching the
> 15 new HOOK-02 cases. Parity: **72 passed, 15 skipped, exit 0, 8:55**. Drift guards 5/5.
> No wheel/installer rebuild (`.githooks/` ships in no wheel — verified against the built
> v1.0.207 artifact; ADR-0399 precedent).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.

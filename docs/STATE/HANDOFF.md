# Handoff — 2026-08-13 (full-repo audit; the approved-gateway class enters Band 1; v1.0.199)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-data-date-fix-065mz7`,
> restarted from `main` **cacd769** after #578 squash-merged (`git fetch --prune` + `checkout -B`,
> per the post-squash-merge rule). ADR-0391 is **on main**; highest ADR still **0391** (this session
> added no ADR — see "the one decision that is NOT mine" below). Version **v1.0.198 → v1.0.199**;
> wheel + nine installers rebuilt. SCHEMA stays 2.11.0.
>
> This was an **audit session**, not a feature session: seven parallel dimension readers over the
> whole repo, each finding re-verified by an adversarial pass, then reconciled by the lead against
> code evidence (ADR-0240). **57 findings — 37 CONFIRMED, 20 OVERSTATED-and-narrowed, 0 refuted.**
> The verifiers narrowed a fifth of the findings, which is the point of running them.
>
> ## THE HEADLINE — POLARIS is running against a NASA-approved AI gateway, and the repo did not know
> The operator obtained NASA approval and pointed POLARIS at
> `https://proxy.fast.luna.nasa.gov` / `claude-opus-4.8-thinking-itar` **on their own Windows
> machine**. Another assistant session patched `ai/backend.py`, `web/app.py`, `web/settings.py` and
> added a hostname allowlist entry **in that local install**. It works — catalog populates, Opus 4.8
> answers return.
>
> **None of it is in this repository.** Verified: zero hits for `POLARIS_GATEWAY` / `luna.nasa.gov` /
> `opus-4.8` across `src/`, `tests/`, `tools/`, `installer/`. Unversioned, untested, outside CI, lost
> with that machine. **Do not read that absence as evidence the gateway is unused — it is in use.**
> Full writeup, anchor by anchor: **`docs/PLAN/APPROVED-GATEWAY-INTEGRATION.md`** (new this session).
>
> ## THE CRITICAL FINDING — the Law-1 guarantee is one unpinned frozenset
> Everything funnels through `net_guard.py:127` `_LOOPBACK_HOSTNAMES = {"localhost","ip6-localhost"}`
> via `is_loopback_host` (`:223`) → `is_local_http_endpoint` (`:237`), consumed at `ai/ollama.py:130`,
> `ai/openai_compat.py:39`, `web/app.py:6406/6408/6447`, `launcher.py:232`, `web/app.py:8018`.
> **No test pins its contents.** An agent EXECUTED the widening in memory (no repo file touched):
> adding `proxy.fast.luna.nasa.gov` → **226 guard/AI/air-gap/startup tests passed**; a second agent
> reproduced it at **854 green**. The suites pin only sampled negatives (`8.8.8.8`, `evil.com`, …), so
> a *named* allowlist entry is invisible to all of them. **The exact change made on the operator's
> machine cannot be detected by this repo's CI, by review, or by a future green suite.**
>
> ## THE DESIGN DEFECT THAT CAUSED IT
> There is **no working gateway path**. `route_backend` takes a `cloud_backend` (`ai/backend.py:117`)
> that **no production caller supplies** (`web/app.py:832-837`, `web/settings.py:346-351`), and
> `ai/cloud.py` does not exist — yet `web/settings.py:449` still offers "Cloud (UNCLASSIFIED only)".
> So the only route that works is **widening the loopback validator**, which silently re-labels a
> remote host as local everywhere at once. The architecture channels a legitimate, approved need into
> the most dangerous possible change. That is a design defect, not operator error.
>
> ## WHY THE BANNER LIES — enforced by a validator, never observed
> `route_backend` returns the literal `Local-only — no data leaves this machine.` for BOTH the
> `ollama` and `openai` paths (`ai/backend.py:129-131`, `:144-147`) — no classification check, no
> endpoint inspection. `banner_for` (`:99-108`) is **config-derived**, and `web/chrome.py:175` renders
> exactly that, so a gateway that is DOWN (routing correctly falls closed to Null) still shows as up.
> `route_backend`'s own Banner is dead code. `AIBackend.is_local` is a hardcoded class constant that
> `route_backend` never reads — there is no runtime concept of "remote" anywhere in the object graph.
> Executed probe: with the allowlist widened, `is_local_http_endpoint(gateway)` → **True**, backend
> constructs, banner reads **"Local-only"**. Six user-visible claims become false, plus four i18n
> translations — and **two print inside EXPORTED exhibits** (`ai/brief.py:625`, `web/sra.py:1076`), so
> a document that leaves the machine can carry a printed assurance that nothing left.
>
> **Scoping correction the adversarial pass forced, and it matters:** nothing in THIS repo falsifies
> those sentences. The shipped build's validators hold; the claims are true *as shipped*. They are
> false only of a **patched install** — the operator's. The docs are not lying today; they are
> unconditional where they must be conditional, guarding a promise nothing pins.
>
> ## GOOD NEWS — an honest gateway needs NO new dependency
> `ai/openai_compat.py` transports over **std-lib `urllib`** and already speaks the OpenAI wire
> format, so a first-class `GatewayBackend` keeps `litellm`/`openai`/`anthropic`/`boto3` banned
> (`net_guard.py:60-120`) and the egress guard green. Surgical, not architectural. It also makes the
> loopback **shim** strictly worse than a direct backend: a shim is banned-dependency third-party
> software, in no ATO, and — being on loopback — structurally unverifiable by the tool.
>
> ## Shipped this session (small, and all of it my own defect from ADR-0391)
> Three user-visible strings still called the CPM finish **"pure-logic"**, which ADR-0391 made false:
> `engine/forecast.py:85` (the basis line on /forecast), `web/forecast.py:219`, `web/chrome.py:470`.
> Fixed. The ~15 other `pure-logic` hits are about **float/critical basis**, which ADR-0391 did not
> touch — deliberately left. No test asserted the three phrases; the oracle carries zero /forecast
> labels.
>
> ## The one decision that is NOT mine — why there is no ADR-0392
> The audit's recommendation is to either **delete** the dead cloud option or **build** a
> `GatewayBackend`. That is an architecture-and-accreditation call belonging to the operator, so it is
> written up as a PLAN doc and queued as **DoD 001c (`human`)** rather than decided here. The next
> session should open ADR-0392 once the operator picks.
>
> ## Next — Band 1 first, in dependency order
> **001a** pin the allowlist contents + mutation proof (land FIRST, alone; closes the gap whether or
> not a gateway is ever built) → **001b** observed banner → **001c** operator's cloud/gateway decision.
> Then the audit's other confirmed items: `actual_start_driven` is computed but **consumed nowhere**
> (ADR-0391 promised it as the disclosure surface; no analyst-facing notice exists) · ADR-0391's
> **own-calendar** floor branch is behaviorally unguarded — deleting it leaves the engine suite AND the
> parity gate green · `mpxj_ref()` still has no shallow-clone guard and its test checks only 40-hex
> shape (DoD 117 — it FIRED last session) · the pre-commit guard has **no image detector** and 120
> tracked PNGs exist · 22 playwright modules hard-pin a chromium BUILD NUMBER · FINAL-REPORT's parity
> and no-egress evidence cells overclaim · 8 stale remote branches, all 148-611 behind (DoD 091).
> **Operator:** the 001c decision · FX-03/04 re-run · the sub-day-negative-float Fuse run · license.
>
> ## Carried forward
> ADR-0353..0391 closed — do not re-open. NEW lessons: (1) **a guard is only as strong as the test
> that pins its DATA** — sampled negatives prove nothing about a named allowlist entry; (2) an
> architecture that offers no legitimate path to a real need will get the dangerous path taken —
> the dead `cloud` option is what pushed a lawful requirement into the loopback validator; (3) a
> claim derived from CONFIG describes intent, not behaviour — banners must be observed; (4) verify
> the SCOPE of a doc-truth finding: "the docs are false" and "the docs are false of a patched
> install" are different claims and only one is true. Standing traps unchanged (a fixture generated
> by a rule cannot validate that rule · the corroborating oracle may already be in a doc nothing
> cross-references · an ADR's observation can be right and its diagnosis wrong · a new disclosure
> needs its own channel when the existing one carries a JUDGEMENT · a sweep's glob/population/pattern
> are part of its claim · `| head -N` can SIGPIPE-kill a build mid-way · the MPXJ pin drifts in a
> shallow clone (FIRED) · never MEASURE a tree a battery is mutating · never MUTATE an instrument a
> measurement is using · `grep -c` exits 1 on zero · two ruffs on PATH, use `python -m ruff` ·
> `pytest -m parity` alone exceeds 900 s · the container starts with NO deps installed ·
> `git fetch origin` before taking an ADR number and again before committing). A number written
> mid-session is not a measurement (`wc` decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.

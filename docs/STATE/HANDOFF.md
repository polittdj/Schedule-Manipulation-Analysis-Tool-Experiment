# Handoff — 2026-09-11 (c) (OR-14 CLOSED (ADR-0485): the local OpenAI-compatible server learns to authenticate — the Ask panel's HTTP 403 was LM Studio refusing an unauthenticated generation, and the tool had nowhere to hold a token; v1.0.255)

STATUS (current) — `main` @ **`5d8d01fb`** (#668, ADR-0484 / v1.0.254, tree-verified after the squash). **This session's second unit answered the operator's screenshot** — `/integrity`'s Ask panel, backend = OpenAI-compatible (LM Studio on `:1234`): *"the model server at http://127.0.0.1:1234 was reachable, but the generation itself failed: server returned HTTP 403. AI Settings shows its live status."* The deep dive (three hypotheses refuted on the code first: a corporate proxy — the client already bypasses every proxy; a wrong model id — a 404/400 shape; the Ollama path — not involved) found the local `openai` backend has **ZERO credential surface** — no `AIConfig` field, no form input, no constructor parameter, no header slot in its 3-arg opener — while LM Studio 0.4+ can *Require Authentication*: ADR-0403's defect class, closed for the gateway a month ago and left open for the local server. **ADR-0485, v1.0.255:** a **Local server API token** field (masked, never echoed, blank keeps, persisted under the ADR-0404 protector as `openai_api_key_dpapi` / `_plain`, forgotten by ai-off and a wipe), sent as the Bearer header on EVERY request to the loopback server (probe, catalog, generation, the cross-check second model, the live model dropdown — from the SESSION's saved token, never a URL), nothing at all when empty; the Ask note and the settings hint NAME the field on a 401/403 and state the cause the tool cannot see (authentication off → the server or something in front of it; check its log); the gateway's generation failure no longer mislabelled with the local address. Red-first on a pristine `origin/main` worktree (**25 new tests → 23 failed / 2 negative pins**; the four migrated 4-arg doubles red too), the operator's sentence reproduced verbatim on the wire against a loopback stub; **30 mutants / 30 red by name**; touched neighbourhood **314 passed**; full suite **5,238 passed / 5 skipped in 35:52**; `-m parity` **96 passed**. **Draft PR #669**, head `e9387761` (branch `claude/optimistic-ride-3qv2jc`; eight checks expected — `installer/**` changed; the SESSION-LOG follow-up records the verdicts). Highest ADR **0485**. QC-1/QC-2 bind every session — ADR-0393.

**CARRIED FORWARD, still live and NOT this unit's:** `test_driving_path_whole_schedule_browser.py:104` is **width-racy** (registered by #667: red on a docs-only PR while `main` passed the identical code two minutes earlier; it compares the rendered `thead` inner_text of two separately rendered pages while both captures wait on ROWS, never on the timescale — a race with a mechanism, not a flake; its own unit, never fixed by widening a wait).

## What landed, in one paragraph

`AIConfig.openai_api_key` (`repr=False`, in equality) · `ollama.HeaderOpener` + `_urllib_header_opener` + `is_auth_refusal` (word-bounded `HTTP 401|403`) · `OpenAICompatBackend(api_key=…)` on the 4-arg opener (Ollama keeps the 3-arg one — no auth dimension) · `factory.openai_or_none` / `second_or_none` thread it · `/api/ai/models?kind=openai` uses the session token · `config_store` generalised to two protected fields (`_protect_into`, `_load_key(doc, field, what)`) · the form field + placeholder + blank-keeps POST · `_generation_failed_note`'s 401/403 branch (local: the field + the honest alternative; gateway: the *Gateway API key* field) + each backend's OWN endpoint · the refused-probe hint on `/settings` and `_no_model_note`'s refused-probe branch on the Ask panel (no more *"Start your local server"* / *"Start it"* for a server that answered). Refused and named in the ADR: an env-var fallback (ADR-0404 removed the friction it solved), an undocumented `x-api-key` header.

## UNVERIFIED, stated — what the operator's machine will settle

- LM Studio's exact refusal code (401 vs 403) and whether `GET /v1/models` is exempt: the docs page read (its GitHub docs repository, `authentication.mdx`; lmstudio.ai was egress-blocked — no verified URL recorded) does not say. The fix accepts both codes and both catalog shapes (the stub's second mode guards the catalog too).
- The menu path in the note and the field's tooltip (*Developer → Server Settings → Require Authentication → Manage Tokens*) is as read on 2026-09-11 and can drift with the vendor's UI.
- If the 403 persists WITH a token saved: the token is wrong/revoked, or something on the machine sits in front of the server — the note now says so instead of "open AI Settings".

## Traps this session paid for, by name

* **A diagnostic that names a PAGE is true and useless when that page reads ON.** "AI Settings shows its live status" was literally correct — the probe passed — and there was nothing on the page that could resolve a 403. Name the actionable FIELD; state the cause you cannot see.
* **"Start your local server" for a server that ANSWERED is exactly the wrong advice** — condition the hint on what the transport proved, not on "unreachable" as a catch-all.
* **A page-wide `FIELD in page` assertion cannot fail when the form's own label carries the name** — read the element (the `notice err`), and pin the WRONG advice absent too. Found while writing the test, before the battery.
* **Negative pins are green on the pristine tree by construction** (2 of 25 in the red run) — their teeth come from a mutant that makes the branch fire where it must not; four mutants did (`auth_refusal_matches_404`, `auth_refusal_unbounded`, `ollama_gets_the_token_note`, `probe_note_for_ollama_too`).
* **The battery's "exactly once" anchor guard fired again** — a second, byte-identical `held` block made two mutants abort as `ANCHOR x2` rather than mutate the wrong branch; re-aim on the branch's own text (ADR-0484's lesson, paid for twice now).
* **The same defect class landed twice** (ADR-0403 remote, ADR-0485 local): every OpenAI-compatible surface needs the credential dimension from day one — vendor auth features arrive AFTER the integration is written (LM Studio 0.4.0's tokens post-date this backend).
* `/root/.local/bin/ruff` 0.15.8 still shadows CI's `/usr/local/bin/ruff` 0.16.7 on PATH — run both; the clone is unshallowed, so `git log -1 -- tools/mpxj` reads `42d92dc9` itself and the builder needs no `--depth` remedy.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha written here** — six consecutive kickoffs arrived stale.

**R-56** (add UID 385, seven heads, both `pc == 0`) · R-49 · R-46 · R-47 · R-52 · R-50 · R-57/58/59 · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. Other residuals: ADR-0483's own (a live-peer response is cut at 5 s) · `/settings` horizontal overflow (its own UI unit) · OR-11b (measure the 48-fact cap on a real 32-file workbook first) · OR-11d · the working-minute axis cannot carry a recorded instant on a day boundary · the hint bubble still widens the document while OPEN · ADR-0484's in-grid scorecard rows as the mock's compact status-pill row without losing table semantics · **NEW (ADR-0485):** `_gateway_status_note` still detects a refusal by substring (`"401" in reason`) — a one-line unit onto `is_auth_refusal` with its own red; the live model dropdown probes with the SAVED token only (Save first — the gateway behaves the same). **The design page: 10 done, 20 artboards remain; next by cost is `/margin` (Control Margin Dashboard, `setScreen('mg')`), the last Control screen.**

**Review cover is still absent** — Codex quota EXHAUSTED on #655–#668; the mutation battery and the full gate are all this repo gets.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.

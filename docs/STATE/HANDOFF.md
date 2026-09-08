# Handoff — 2026-09-08 (b) (Ask-the-AI stopped lying about why it has no answer (ADR-0478): five different failures shared ONE payload and ONE sentence — now each names itself and the operator's next action; v1.0.248)

STATUS (current) — Branch `claude/polaris-audit-r55-r20-handoff-uoa34g` (the harness's designated branch), started on `origin/main` @ `9eeff406` (#653's squash). One unit, engine-untouched, UI + API, proven red-first and mutation-tested 9/9. Highest ADR **0478**. Version **1.0.248** (wheel + nine installers rebuilt AFTER the last source edit; `SF_MPXJ_REF=42d92dc9acc98f7d87f19c82dc62be3e5d3c15ca` — this container is a SHALLOW clone, so `git log -1 -- tools/mpxj` resolves to the graft boundary and the build REFUSES it; the override's `tools/mpxj` tree was verified byte-identical, `2001032378e5253edaecf0a8fe142bcbd54f666e` on both). QC-1/QC-2 bind every session — ADR-0393, pinned by `tests/test_standing_rules.py`.

## The operator's report, and what was actually wrong

A 32-version workbook, a long manipulation question about UID 152 on `/integrity`, AI Settings showing a configured model — and the panel answered *"No local model is active (or strict mode discarded its answer)."* **The root problem is not the AI stack; it is that `/api/ask` is not self-diagnosing.** Measured end-to-end against a real loopback fake-Ollama with 32 synthetic versions and the operator's verbatim question: a routed Null backend, an unreachable Ollama, an Ollama that 404s the generation (the selected model was never pulled), a generation that times out, an empty completion and a strict-mode discard **all returned the identical payload** — `answer: null` and no other key — so one hard-coded `ask.js` sentence had to cover all six. It led with the cause the operator can see is false, and offered a strict-mode discard **in ANNOTATE mode, the default, where a discard is impossible** (`qa.answer_question` discards only under `strict`). The diagnosis was already WRITTEN — `settings._ai_status_note` says "could not reach Ollama at …" and "the selected model … isn't installed" — on a page the operator has to go looking for, never at the point of failure.

**The fix.** `ai/qa.py` gains `NoAnswer(code, detail)` + `answer_question_detail(...)` (four codes: `no_model` · `generation_failed` · `empty_answer` · `discarded_unsourced`); `answer_question` stays a two-tuple wrapper so its dozen call sites are untouched. `web/app.py` gains `_no_answer_note(cfg, why)` — the half that needs the OPERATOR'S CONFIGURATION (which endpoint, which model, which timeout, which mode) and therefore cannot live in `ai/` or in the client — shipped as `no_answer: {code, text}`. A 404 on Ollama re-probes `/api/tags` and names the model, lists what IS installed and prints the `ollama pull` command: `is_available()` asks `/api/tags` and NEVER whether the configured model exists, which is exactly how a reachable server produced "no local model is active". `static/ask.js` renders the server's sentence and degrades to a usable line without one.

**What it does not do:** it does not make a model appear. If Ollama is down the tool still cannot answer — it now says so in the operator's own configuration terms instead of guessing.

## Traps this session paid for, by name

* **A green mutation is a finding about the TEST.** The first battery returned 8 RED / 1 GREEN: "a non-strict cause blames strict mode" walked straight through, because the endpoint-level test only ever exercises the `ollama` branch and the leak was planted in the AI-switched-off sentence. Remedy: `test_only_a_strict_discard_ever_mentions_strict_mode`, a census over every cause × every backend selection straight at the composer. 9/9 RED after.
* **Re-aim a monkeypatch per CALL SITE, not per name** (ADR-0390's rule, paid again). The primary answer moved to `answer_question_detail`; two existing tests patch `app.answer_question` to intercept it. They went red rather than silent — and the cross-check second model still calls `answer_question`, so `test_ask_response_skips_agreement_when_an_answer_is_empty` patches **both**.
* **The census's first assertion was over-specified.** "Five causes ⇒ five distinct CODES" is false by design: *AI switched off* and *server unreachable* are both `no_model` and are separated by their SENTENCE. The contract is five distinct sentences; the codes name the class.
* **A shallow clone refuses the installer build** — `git log -1 -- tools/mpxj` returns the graft boundary. `SF_MPXJ_REF` + `git fetch --depth 1 origin <sha>` is the whole remedy; the script verifies tree-identity itself.
* **`python -m pip install -e '.[dev]'` read-timed-out twice on this container**; `uv pip install --system -e '.[dev]'` completed. Nothing was wrong with the network (pypi answered `200` in 0.08 s).

## Next — campaign queue

Unchanged and untouched by this unit: R-56 (add UID 385, seven heads, both `pc == 0`; it is what tightens updated3's −13 d) · R-49 (MPXJ omits a ZERO TotalSlack) · R-46 · R-47 · R-52 · R-50 · R-57 / R-58 / R-59 · then R-03 / R-04 / R-09 / R-13 / R-18 / R-21 / R-22 / R-32 / R-39. Residuals still registered: the working-minute axis cannot carry a recorded instant on a day boundary or a non-working moment (2 of 42 on updated3, 19 of 699 on LTF); the hint bubble still widens the document while OPEN. **NEW residual:** `_AskRecord` — and therefore the Q&A Excel/Word export — still records only `answer=None`, so an exported unanswered ask does not carry its reason. PLUS the design page owed each session — still current, not owed: the next Control screen is `/scorecards` (`setScreen('sk')`), next by cost, 21 artboards remaining (report §6).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.

# ADR-0481 — The operator can set the Ollama context window, and is told what it costs

* **Status:** Accepted (2026-09-09)
* **Unit:** OR-11e (operator queue) — the half ADR-0480 deliberately did not ship
* **Supersedes nothing.** Extends ADR-0480; ADR-0315's env reporting is unchanged.

## Context

ADR-0480 shipped a disclosure: when Ollama's own `prompt_eval_count` proves the model
evaluated fewer tokens than the prompt could possibly contain, the answer says so. That
closed the *silence*. It did not close the *loop*, and it said so in its own "Not done":

> the tool still does not SEND `num_ctx`. Adding an operator-set window is a separate unit.

So the disclosure named a remedy the tool could not perform. An operator reading
"Raise the window (`OLLAMA_CONTEXT_LENGTH` on the Ollama server)" had to leave the tool,
find the server's environment, set a variable, and restart Ollama — for a setting the tool
sends on every request anyway. Every other decoding parameter (`temperature`, `seed`,
`top_p`, `keep_alive`) is ours; the one that decides how much of the evidence the model
reads was the server's alone.

**Why ADR-0480 stopped where it did, and why that reasoning still binds.** Raising the
window is not free and is not reversible from the tool's side: the KV cache scales with it,
and `ollama/ollama#14073` — the issue recording that Ollama's defaults became VRAM-tiered in
v0.15.5 (`< 24 GiB` 4,096 · `24-48 GiB` 32,768 · `>= 48 GiB` 262,144) — reports a **machine with 52 GB
of VRAM going unresponsive** once the larger default spilled out of GPU memory. A tool that
silently raised `num_ctx` to make its own warning go away would be handing the operator that
outcome to fix a cosmetic problem. That refusal was correct and is not revisited here.

## Decision

**Ship the lever, off by default, bounded, and carrying the evidence that made the refusal
correct.**

* **`AIConfig.num_ctx: int = 0`.** Zero requests nothing: `generate()` omits the key
  entirely, so the request is byte-for-byte what every install sent before this ADR and the
  server's own default (`OLLAMA_CONTEXT_LENGTH`, else its VRAM tier) still governs. Omitting
  a key is not the same as sending a default, and an upgrade must not start dictating
  allocations to machines whose operators never asked.
* **Bounded at every boundary it crosses** (`ollama.clamp_num_ctx`): the settings form, the
  persisted settings file, and the `OllamaBackend` constructor each clamp, because each is
  separately reachable — a hand-edited `ai-settings.json`, a direct construction in another
  caller. `MIN_NUM_CTX = 2,048` (below it the request is self-defeating: this tool's fact
  sheets do not fit, so the "window" guarantees the truncation the warning exists to report).
  `MAX_NUM_CTX = 262,144`, **not a number of ours**: it is Ollama's own default for the
  `>= 48 GiB` tier, so the tool can never request more than the reference implementation
  would hand the largest machine it recognises. It is a **bound, not a safety guarantee** —
  #14073's 52 GB-VRAM machine was at that very number.
* **The cost is stated where the value is typed** (`web/settings.py::_num_ctx_cost_note`).
  The note gives the mechanism (KV cache grows with the window), the multiplier
  (`OLLAMA_NUM_PARALLEL`, already reported on this page by ADR-0315), Ollama's own tier
  defaults as the calibration, and the reported incident, **attributed**. It also reports
  what is actually in force — "the tool sends no window" vs "the tool asks for N tokens" —
  because a claim derived from configuration describes intent, not behaviour (QC-2).
  **No GB-per-token figure is given.** That depends on the model's layer/KV-head geometry and
  cache dtype, none of which this tool reads; a fabricated number on a page an operator sizes
  hardware from would be worse than no number at all.
* **The cross-check model gets the same window.** It reads the same fact sheet, so a window
  granted to the primary and withheld from the second model would truncate exactly the
  comparison the cross-check exists to make.
* **ADR-0480's disclosure is kept true against its own product.** `GenerationStats` gains
  `num_ctx_sent` — a record of *our outbound payload*, never a claim about what the server
  allocated — and the warning now names the window already requested rather than telling an
  operator to raise what they raised. Both remedies stay named.

## Consequences

* An operator who hits the evidence warning has an in-tool remedy for the first time.
* The default configuration is unchanged in behaviour. Every settings file written before
  this ADR lacks the key and loads as OFF; a non-integer or a JSON `true` also loads as OFF.
* **UNVERIFIED, and deliberately not claimed anywhere in the product:** what the server DOES
  on receipt. There is no Ollama in this container, and ADR-0480 already recorded the
  truncation semantics as not verbatim-confirmed against primary sources. What is proven
  here is what *leaves the tool* — the request payload — which is the whole of what the tool
  controls. The UI says "asking is not allocating: the server decides, and it may refuse or
  cap it", which is the strongest honest statement available.
* Ollama-only. An OpenAI-compatible local server has no such parameter and is untouched.
* Law 1 is unaffected: no new endpoint, no new transport, no new dependency; one integer is
  added to a request that already went to the same loopback address.

## How it was proven

Red first: both new modules failed at collection (the API did not exist). Then a **20-mutation
battery**, each mutation applied in a sandbox copy and required to turn a **named** test red —
20/20 did. Two of them did not, first time round, and both were findings about the tests, in
the shape ADR-0480 paid for by name: the cost-note checks searched the **whole page body**,
which already contains `OLLAMA_NUM_PARALLEL` (the ADR-0315 env report) and `262,144` (the
input's own `max=`), so deleting the note entirely and gutting its text both walked straight
through. Re-aimed at the note's own output plus a separate "the page carries this note"
assertion, both go red.

`/settings` was **rendered** over loopback in all four themes (console / daylight / apollo /
jarvis): the field and the note are visible, zero page errors, and the field reports the
clamped value the server actually saved.

## Registered, measured, and NOT taken here

`/settings` scrolls sideways at a 1440-px viewport — `document.scrollingElement.scrollWidth`
**1877 / 1641 / 1877 / 1877** (console / daylight / apollo / jarvis). **This is not ours**:
the identical figures were measured on a pristine `HEAD` worktree as the control, and the
widest element is the `AI answer mode` `<select>`, which Chrome sizes to its longest option
("Annotate (default) — the model may analyze and derive figures…"). ADR-0477 closed R-20 /
UI-03 for the **four routes its guard renders** (`/`, `/driving-path`, `/evolution`,
`/standards`) and for the **hint-bubble** mechanism; `/settings` was never in that census and
its overflow has a different cause. The summary "every page measures 1440" is therefore
broader than what was measured. Fixing it is a UI unit with its own Definition of Done — an
over-wide `<select>` is a content-and-layout decision, not a one-liner — so it is registered
as a residual rather than bolted onto this one. This change added nothing to the number: the
totals are byte-identical to the control in all four themes.

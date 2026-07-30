# Operator requests — the standing intake queue

Verbatim-intent capture of feature requests the operator raises mid-session, parked here so they
survive the session that received them. **This file is durable state** alongside `HANDOFF.md` /
`SESSION-LOG.md` / `LESSONS-LEARNED.md`: an item is added the moment it is raised, and removed only
when it ships (with the ADR / PR that closed it recorded on the line).

Status vocabulary: `OPEN` (not started) · `IN FLIGHT` (a round owns it) · `SHIPPED (ref)` · `PARKED
(reason)`.

---

## 2026-07-28 — `07282026_Prompt_Notes.docx` (received mid-round-11)

### OR-01 — Per-project summary must name what each metric is computing · `OPEN`

Every individual project schedule should list, **for every file**:

- SITE / COMPANY
- VERSIONS
- LATEST DATA DATE
- COMPUTED FINISH
- EFFECTIVE MARGIN
- DCMA-14 score

…and when the project is **wrapped up** (the rolled-up, one-row-per-project view), show:

- the SITE / COMPANY name
- the **number of versions** (how many schedules make up the project)
- the **LATEST DATA DATE** of the latest file
- the **most recent COMPUTED FINISH DATE**
- the **most recent EFFECTIVE MARGIN**
- the **average DCMA-14 score across the schedules**

**And the metric TITLE itself must make clear what the view is computing** — i.e. a rolled-up column
must say so in its heading ("Average DCMA-14 across N versions", "Latest data date"), never reuse the
per-file label for an aggregate. Reading the title alone must tell the analyst whether they are
looking at a latest-value or an average.

*Implementation notes for whoever picks this up:* this lands on the portfolio/ledger surface
(`_portfolio_body`, `/portfolio`) and the per-project card views. Law 2 applies — the aggregation rule
for each column is a **stated** rule (latest vs mean), and the heading must match the rule the engine
actually applied. Do not invent an aggregate the engine does not compute.

### OR-02 — A help call-out sticks over the left menu bar and cannot be dismissed · `SHIPPED (ADR-0314)` · **BUG**

> "I keep getting this weird call-out that covers the menu bar on the left side of the screen that I
> can't get to go away unless I switch to another page but then it will return. This should never
> happen. It is the DCMA 11 — Missed Activities call-out which explains what it is, why it matters,
> threshold, pass example, etc."

Reproduced, measured, and closed as **two** defects in the DCMA-overview float tip (`app.js`, not
the hint layer the notes guessed): a FOCUS-shown tip (what a click/tap does) had no reachable
dismissal — Escape, pointer-away, and alt-tab all stuck — and the nav-avoidance clamp tested for a
`fixed` header only, so daylight's `sticky` full-width bar was never avoided (overlap measured at
three viewport sizes). Fixed with document-level Escape/pointer/blur dismissal + a fixed-OR-sticky
clamp that clears a rail sideways and a bar downward. Both pinned by measured-box tests
(`tests/web/test_float_tip_dismiss.py`, the operator's own DCMA-11 callout by name). ADR-0314.

### OR-03 — Launch Sequence: motion + a full-length boot hum while projects load · `OPEN`

On the boot-up start screen (the **Launch Sequence**):

- keep the visuals showing **while projects are loading**, with "something flying around" so it is
  unmistakable that the tool is working and **not frozen**;
- play a **longer version of the Boot Audio "Hum"** for the **entire** load;
- **mix the audio correctly** if a loop is used — no audible seam;
- the source audio must be **at least a minute long** and must **not be one repeating sound**: a
  *series* of similar sounds, a *pattern* of the "Hum" boot audio.

*Implementation notes:* the loading indicator must be driven by real load state (start on upload,
end on ready) — never a fixed timer that lies about progress. Honor `prefers-reduced-motion` for the
animation and keep audio opt-in/mutable per the design system's a11y line. Audio must be a **local,
vendored** asset (Law 1: no remote fetch, and the air-gap test must stay green).

---

## 2026-07-30 — chat report (mid-planning session)

### OR-04 — Ollama's model runner keeps the GPU after quit · `SHIPPED (ADR-0315)` · **BUG**

> "when I open the tool and then close the tool Ollama stays active and it is eating up my
> Dedicated GPU memory."

Reproduced by the operator (enable in AI Settings → ask → wipe → quit): `llama-server.exe`
resident post-quit at ~10.9/12 GB dedicated VRAM and ~30 GB committed shared GPU memory, while
both of the tool's own cleanup taskkills reported "process not found". Behavior ruling (operator,
same day): **free the GPU on exit** — stop the runtime if the tool started it; if it is an
external service the tool merely used, unload the model (`keep_alive: 0`); never kill a process
the tool didn't start.

Root cause per the operator-gated adversarial audit
(`audit/VERIFICATION-REPORT-ollama-lifecycle.md`): shutdown no-opped for default-config use
(`_engaged` set only by the Settings POST), and the engaged path's own kill ordering orphaned the
runner (parent terminated before the `/T` tree-walk) with every failure invisible. Closed by the
three-tier shutdown + durable marker + startup reconciliation (ADR-0315). Operator verification:
the four-scenario smoke script in the PR body; park artifacts #1/#3/#5 (+#4) remain open in the
audit's §8.

---

## How to work this queue

- Pick items up in a numbered round like any other tail work; record the ADR that closes each.
- An item here is **not** a licence to widen an in-flight round's scope — round 11 was mid-flight when
  these arrived and correctly did not absorb them.

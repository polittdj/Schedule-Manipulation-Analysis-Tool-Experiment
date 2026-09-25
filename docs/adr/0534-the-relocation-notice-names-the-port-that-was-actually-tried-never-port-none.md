# ADR-0534 — The relocation notice names the port that was actually tried: the console entry point printed "port None was busy" because the notice interpolated the caller's argument, not the port the launcher claimed

**Status:** Accepted · **Date:** 2026-09-25 · **Extends:** ADR-0412 (a launch never dead-ends: an unclaimable port relocates, and the move is announced) · **Closes:** the "launcher wart" carried in the kickoff's "also open" list since ADR-0412

## Context — the wart, measured before it was touched

The kickoff carried a two-part claim: ADR-0412's relocation notice is a `print()` the windowless
desktop icon never shows, and it prints "port None". Both parts were tested on the pristine
launcher (`src/schedule_forensics/launcher.py`) before any edit.

| Entry path | How it calls `main` | Pristine notice (probe with a claim that refuses the first port) |
| --- | --- | --- |
| console script `schedule-forensics` (`pyproject.toml` `[project.scripts]` → `launcher:main`) and `python -m schedule_forensics` (`__main__.main` → `_launch()`) | `main()` — no port, so the launcher picks an ephemeral one | "POLARIS² — port **None** was busy and would not release, so this session is on 42873 instead" — **the defect** |
| the desktop icon (all nine installers: `pythonw -c "…main(port=$AppPort)"`, `$AppPort = 8321`) | `main(port=8321)` | "port **8321** was busy …" — correct text, but written to the devnull sink `_ensure_streams` installs for `pythonw`, so the operator never sees it |

The mechanism is one line: the notice interpolated the `port` **argument**, which is `None` on the
console path, instead of the port the launcher actually tried to claim. It is reachable there
only when the claim on the ephemeral port fails (a lost race or a refused claim), so it is rare.
It is still false text, and it prints to the one path that has a console.

## Decision

1. **The notice names the port that was tried.** `main` records `tried_port = chosen_port` (the
   caller's port, or the ephemeral pick) *before* `resolve_port` relocates, and the notice prints
   `tried_port`. `resolve_port`, the claim order, the browser URL and ADR-0334's safety property
   (the contested port is never bound) are untouched.
2. **Pinned:** `tests/test_launcher_single_instance.py::test_the_relocation_notice_names_the_port_that_was_actually_tried`,
   parametrized on both entry paths. It asserts the notice names the first port claimed and the
   port relocated to, never contains "None", and names 8321 on the icon path, which is the
   true-positive twin that was already right.

## QC-3 — the plan's assumptions, attacked before the first edit

| # | Assumption | Attack | Verdict |
| --- | --- | --- | --- |
| L1 | "port None" is reachable at all | probe `main(port=None)` with a claim that refuses the first port | **held** — reproduced verbatim |
| L2 | the icon path is affected the same way | same probe with `port=8321`; read the nine installers' launch lines | **FELL as stated** — the icon's text was already correct (8321); its defect is visibility, not content |
| L3 | the notice is the only place the wrong port appears | read the launcher's two log lines on the same probe | **held** — both log lines already named the tried port (`port 52543 could not be claimed`, `serving on 42873 instead of 52543`) |
| L4 | capturing after `resolve_port` would also be correct | mutant: `tried_port` captured after the relocation | **refuted** — it names the NEW port as busy; both parametrized cases red |

## Verification

* **Red-first on the pristine launcher:** the console-entry case red by name with "port None was
  busy"; the icon twin green. 1 failed, 15 passed.
* **Green:** the module 16 / 16.
* **Mutant:** `tried_port` captured after `resolve_port`, so it names the relocated port as busy:
  both parametrized cases red by name; restored from a scratch copy and verified identical.

## Deliberately NOT done

* **The icon-path visibility.** Under `pythonw` both the notice and the log lines go to the
  devnull sink, so an operator whose launch relocated sees no word of it. The browser still
  opens on the live port (ADR-0412's pinned property), so nothing dead-ends. Making the move
  visible in the page is a UI decision — a banner, its wording and its placement under the
  design system — and is not taken here. It is recorded as open.
* No change to `resolve_port`, the claim protocol, or any installer's launch line.

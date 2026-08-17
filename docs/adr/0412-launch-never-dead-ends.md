# ADR-0412 — a launch never dead-ends: an unclaimable port relocates instead of refusing to start

**Status:** Accepted · **Date:** 2026-08-17 · **Supersedes (in part):** ADR-0334's *refuse*
outcome — its *safety property* is kept · **Severity:** high (availability of a testimony
tool) · **Version:** v1.0.209 → **v1.0.210** — wheel + nine installers rebuilt, lockstep 64/64.

## Context — a field report

> *"I don't like the fact that if the user accidentally closes the program without using the
> Quit function … it prevents the user from opening the program again. Make it so that no
> matter how the user closes the program there is no issue."* — operator, 2026-08-17, with a
> screenshot reading **"POLARIS is already running on port 8321."**

`claim_port` (ADR-0334) had two outcomes that ended the launch:

1. the holder does not answer `/api/whoami` — a **wedged or half-dead instance**, a process
   caught mid-shutdown, or an unrelated program → `PortUnavailable`;
2. a predecessor is asked to stand down and **never releases** → `PortUnavailable`.

Both messages advised quitting the other session *"from its own window"*. **There is no
window.** The desktop shortcut launches `pythonw.exe` — deliberately console-less — so the
advice is impossible to follow, and the operator's only remaining move is Task Manager. A
forensic tool that cannot be opened is worth nothing, whatever the reason.

## Decision

`resolve_port(host, preferred)` wraps the claim and **always returns a port to serve on**,
reporting `"free"`, `"handover"`, or `"relocated"`. On `PortUnavailable` it takes an ephemeral
free port (up to `_RELOCATE_ATTEMPTS`, skipping the contested one and retrying if it loses a
race) and serves there. `main()` computes the URL **after** resolution, so the browser always
opens on the port actually served, and prints a plain-language line when the address moved.

**ADR-0334's safety property is preserved, not traded away.** Its reasoning — never bind a
port another server may hold, because Windows permits the second bind and requests would then
route indeterminately between two servers — is *why we relocate rather than force the bind*.
The contested port is still never bound. What changes is only the outcome when it cannot be
had: serve elsewhere instead of not at all.

Relocation stays the exception. A claimable preferred port is used as-is (test-pinned), so
`8321`, the operator's bookmark, and every document that names it keep working. And when
*every* port fails to claim, `resolve_port` exhausts its retries and re-raises — the machine
genuinely cannot serve, and failing honestly is right. That is why ADR-0334's original
"stops the launch before any browser opens" test **still passes unchanged**.

## Verification (QC-1)

- **Red first:** `test_an_unclaimable_port_relocates_instead_of_refusing_to_start` and
  `test_resolve_port_reports_how_it_got_the_port` failed by name; both launcher modules are
  **28 passed** after, with no existing test repointed.
- **The safety assertion is in the same test as the availability one**: it asserts a port was
  served *and* that it was **not** the contested one — so a "fix" that simply forced the bind
  would fail the very test that proves the lockout is gone.
- **Mutation battery 4/4 caught by name** (PYTHONPATH shadow, import-origin canary, instrument
  md5-identical, controls green both sides): M1 no relocation (the reported lockout) · M2
  relocating onto the contested port (ADR-0334 broken) · M3 the URL/browser computed from the
  preferred rather than the served port · M4 a relocation mislabelled `"free"`.

## Scope — what this does NOT fix

The screenshot's exact wording, **"POLARIS is already running on port 8321."**, appears
**nowhere in this repository**, and its window is a console titled "POLARIS (ITAR AI)" while
the shipped shortcut runs `pythonw` with no console at all. It is a **local wrapper script on
the operator's machine**, not shipped code. That wrapper refuses *before* invoking Python, so
this fix cannot run on that path — the operator must launch via the installed "Schedule
Forensics" shortcut (or `Start-ScheduleForensics.cmd`) for it to apply.

Worth stating plainly: on the shipped path the reported symptom was **already** handled — a
live previous instance answers `/api/whoami` and is stood down (handover). What was genuinely
broken, and is fixed here, is every case where the holder cannot be stood down.

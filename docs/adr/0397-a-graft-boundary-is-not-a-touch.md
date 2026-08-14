# ADR-0397 — A graft boundary is not a touch: the MPXJ pin refuses shallow-clone artifacts

Status: accepted (2026-08-13). Closes **DoD 117** (the `mpxj_ref()` shallow-clone guard). Renumbered 0396→0397 at the #585 merge. Lands with
ADR-0396 in v1.0.201 because the defect fired *inside* that session's mandatory installer rebuild —
this is the fix for a wound taken while shipping 001b, not opportunistic scope.

## Context

`tools/installer/build_installers.py::mpxj_ref()` pins the vendored-converter download URL to "the
last commit that touched `tools/mpxj`" via `git log -1 --format=%H -- tools/mpxj`. **In a shallow
clone, git attributes the entire tree to the graft-boundary commit**, so that command returns
whatever commit the clone happened to be cut at. The kickoff recorded one firing (`79865bc` pinned
instead of `42d92dc`); this session produced the second: the v1.0.201 rebuild's first attempt
pinned **`a100184d`** — this container's own graft boundary (`.git/shallow` names it), whose
`--stat` even *showed* 28 files "added" under `tools/mpxj` that were in fact present at `42d92dc`
all along.

The diagnosis chain is worth recording because it reversed **twice** under measurement (QC-2):

| Step | Claim | Overturned by |
| --- | --- | --- |
| 1 | "my fresh pin `a100184d` is correct — it is the last touch and an ancestor of origin/main" | the committed installers disagreed (`42d92dc`), and this trap is *named* in the kickoff |
| 2 | "then the committed v1.0.198–200 installers are broken — they reference `poi-5.5.1.jar`, which `a100184d`'s stat says did not exist at `42d92dc`" | `git show 42d92dc:tools/mpxj/lib/poi-5.5.1.jar` returned the jar's bytes — the "addition" was a graft artifact |
| 3 | "so which pin is right is undecidable locally" | `git rev-parse <ref>:tools/mpxj` — all three trees (`42d92dc`, `a100184d`, `HEAD`) are **identical** (`2001032…`), and the GitHub commits API (`path=tools/mpxj`, full history) names **`42d92dc`** the true last touch |

Net: nothing in the wild was ever broken (identical trees mean every shipped pin serves the right
bytes), the committed pin was correct, and the *only* wrong artifact was this session's first
rebuild — which the 40-hex shape test (`test_the_converter_url_is_pinned_to_an_immutable_commit`)
passed happily, exactly as DoD 117 predicted it would.

## Decision

Two layers, both landed red-first:

1. **`mpxj_ref()` refuses a graft-boundary resolution.** If the resolved SHA appears in the
   clone's `$GIT_DIR/shallow`, the build exits with instructions instead of pinning an artifact.
   The escape hatch is **`SF_MPXJ_REF=<sha>`** — an operator-supplied true last-touch ref,
   accepted only after verifying `<sha>:tools/mpxj` is **tree-identical** to `HEAD:tools/mpxj`
   (the property the baked manifest actually depends on); a non-40-hex, unresolvable, or
   tree-divergent override is refused. All three refusal paths were exercised live: the
   boundary refusal fired on this container's real resolution, `SF_MPXJ_REF=main` and an
   unfetchable SHA were both rejected.
2. **`test_the_converter_pin_is_a_real_touch_not_a_shallow_graft_artifact`** (tests/installer)
   checks the *built artifacts*: the pinned ref must not be one of the building clone's boundary
   commits, and — where the ref's objects are locally dereferenceable — its `tools/mpxj` tree
   must equal the working tree's (environment-gated skip for a depth-1 clone that cannot
   dereference an old pin). Observed RED against the drifted build (3/3 families), GREEN after
   the `SF_MPXJ_REF=42d92dc…` rebuild.

The v1.0.201 installers ship pinned to `42d92dc` via the validated override.

## Consequences

- A shallow CI or container clone can no longer silently mint a wrong pin: the build refuses,
  and the test catches a drifted artifact even if the build tool is bypassed.
- The ancestry check the kickoff sketched ("refuse if the SHA is not an ancestor of origin/main")
  is **subsumed by a stronger one**: tree-identity is checkable in a shallow clone (ancestry often
  is not — `42d92dc`'s ancestry was literally unverifiable in this container) and is the property
  that makes an installer self-consistent.

## Deliberately NOT done

- **No network lookup in the build tool.** The GitHub commits API knows the true last touch, but
  the build must stay offline-deterministic; the operator passes the ref in, and the tool verifies
  the part that matters (bytes) locally.
- **The historic pins were not "corrected".** `42d92dc` remains correct; no retro-rebuild of
  released installers is needed (identical trees, above).

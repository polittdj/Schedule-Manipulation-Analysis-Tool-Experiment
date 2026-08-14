# ADR-0398 — The installers learn to fetch from a private repository

Status: accepted (2026-08-13). Fixes PR #586's `linux`/`windows` installer-smoke failures.
Extends ADR-0397 (the pin the fetch rides) and responds to the #585 audit's DISC-01 remediation.
`src/` untouched — v1.0.201 stands; the nine installers are regenerated from changed templates.

## Context

Between PR #580's green smoke run (04:58Z, 2026-08-13) and PR #586's red one (23:03Z, same day),
**the repository was flipped to private** — the operator's remediation for the #585 audit's
DISC-01 finding (sensitive gateway/model strings published in a public repo). Measured, not
inferred: the installers' anonymous `raw.githubusercontent.com` MPXJ fetch returns **404 at every
ref** — the pinned `42d92dc`, the PR head, and `main` — for a path tracked in git at all three;
the repos API reports `"visibility": "private"`; and the *identical* smoke legs passed hours
earlier. Nothing in the PR's diff touches the download path (the wheel-blob-excluded diff against
#580's installers is version strings plus the ADR-0397 pin correction).

So the failure is environmental and permanent-by-design: an anonymous fetch against a private
repository cannot work, for CI or for a real operator's one-file install. "Flip the repo public"
is not a fix — it would undo a deliberate security remediation.

## Decision

**The MPXJ download becomes token-aware, with the anonymous path kept as the public fallback.**

- Each installer now carries TWO transports for the same pinned commit: the historic anonymous
  raw URL, and the GitHub contents API
  (`https://api.github.com/repos/<owner>/<repo>/contents/tools/mpxj/<path>?ref=<pin>` with
  `Accept: application/vnd.github.raw+json` and `Authorization: Bearer <token>`). The API path is
  taken exactly when `SF_GITHUB_TOKEN` (an operator's token) or `GITHUB_TOKEN` (CI's built-in) is
  set; unset, behaviour is byte-for-byte the old anonymous fetch. The SHA-256 manifest check is
  unchanged and guards both transports — bytes are proven, not the transport.
- `installer-smoke.yml` passes `${{ github.token }}` to both jobs, so the smoke legs exercise the
  authenticated path — which is now also the *product's* supported one-file path for a private
  repo (the offline repo-ZIP fallback the installers already print remains for operators without
  a token).
- `tools/installer/build_installers.py` templates the API base and the pin (`{{MPXJ_API_BASE}}`,
  `{{MPXJ_REF}}`) from the same single `mpxj_ref()` resolution as the raw URL — one ref, two
  transports, incapable of disagreeing.

## Verification (QC-1)

- **Mechanism proven before shipping:** the contents-API raw fetch of the 3 MB `poi-5.5.1.jar` at
  the pinned ref returned bytes **SHA-256-identical** to the local manifest file.
- **Red:** a bare-directory smoke install of the rebuilt tier1 WITHOUT a token reproduces the CI
  failure exactly (404 → "MPXJ download failed" warn path).
- **Green:** the same install WITH a token fetched the **entire manifest through the API path,
  SHA-256-verified every file, and deployed the converter** (24 jars in `lib/`).
- **Pinned:** `test_the_converter_fetch_is_token_aware_for_the_private_repo` (9 parametrizations)
  requires both transports, both env names, the raw media type, and one shared immutable ref in
  every built installer — observed to FAIL by name under a targeted mutation of a built artifact
  and to pass after regeneration. `bash -n` parses all six shell installers; the installer suite
  is 64/64.
- CI's smoke legs are the final oracle for the Actions-token semantics; they now run the exact
  path a private-repo operator would.

## Deliberately NOT done

- **No token is ever embedded in an installer** — the token arrives via environment at run time
  or the fetch stays anonymous. A CUI tool's install artifact must not carry credentials.
- **No network lookup in the build tool** (unchanged from ADR-0397): the operator passes
  `SF_MPXJ_REF` in; the tool verifies tree-identity locally.
- **The release-asset alternative was not taken**: release assets inherit repository visibility,
  so they solve nothing a token does not, while adding a publish step that can drift from the
  tree. Embedding the 17 MB converter in each installer (≈23 MB × 9 per rebuild) was rejected as
  repo bloat with no integrity gain over the manifest check.
- **DISC-01's release determination stays open** — private visibility mitigates; the authorizing
  official decides history. This ADR neither adds new copies of the sensitive strings nor removes
  the existing ones.

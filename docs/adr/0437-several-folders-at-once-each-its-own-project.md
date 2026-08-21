# ADR-0437 — Several folders at once, each its own Project: the drop traverses directories, because the picker dialog cannot multi-select

**Status:** Accepted · **Date:** 2026-08-21 · **Extends:** ADR-0258 (grouped ingestion), ADR-0289 (bounded pre-read)

## Context

Operator ask (2026-08-21): *"I want the user to be able to select multiple folders at one time and
have the program group the files in each folder into a separate project."*

Measured baseline, each leg with an executable check before any code changed:

| Leg | Fact | Evidence |
| --- | --- | --- |
| Server grouping | ALREADY per-file: one POST whose `file_meta` rels span two top folders lands as two folder Projects | probe green on the unmodified tree; mutation (all rels one folder) red on the exact population assert |
| Folder picker dialog | CANNOT multi-select: `webkitdirectory` overrides `multiple` — Chromium's file-chooser modes are exclusive | WICG entries-api issue #24; MDN |
| Drag-and-drop | a dropped FOLDER never loaded at all: `dataTransfer.files` exposes the bare directory File, its byte read fails, and the operator was told the folder was *"online-only in OneDrive"* | browser probe on the pre-feature tree: dropping two fake folders + one loose file loaded keys `['loose']`, the folders skipped as "2 non-schedule" |

So the ask decomposes into: the server needs pinning, not fixing; the picker is a browser platform
limit; **the drop is the one mechanism that can deliver several folders at once, and it was broken
for folders entirely.**

## Decision

1. **`home.js` traverses dropped directories** (`dropEntries` + `walkEntries`): entries are
   captured **synchronously** inside the drop handler (the items list goes inert once the handler
   yields), then walked async — directories drain `readEntries` **until an empty batch** (Chrome
   returns at most 100 per call; the browser test's fake reader hands one per call to pin the
   loop), files materialize as `preread()`-shaped **File-likes** carrying
   `webkitRelativePath = "Folder/sub/file.ext"` rooted at the dropped folder's own name. A loose
   dropped file keeps `rel ''` (loose semantics unchanged); an entry whose File cannot
   materialize becomes a File-like whose read rejects, so the existing skip reporting names it.
   With no usable entries (a synthetic DataTransfer, an old engine) the handler falls back to
   `dataTransfer.files` byte-for-byte. `preread()` itself is untouched — the
   `PREREAD_CONCURRENCY → skipHint` harness extraction window is byte-stable, and the harness's
   own stubs are the proof File-likes are first-class inputs.
2. **The server changes nothing** — `_parse_upload_meta` already derives the top folder per FILE
   and `group_into_projects` buckets per distinct folder, so N dropped folders land as N Projects
   through the existing pipeline. That behavior is now **pinned**
   (`tests/web/test_multi_folder_ingestion.py`), including the loose-file-beside-folders case.
3. **The dashboard copy states the contract**: *each folder is its own Project*; to load several
   Projects at once, **drop** several folders at once — and, honestly, that the picker dialog
   selects one folder per pick.

Verification: `tests/web/test_multi_folder_drop_browser.py` drives the REAL `home.js` end to end
in chromium — a synthesized drop whose `DataTransferItem.webkitGetAsEntry` returns fake entry
trees (the one object a test cannot manufacture without an OS drag), through the real traversal,
pre-read, `fetch('/upload')` and grouping, asserted on the live `SessionState`. Observed red on
the pre-feature tree; mutation (recursion removed) red **by name** on the nested-file count.

## Consequences

- Dropping N folders — nested sub-folders and all — loads N Projects in one gesture; Mission
  Control/Portfolio see them exactly as N folder uploads.
- The misleading "online-only in OneDrive" report for a dropped folder is gone (that hint now
  fires only for genuinely unreadable files).
- A single dropped folder also finally works as a folder ingest (it previously loaded nothing).

## Deliberately NOT done

- **No picker-dialog workaround** (no `showDirectoryPicker` loop, no "add another folder" queue):
  the dialog's one-folder limit is the platform's, stated in the copy; the drop covers the
  multi-folder gesture. UNVERIFIED in this sandbox: whether any Chromium build honours
  `multiple` on the directory dialog — the input keeps the attribute, which is inert where
  unsupported and free where it ever isn't.
- **No server-side changes** — the grouping was already correct; changing it to "help" would have
  risked the ADR-0258 contract for zero behavior.
- **Traversal order is not canonicalized** (entry callbacks interleave): per-file `rel` + `mtime`
  carry the grouping and ordering signal, so arrival order is immaterial to the model.

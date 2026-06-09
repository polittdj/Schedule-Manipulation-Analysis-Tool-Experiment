# 00_REFERENCE_INTAKE — Deposit reference & golden files here (Gate 1)

This folder is the **only** place you put the reference materials the build needs.
Everything you drop here (except this file and `.gitkeep`) is **git-ignored** so it
can never be committed — see `.gitignore`. The build tool will read these files
**locally only**; nothing here ever leaves this machine.

> **STOP — read the CUI rule first.** Treat every schedule file and every export as
> **Controlled Unclassified Information (CUI) by default.** Before you place an item
> here, confirm it is **non-CUI or fully sanitized/synthesized** and that you are
> authorized to use it in this environment. **If this session is running in the
> cloud/web, do NOT deposit CUI** — run the build on a local, offline, authorized
> machine instead (see `AUTONOMOUS-BUILD-SETUP-CHECKLIST.md` §A). If any item's CUI
> status is unclear, **do not deposit it** — tell me and I will stop and ask before
> reading anything.

When everything below is in place and confirmed non-CUI, reply **`GO`** to start Phase 1.

---

## What to deposit (checklist)

Place each item directly in this folder (subfolders are fine). For every item,
confirm the **"non-CUI / sanitized"** box.

### 1. Power BI reference — `.pbix`  ☐ deposited  ☐ confirmed non-CUI/sanitized
- The `.pbix` you use today for schedule metrics/visuals.
- Why: I will extract the **extra metrics and how they're calculated** and the
  **example visuals**, and I'm encouraged to **expand/improve** on them.
- If the `.pbix` itself is sensitive, a sanitized export works too: the **DAX/measure
  definitions** (e.g. exported via Tabular Editor or copied measure text) and
  **screenshots** of the example visuals.

### 2. The two compared Microsoft Project schedules — `.mpp` ×2  ☐ deposited  ☐ confirmed
- The exact **two `.mpp` files** that were compared (the pair behind the golden
  Acumen/SSI numbers below). Native `.mpp` is fine — parsing native `.mpp` without
  conversion is a core requirement.
- Why: these are the **inputs** the parity suite runs on. Numbers I compute from
  these must match the golden exports exactly.
- Name them so the pairing is obvious, e.g. `projectX_v1.mpp` and `projectX_v2.mpp`.

### 3. Acumen Fuse v8.11.0 outputs (GOLDEN NUMBERS)  ☐ deposited  ☐ confirmed
- (a) The **comparison output** Acumen produced for the two `.mpp` files above.
- (b) The **raw per-file result exports** — one per `.mpp` — with the full metric
  values Acumen calculated.
- Format: whatever Acumen exports (`.xlsx`/`.csv`/PDF). These are the **exact target
  numbers** the parity suite must reproduce. Confirm the **version is v8.11.0**.

### 4. SSI MS Project add-on outputs (GOLDEN NUMBERS)  ☐ deposited  ☐ confirmed
- The **driving-path / driving-slack exports** for a **chosen target UniqueID**.
- Tell me, in `NOTES.md` (template below), **which UniqueID** was the endpoint/focus
  and from **which of the two `.mpp` files**, plus the **MS Project version** used.
- Why: I must reproduce SSI's **Driving Slack (in days) per task** along the driving
  logic path to that UniqueID, **exactly**.

### 5. Acumen Fuse **metrics library** (FORMULAS)  ☐ deposited  ☐ confirmed
- The metric/measure library with the **formula/definition for every metric** Acumen
  computes (the published metrics-library doc, an export, or screenshots).
- Why: I implement each metric to match, and write a plain-language **metric
  dictionary** (formula + citation) for the in-tool help.

### 6. Supporting references (optional but valuable)  ☐ deposited  ☐ confirmed
- **Data dictionaries** (field/UniqueID definitions, code mappings).
- **Sample reports** you want the output to resemble.
- **NASA UI / theme references** (colors, logos you're cleared to use, layout
  examples) for the dark-mode NASA-themed UI.
- The **DCMA 14-point** reference you consider authoritative (if you have a preferred
  one), so my audit matches your expectations.

---

## Add a short `NOTES.md` (helps me hit parity on the first try)

Create `00_REFERENCE_INTAKE/NOTES.md` (also git-ignored) answering:

1. Which two `.mpp` files form the compared pair? (filenames)
2. For SSI: target **UniqueID**, which `.mpp` it's in, and the **MS Project version**.
3. Acumen Fuse version (confirm **8.11.0**) and the **project/working calendar** and
   **status/data date** used, if known.
4. Any metric where you already know Acumen and SSI/MS Project **disagree**, so I treat
   it carefully.
5. Default **secondary / tertiary path day-thresholds** you want pre-filled at upload
   (you can change them per-upload in the tool).
6. Units/rounding expectations beyond the global rule (durations in **days**,
   percentages shown with a sign, e.g. `100%`).

---

## Naming & layout (suggested)

```
00_REFERENCE_INTAKE/
├─ DEPOSIT-HERE.md            ← this file (tracked)
├─ NOTES.md                   ← your answers (git-ignored)
├─ pbix/                      ← item 1
├─ mpp/                       ← item 2 (the two compared schedules)
├─ acumen_v8.11.0/            ← item 3 (comparison + per-file raw exports)
├─ ssi/                       ← item 4 (driving-path / driving-slack exports)
├─ metrics_library/           ← item 5 (formulas)
└─ references/                ← item 6 (data dictionaries, samples, theme)
```

---

## When you're done

1. Tick every **deposited** + **confirmed non-CUI/sanitized** box above for the items
   you're providing.
2. If you're **intentionally omitting** an item, note it in `NOTES.md` so I don't wait
   on it — but be aware parity for the affected area may be deferred or partial.
3. Reply **`GO`**.

I will then verify each file is present, readable, and confirmed non-CUI; if anything
is missing, ambiguous, or possibly CUI, I will list it and ask before reading it.

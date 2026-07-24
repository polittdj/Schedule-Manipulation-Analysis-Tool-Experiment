# CRISPNESS-PATCH — vendored type + an 11px floor

Applyable spec for PROMPT 1. Governing law: repo `CLAUDE.md` and `docs/DESIGN-SYSTEM.md` — tokens only, air-gap absolute, no engine change, no displayed number changed, nothing renamed, no features added.

**What I could not execute from here, and who must:** this workspace has no network egress, no Python runtime and no running app, so it cannot (1) download the font binaries, (2) run `pytest`/`ruff`/`mypy`/`bandit`/`pip-audit`, (3) build the wheel or regenerate the 9 installers, or (4) screenshot the 4 themes × 2 densities × 3 zoom levels. Everything else — the verification of the diagnosis, the licence verdicts, the `@font-face` block, the token ramp, and the complete line-exact patch list — is below and is ready to apply verbatim.

---

## 1. The diagnosis, verified against the real files

**(a) The type scale bottoms out at 8–9px — confirmed.** All px type declarations across `base.css`, `app.css`, `hud.css` (`font-size` **and** the `font:` shorthand): **197 declarations**, distributed 8px ×3 · 9px ×10 · 10px ×15 · 11px ×42 · 12px ×66 · 12.5px ×1 · 13px ×25 · 14px ×11 · 15px ×5 · 16px ×9 · 17px ×1 · 18px ×2 · 19px ×1 · 20px ×1 · 22px ×3 · 26px ×1 · 34px ×1. **28 of them are below 11px** (3 × 8px, 10 × 9px, 15 × 10px) — full list in §5.

**Worse, and not in the original diagnosis: the charts are the main offender, and they bypass CSS entirely.** The SVG/DOM chart modules set type as an *attribute or inline style in JavaScript*: **40 sub-11px sizes across 12 modules** (§6). Those are the axis ticks and bar labels — exactly the text that reads as "fussy" — and because they are not CSS they will survive any change to the stylesheets and they violate DESIGN-SYSTEM Law 1 (nothing styles itself) today.

**(b) No `@font-face` exists and the designed typography has never rendered — confirmed, and it is worse than "not vendored".** `@font-face` blocks in all three stylesheets: **0**. `url(...)` references: **0**. Font binaries in the repo (`.woff`/`.woff2`/`.ttf`/`.otf`): **0 files**. Grepping the stylesheets for the three faces DESIGN-SYSTEM §1 specifies: **"Barlow" 0 hits · "Barlow Semi Condensed" 0 hits · "IBM Plex Mono" appears only as a name inside `ui-monospace,"IBM Plex Mono",Consolas,monospace`**. The UI face is not a designed font at all — `base.css` sets `font:11px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif`, i.e. the OS system stack, and everything else inherits.

---

## 2. Three conflicts to settle before this is applied

1. **`sf-themes.css` does not exist in the repo.** PROMPT 1 §3 says all sizes come from custom properties in `sf-themes.css`; the audit found the token layer lives in **`base.css`** (`:root` + `[data-theme=console|apollo|jarvis]` blocks) and `sf-themes.css` was never committed. **Recommendation:** put the ramp in `base.css` beside the existing tokens — one token layer, no import-order risk — and update DESIGN-SYSTEM to name `base.css` as the token file. If you want the separate file, create it and `@import` it first from `base.css`; do not split the ramp across both.
2. **The 40 chart sizes are JS attributes, not CSS**, so "all sizes come from custom properties" cannot be met by editing stylesheets. The fix that satisfies Law 1: delete the numeric `font-size` attribute/inline style at each site, give the element the semantic class it already deserves (`.ch-xl`, `.ch-yl`, `.g-tick`, `.g-barlabel`, …), and let CSS set `font-size: var(--sf-fs-label)`. Several of those classes already exist (`app.css:349`, `app.css:824`) — they are simply not used everywhere.
3. **Density.** Raising the floor costs vertical space. Do **not** buy it back by shrinking type in the compact density; buy it back in padding/line-height only. Compact must remain a *spacing* mode, per DESIGN-SYSTEM §7.

---

## 3. Fonts — licences verified, then vendored

| Face | Licence | Redistributable in-repo? | Upstream |
|---|---|---|---|
| **Barlow** (400/500/600/700) | SIL Open Font License 1.1 | **Yes** — OFL explicitly permits bundling and redistribution, with or without modification | `github.com/jpt/barlow` (also on Google Fonts) |
| **Barlow Semi Condensed** (600/700) | SIL Open Font License 1.1 | **Yes** — same family/licence | `github.com/jpt/barlow` |
| **IBM Plex Mono** (400/600) | SIL Open Font License 1.1 | **Yes** — IBM released the whole Plex family under OFL 1.1 | `github.com/IBM/plex` |

No substitution is needed: all three intended faces are OFL 1.1, so nothing in this change requires shipping something we cannot legally vendor.

**One OFL caveat, and how to stay clean:** OFL 1.1 forbids using a Reserved Font Name on a *modified* version. Format conversion and subsetting are technically modifications. Ship the **unmodified upstream woff2 builds** and keep the family names — that is unambiguously compliant. Only subset if the payload actually hurts, and then rename per OFL §3 (e.g. `SF Mono Deck`) rather than shipping "IBM Plex Mono" altered.

**Vendor to** `src/schedule_forensics/web/static/fonts/` — 8 files, all woff2, all committed:

```
barlow-400.woff2  barlow-500.woff2  barlow-600.woff2  barlow-700.woff2
barlow-semicondensed-600.woff2  barlow-semicondensed-700.woff2
ibm-plex-mono-400.woff2  ibm-plex-mono-600.woff2
```

**`@font-face` block — add at the very top of `base.css`, above the token blocks:**

```css
/* Vendored locally (SIL OFL 1.1) — no CDN, no network. Air-gap law, CLAUDE.md §4. */
@font-face{font-family:Barlow;src:url("/static/fonts/barlow-400.woff2")format("woff2");font-weight:400;font-style:normal;font-display:block}
@font-face{font-family:Barlow;src:url("/static/fonts/barlow-500.woff2")format("woff2");font-weight:500;font-style:normal;font-display:block}
@font-face{font-family:Barlow;src:url("/static/fonts/barlow-600.woff2")format("woff2");font-weight:600;font-style:normal;font-display:block}
@font-face{font-family:Barlow;src:url("/static/fonts/barlow-700.woff2")format("woff2");font-weight:700;font-style:normal;font-display:block}
@font-face{font-family:"Barlow Semi Condensed";src:url("/static/fonts/barlow-semicondensed-600.woff2")format("woff2");font-weight:600;font-style:normal;font-display:block}
@font-face{font-family:"Barlow Semi Condensed";src:url("/static/fonts/barlow-semicondensed-700.woff2")format("woff2");font-weight:700;font-style:normal;font-display:block}
@font-face{font-family:"IBM Plex Mono";src:url("/static/fonts/ibm-plex-mono-400.woff2")format("woff2");font-weight:400;font-style:normal;font-display:block}
@font-face{font-family:"IBM Plex Mono";src:url("/static/fonts/ibm-plex-mono-600.woff2")format("woff2");font-weight:600;font-style:normal;font-display:block}

:root{
  --sf-font-ui:Barlow,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --sf-font-display:"Barlow Semi Condensed",Barlow,-apple-system,"Segoe UI",sans-serif;
  --sf-font-mono:"IBM Plex Mono",ui-monospace,Consolas,monospace;
}
```

`font-display:block` (not `swap`) is deliberate: a local file loads in single-digit milliseconds, and `block` prevents the system-stack flash that would make a dense table reflow on every page load.

**Air-gap:** these are same-origin `/static/` URLs, so `tests/web/test_airgap.py` stays green. Add one assertion to it while you are there: every `url(...)` in the shipped CSS must start with `/static/`. Also confirm the wheel picks the new directory up — `tests/installer/test_installers.py:68` already asserts **≥30** `/web/static/` entries; 8 font files raise the count, they do not break it, but check `pyproject.toml` package-data globs include `web/static/fonts/*.woff2`.

---

## 4. The type ramp (rescaled whole, not patched at the offenders)

```css
:root{
  /* Type ramp — single source of truth. 11px floor, no exceptions. */
  --sf-fs-label:11px;  --sf-fs-micro:12px; --sf-fs-sm:13px;   --sf-fs-base:14px;
  --sf-fs-md:15px;     --sf-fs-lg:16px;    --sf-fs-xl:18px;   --sf-fs-2xl:20px;
  --sf-fs-3xl:24px;    --sf-fs-4xl:30px;   --sf-fs-5xl:38px;
  --sf-lh-tight:1.2;   --sf-lh-data:1.35;  --sf-lh-body:1.5;
}
```

| was | becomes | role |
|---|---|---|
| 8px | `--sf-fs-label` → 11px | mono tick / micro-label |
| 9px | `--sf-fs-label` → 11px | mono tick / micro-label |
| 10px | `--sf-fs-micro` → 12px | kickers, chips, nav beats, table heads |
| 11px | `--sf-fs-sm` → 13px | compact body (old base) |
| 12px / 12.5px | `--sf-fs-base` → 14px | UI + body default |
| 13px | `--sf-fs-md` → 15px | emphasised body |
| 14px / 15px | `--sf-fs-lg` → 16px | panel h2, lead-in |
| 16px / 17px | `--sf-fs-xl` → 18px | section heads |
| 18px / 19px / 20px | `--sf-fs-2xl` → 20px | page h1 (unchanged at the top end) |
| 22px | `--sf-fs-3xl` → 24px | takeaway h1 |
| 26px | `--sf-fs-4xl` → 30px | hero metric |
| 34px | `--sf-fs-5xl` → 38px | hero metric large |

**Why 8px and 9px collapse into one token rather than becoming two sizes:** the audit shows 8px appearing 3 times and 9px 10 times, spread across three files and three unrelated component families (SSI chart labels, nav section labels, stack feet). That is drift, not a semantic level — there is no page where an 8px label and a 9px label are meant to read as different ranks. Collapsing them into `--sf-fs-label` removes a distinction that was never intentional, and the ramp still has eleven distinct steps.

**Hierarchy check:** every adjacent pair in the new ramp keeps a ≥1px / ≥7% step, and the top end moves least (34→38, 22→24) so headline-to-body contrast *increases* slightly rather than flattening. The 90–125% UI-scale control multiplies the base as it does today; at 90% the floor renders 9.9px, so if that is unacceptable, clamp the scale control's lower bound to 100% for `--sf-fs-label` with `font-size:max(11px, calc(var(--sf-fs-label) * var(--sf-ui-scale)))`.

---

## 5. Patch list A — the 28 sub-11px CSS rules

| site | now | replace with | rule |
|---|---|---|---|
| `base.css:292` | 9px | `var(--sf-fs-label)` (11px) | `.rk-cell-s{position:absolute;right:4px;bottom:2px;font-size:9px;opacity:.7}` |
| `base.css:316` | 9px | `var(--sf-fs-label)` (11px) | `.nav-sect-label{font-size:9px;font-weight:700;letter-spacing:.16em;text-transform:up` |
| `base.css:320` | 9px | `var(--sf-fs-label)` (11px) | `.nav-chapter .ch-num{font-size:9px;font-weight:700;color:var(--header-line);letter-s` |
| `base.css:324` | 10px | `var(--sf-fs-micro)` (12px) | `.nav-beats a{font-size:10px;font-weight:500;color:var(--header-muted);white-space:no` |
| `base.css:409` | 10px | `var(--sf-fs-micro)` (12px) | `.chapter-kicker{font-size:10px;font-weight:700;letter-spacing:.16em;text-transform:u` |
| `base.css:414` | 9px | `var(--sf-fs-label)` (11px) | `.story-so-far{font-size:9px;font-weight:700;letter-spacing:.16em;text-transform:uppe` |
| `base.css:450` | 9px | `var(--sf-fs-label)` (11px) | `.stack-foot{font-size:9px;font-weight:700;letter-spacing:.14em;text-transform:upperc` |
| `base.css:462` | 10px | `var(--sf-fs-micro)` (12px) | `.concl-topic{font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppe` |
| `base.css:475` | 10px | `var(--sf-fs-micro)` (12px) | `.wb-family-head .linkbtn{font-size:10px}` |
| `base.css:486` | 10px | `var(--sf-fs-micro)` (12px) | `font-size:10px;letter-spacing:.1em;font-weight:700}` |
| `app.css:60` | 10px | `var(--sf-fs-micro)` (12px) | `.g-tick { position: absolute; bottom: 2px; transform: translateX(-50%); font-size: 1` |
| `app.css:95` | 9px | `var(--sf-fs-label)` (11px) | `.g-barlabel { position: absolute; top: 1px; font-size: 9px; line-height: 14px; color` |
| `app.css:155` | 9px | `var(--sf-fs-label)` (11px) | `.pv-tick-label { position: absolute; top: 1px; font-size: 9px; color: var(--muted); ` |
| `app.css:167` | 10px | `var(--sf-fs-micro)` (12px) | `box-sizing: border-box; text-align: center; white-space: nowrap; font-size: 10px;` |
| `app.css:339` | 10px | `var(--sf-fs-micro)` (12px) | `.ut-badge { display: inline-block; font-weight: 700; font-size: 10px; text-transform` |
| `app.css:349` | 9px | `var(--sf-fs-label)` (11px) | `.res-svg .res-yl, .res-svg .res-xl { font-size: 9px; fill: #5a6878; }` |
| `app.css:469` | 10px | `var(--sf-fs-micro)` (12px) | `.ev-badge { background: var(--warn); color: #000; border-radius: 3px; padding: 0 4px` |
| `app.css:765` | 10px | `var(--sf-fs-micro)` (12px) | `.nm-chead { font-size: 10px; text-align: center; padding: 1px 2px; vertical-align: b` |
| `app.css:767` | 9px | `var(--sf-fs-label)` (11px) | `.nm-clab { font-size: 9px; color: var(--muted); max-width: 64px; }` |
| `app.css:770` | 9px | `var(--sf-fs-label)` (11px) | `.nm-rlab { font-size: 9px; color: var(--muted); }` |
| `app.css:777` | 10px | `var(--sf-fs-micro)` (12px) | `border-radius: 8px; background: #10202e; color: #fff; font-size: 10px; font-weight: ` |
| `app.css:789` | 10px | `var(--sf-fs-micro)` (12px) | `.nm-leg-item { font-size: 10px; color: var(--ink); display: inline-flex; align-items` |
| `app.css:814` | 10px | `var(--sf-fs-micro)` (12px) | `.ssi-chart-t { font-size: 10px; font-weight: 700; color: var(--ink); margin-bottom: ` |
| `app.css:824` | 8px | `var(--sf-fs-label)` (11px) | `.ssi-svg .ch-yl, .ssi-svg .ch-xl { font-size: 8px; fill: #5a6878; }` |
| `app.css:832` | 8px | `var(--sf-fs-label)` (11px) | `.ssi-svg .ch-ql { font-size: 8px; font-weight: 700; fill: #5a6878; }` |
| `app.css:998` | 8px | `var(--sf-fs-label)` (11px) | `.brand-sub { font-size: 8px; font-weight: 600; letter-spacing: .24em; text-transform` |
| `hud.css:44` | 10px | `var(--sf-fs-micro)` (12px) | `margin-left:5px;border-radius:50%;font-size:10px;font-weight:700;cursor:help;` |
| `hud.css:145` | 10px | `var(--sf-fs-micro)` (12px) | `html[data-theme=jarvis] table th{color:var(--warn);text-transform:uppercase;font-siz` |

Then sweep the remaining 169 px declarations onto the ramp using the §4 mapping (they are not floor violations, but Law 1 requires them to be tokens): `grep -n "font-size:\s*[0-9]" src/schedule_forensics/web/static/*.css` must return **zero** raw px values when you are done, and `base.css`'s `font:11px/1.5 …` shorthand becomes `font:var(--sf-fs-base)/var(--sf-lh-body) var(--sf-font-ui)`.

---

## 6. Patch list B — the 40 sub-11px chart type sizes set from JavaScript

These are the ones that actually make the charts look fussy. Replace each numeric size with a class on the element and let CSS carry the token.

| module | count | sites |
|---|---|---|
| `cei.js` | 6 | 10px@L90, 9px@L123, 10px@L135, 10px@L146, 10px@L157, 9px@L180 |
| `curves.js` | 2 | 10px@L295, 10px@L309 |
| `drift.js` | 2 | 10px@L71, 10px@L83 |
| `histogram.js` | 1 | 10px@L184 |
| `margin.js` | 3 | 10px@L164, 10px@L169, 10px@L179 |
| `scatter.js` | 3 | 10px@L79, 10px@L87, 10px@L95 |
| `scurve.js` | 3 | 10px@L87, 10px@L98, 9px@L131 |
| `sra.js` | 4 | 10px@L66, 10px@L77, 10px@L167, 10px@L188 |
| `timeaxis.js` | 1 | 10px@L89 |
| `trend.js` | 10 | 10px@L375, 10px@L461, 10px@L506, 9px@L579, 10px@L588, 10px@L626, 9px@L687, 10px@L697, 9px@L775, 10px@L785 |
| `trend_drill.js` | 1 | 10px@L65 |
| `wbs.js` | 4 | 10px@L56, 10px@L63, 10px@L71, 10px@L91 |

Full occurrence census across the 37 chart modules: **9px ×6 · 10px ×34 · 11px ×19 · 12px ×4 · 16px ×3 · 18px ×1**. Note there is no size above 18px anywhere in the chart layer — every chart label in the product is between 9 and 18px today.

Recommended class vocabulary (reuse what exists in `app.css`, add the rest in one block): `.ch-xl` / `.ch-yl` axis tick labels · `.ch-at` / `.ch-atv` axis **titles** · `.ch-ql` quartile/annotation · `.g-tick` / `.g-barlabel` bar labels · `.ch-legend` legend text. All get `font-family:var(--sf-font-mono)` and `font-size:var(--sf-fs-label)`, with `font-variant-numeric:tabular-nums` on every one that renders a number.

While you are in these 12 modules: `docs/UI-INVENTORY.md` §2 flags that titled X/Y axes are not universal. Adding the `.ch-at` class here is the natural moment to give every one of them an axis title — but that is a **separate PR** under PROMPT 2, not this one. Do not mix it in.

---

## 7. Verification matrix (4 themes × 2 densities × 3 zooms)

Themes `console` · `daylight` · `apollo` · `jarvis` (`html[data-theme=…]`, set from the header View dropdown; `theme.js` persists `sf-theme`). Densities comfortable · compact. Browser zoom 90% · 100% · 125%.

Screenshot before/after, same window size, for at least: `/mission` · `/trend` · `/analysis/<key>` (Gantt + float histogram) · `/sra` (the 8px SSI labels live here) · `/margin`. That is 5 pages × 4 themes × 2 densities × 3 zooms = **120 captures**; the honest minimum is 5 pages × 4 themes at 100%/comfortable (20) plus `/trend` and `/sra` at all 3 zooms in both densities (12).

Specific things to look at, because they are where this change can go wrong:
- `/sra` SSI chart labels (`app.css:824`, `:832`) — 8px → 11px in a fixed-width grid; check nothing clips.
- `/trend` — 10 of the 40 JS sites are in `trend.js`; check tick collision at 90% zoom after the rescale, and thin ticks if they now overlap (that is a **spacing** fix, never a size fix).
- `apollo` theme forces mono + uppercase; uppercase at 11px is wider — check the nav section labels (`base.css:316`) and stack feet (`:450`).
- `jarvis` `table th` (`hud.css:145`) at 10px → 12px, and the help-dot (`hud.css:44`).
- Print/export: CUI bars must still fit their bar height with the larger type.

---

## 8. Definition of done

```bash
ruff check . && ruff format --check . && mypy
pytest --cov=schedule_forensics --cov-report=term-missing --cov-fail-under=70
coverage report --include='*/schedule_forensics/engine/*' --fail-under=85
pytest -m parity -p no:cacheprovider
bandit -q -r src && pip-audit --progress-spinner=off
pytest tests/web/test_airgap.py tests/web/test_dashboard_perf_contract.py -q
python -m build --wheel --outdir dist/wheel
python tools/installer/build_installers.py dist/wheel/schedule_forensics-*.whl
pytest tests/installer/test_installers.py -q
```

- [ ] Full suite green; ruff / ruff format / mypy (strict) / bandit / pip-audit clean.
- [ ] The three dashboard goldens **unchanged** — `_SHA_TWO_VERSION` `d62a4f9e…58d1`, `_SHA_UNSOLVABLE` `8d7bcc38…fc16`, `_SHA_TWO_VERSION_PARITY` `51691cb7…504cb`. A styling change that moves one of these means a payload was touched — revert and find out why.
- [ ] `grep -rn "font-size:\s*[0-9]" src/schedule_forensics/web/static/*.css` → empty; `grep -rn "font-size" src/…/static/*.js` → no numeric literals.
- [ ] No text below 11px in any theme, density or zoom ≥100%.
- [ ] 8 woff2 files committed under `web/static/fonts/`; `pyproject.toml` package-data includes them; wheel + 9 installers regenerated **in the same commit** (lockstep test 120 is what catches you otherwise); version bumped in `pyproject.toml`.
- [ ] `docs/DESIGN-SYSTEM.md` §1 updated — replace "Type (vendor locally for air-gap — NOT yet done; system stacks in use)" with:

> **Type (vendored locally, air-gap clean).** Barlow 400/500/600/700 · Barlow Semi Condensed 600/700 · IBM Plex Mono 400/600, all SIL OFL 1.1, shipped as unmodified woff2 under `web/static/fonts/` and declared with `@font-face` in `base.css`. Families come from `--sf-font-ui` / `--sf-font-display` / `--sf-font-mono`; sizes come from the `--sf-fs-*` ramp (`label` 11 · `micro` 12 · `sm` 13 · `base` 14 · `md` 15 · `lg` 16 · `xl` 18 · `2xl` 20 · `3xl` 24 · `4xl` 30 · `5xl` 38). **Floor is 11px everywhere, including chart labels drawn from JavaScript** — the former 8px mono-label exception is withdrawn. A raw px size in CSS or a numeric `font-size` in a chart module is a build failure.

- [ ] Nothing renamed, no feature added, `engine/` untouched, no displayed number changed.

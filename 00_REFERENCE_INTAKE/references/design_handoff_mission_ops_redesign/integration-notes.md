# Redesign handoff — theme system

**Contents:** `sf-themes.css` (drop-in tokens) · `DESIGN-GUIDE.md` (the rulebook —
copy to `docs/DESIGN-SYSTEM.md` and reference it in your build prompt so every
future session respects the theme).

**What this is:** token-level restyle for the real app. No calculation, route,
or template logic changes. The interactive prototype (`Mission Ops Redesign.dc.html`)
is the visual reference; this folder is the code you can drop into the repo.

## 1. Add the stylesheet
Copy `sf-themes.css` into `src/schedule_forensics/web/static/` and link it
**after** `base.css` / `hud.css` (it only overrides custom properties, plus a
few Apollo chrome rules).

## 2. Replace the dark/light toggle with a View dropdown (keep the toggle too if you like)
```html
<label class="ui-scale-ctl">View
  <select id="themeSelect">
    <option value="console">CONSOLE — mission control</option>
    <option value="daylight">DAYLIGHT — clean light</option>
    <option value="apollo">APOLLO — retro CRT</option>
    <option value="jarvis">JARVIS — HUD</option>
  </select>
</label>
```
```js
// theme-select.js — same localStorage key style as the existing toggle
(function(){
  var sel=document.getElementById('themeSelect'); if(!sel) return;
  var cur=localStorage.getItem('sf-theme')||'console';
  document.documentElement.setAttribute('data-theme',cur); sel.value=cur;
  sel.addEventListener('change',function(){
    localStorage.setItem('sf-theme',sel.value);
    document.documentElement.setAttribute('data-theme',sel.value);
  });
  // dark/light toggle interop: map "light" -> daylight, anything else -> last dark view
})();
```
Migration: treat existing `data-theme=light` as `daylight`; default/absent as `console`.

## 3. Branding
The redesign drops the "NASA" wordmark: keep the wireframe globe (it doubles as
the AI status light) and retitle the header **SCHEDULE FORENSICS · Manipulation
Analysis Console**. Keep the blue command-banner gradient + red keel line — in
`daylight` the header goes white with `#0B3D91` ink and the same red keel.

## 4. Fonts (optional, vendor locally for air-gap)
- UI: **Barlow** (400/600/700) · Headings: **Barlow Semi Condensed** (700)
- Data/mono: **IBM Plex Mono** (400/600/700)
Fallback stacks already work with system fonts.

## 5. What the prototype demonstrates beyond tokens
Story-driven nav (three acts / twelve chapters 01–12 with per-chapter takeaways +
"Continue" segues; utilities in a Setup group off the spine), a consistent chart
contract (takeaway headline · labeled X/Y axes with values · legend · hover callout ·
`SOURCE: file · DD` provenance chip · dotted reading grid · labeled DD line · same series
colors everywhere), time-granularity chips where data supports them, the full SRA page
(editable SSI grid with MS-Project column-paste + auto-calc BC/WC, Monte-Carlo outputs,
5×5 matrices, OAT — all Excel-exportable), and per-view nav patterns (left rail for dark
views, top bar for daylight). Those are template-level changes to app.py page shells — do
them screen by screen using the prototype as the spec; the calculations feeding each panel
stay exactly as they are.

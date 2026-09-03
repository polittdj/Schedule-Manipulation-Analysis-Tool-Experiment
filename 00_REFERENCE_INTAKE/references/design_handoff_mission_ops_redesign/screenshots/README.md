# Reference screenshots

Viewport captures (909×540) of `Mission Ops Redesign.dc.html`. For anything a
screenshot leaves ambiguous, open the prototype — it is the pixel truth.

## Naming
`NN-<theme>.png` — theme ∈ console · daylight (full sets, top + scrolled) ·
apollo · jarvis (top views).

**Console & Daylight (18 each):** odd = top of screen, even = scrolled to bottom.
- 01/02 Import · 03/04 Mission Control · 05/06 Ch 01 Where we stand ·
  07/08 Ch 02 What drives the date · 09/10 Ch 03 How it moved ·
  11/12 Ch 04 Work piling up · 13/14 Ch 05 Where it lands ·
  15/16 Ch 06 What changed · 17/18 Ch 07 The briefing

**Apollo & JARVIS (9 each, top views):**
- 01 Import · 02 Mission Control · 03 Ch 01 · 04 Ch 02 · 05 Ch 03 · 06 Ch 04 ·
  07 Ch 05 · 08 Ch 06 · 09 Ch 07

## Known capture artifacts (not design intent)
- The header **View** select can display a stale label ("CONSOLE — …") in
  non-console shots — an artifact of scripted capture; implement it as a normal
  controlled select showing the active theme.
- **Text** scale may read 90% in some shots; specs assume 100% (11px base).
- Scrollbars visible in captures are the capture viewport's, not styled chrome.

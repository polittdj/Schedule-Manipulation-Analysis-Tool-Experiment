# LODESTAR — One-Pager Studio

**Created by David Politte.** Questions or issues: [david.j.politte@nasa.gov](mailto:david.j.politte@nasa.gov)

LODESTAR turns a plain Excel list into a one-slide swimlane timeline — and a PowerPoint of the same
slide, built from native, editable shapes. It has two pages:

* **Timeline** — one list becomes one slide: a tinted band per swimlane, a bar per activity, a
  diamond per milestone, each labelled with its name and finish date, a check beside what is
  complete, a month/year header and a red line at the **data date** — your computer's date unless
  you set one with the **data date** control above the slide (one setting for both pages; the
  slide's caption and legend follow it, and the subtitle says both the data date and the day the
  slide was prepared when they differ). Drag its slider and the red line walks across the slide as
  you go; let go and the date is set. **Computer's date** puts it back.
* **Compare** — two lists (a PRIOR and a CURRENT) on one slide: what slipped, what pulled in, what
  is new and what was removed, every move in calendar days. **Swap prior and current** trades the
  two lists over.

On either page you can draw **logic links**: click an item on the slide and then another (first
the predecessor, then the successor), drag one item onto another, or pick the two in the **From**
and **To** lists beside the slide; choose the type (Finish-to-Start by default, or Start-to-Start,
Finish-to-Finish, Start-to-Finish) and add the link. Add as many pairs as you need (up to 200).
Only the links you add are drawn — on the page and in the PowerPoint export.

The slide always fills the page: a short list gets large bars and text, a long one smaller, and it
is never split onto a second slide. Every link takes the shortest square-cornered route from the
predecessor to the successor and is drawn **behind** the bars, diamonds and names it passes — so
every item stays readable — with its arrowhead and type tag drawn on top. Adding a link never
moves an item.

### Working in the studio

Every change redraws the slide at once — no page reload.

* **Undo / Redo** at the top (or Ctrl+Z / Ctrl+Shift+Z — ⌘ on a Mac) step back and forward through
  your last 60 changes; the **session log** in the side panel names each one.
* **Ctrl+K** (⌘K) opens the command palette: load a list, load the example, go to a page, export,
  print, show all dates, go back to the computer's date, switch the marking, change the view —
  type a few letters and press Enter.
* **Tour** walks you through the studio in seven steps; **Show me** plays a short demonstration
  (drawing a link, dragging to link, moving the data date, narrowing the dates, comparing two
  lists) on a copy of your list — or on the example list when none is loaded — and changes
  nothing.
* **Load the example list** (or the example pair on Compare) to try it before you have a list.
* Above the slide: **DATA** shows the list the slide was drawn from, **Excel** downloads it, and
  the full-screen button shows the slide on its own.
* **Print** prints the slide alone, with its marking — choose *Save as PDF* in the print dialog
  for a PDF.
* The view menu at the top switches between four views — **Dark**, **Bright**, **High contrast**
  and **Console**; the browser remembers your choice.

With scripting switched off in the browser the studio still works as plain forms — load, title,
dates, data date, links, swap, undo/redo, marking and the exports — and the page reloads after
each one; the palette, the tour, the demonstrations, dragging and the slider need scripting.

## What you need

**Python 3.10 or newer** — nothing else, and no internet. If the computer does not have it, install
it from python.org (on Windows the per-user install needs no administrator rights).

## Start it

Keep all the files of this folder together.

* **Windows** — double-click **`LODESTAR.bat`** (or double-click `LODESTAR.pyz` itself if Python is
  set up to open `.pyz` files).
* **macOS** — double-click **`LODESTAR.command`**. The first time, macOS may refuse to open a file
  from another computer: right-click it and choose *Open*, or, where that is not offered, allow it
  under System Settings → Privacy & Security.
* **Linux** — run `sh lodestar.sh` (or `python3 LODESTAR.pyz`).

A small window opens and your browser shows LODESTAR's launch page — take a star fix (it ends on
a welcome panel that opens either page), or skip straight to the studio (tick *Go straight to the
studio next time* and it will). **Leave the small
window open while you work.** To stop, press **Quit** on the page, or close the window.

### The Desktop shortcut

The first time it runs, LODESTAR puts a shortcut named **LODESTAR**, with its own ✦ icon, on your
Desktop — double-click it to start LODESTAR from then on. It is written once: delete it and it stays
deleted (start LODESTAR with `--shortcut` to make it again; `--no-shortcut` never makes one). It
carries nothing but the path to `LODESTAR.pyz` and the Python that made it, so keep the folder where
it is (move it and make the shortcut again). On Windows it is a `.lnk` that runs the Python launcher
`py` where there is one; on macOS a `LODESTAR.app` that opens with no window of its own — stop it
with **Quit** on the page; on Linux a `LODESTAR.desktop` entry (a desktop that asks you to *allow
launching* the first time is being careful, not broken). The icon and a one-line record live in
LODESTAR's own folder under your user profile (`%LOCALAPPDATA%\LODESTAR`, `~/Library/Application
Support/LODESTAR`, `~/.local/share/lodestar`), never beside the archive.

## The Excel list

One sheet, one row per item:

| Column | Holds |
| --- | --- |
| **A** | the swimlane name |
| **B** | the task or milestone name |
| **C** | the **start** date |
| **D** | the **finish** date |
| **E** | complete — a status word: Complete, Completed, Done, Finished, Closed, Yes, X, TRUE, a check mark (✓ ✔ ☑ ✅) or 100% stored as text draws a check. A number is not read as complete (Excel keeps a typed 100% as the number 1); the page names that cell |

A row whose start and finish are the same day — or that has only one date — is a **milestone**
(except a lone month such as Jan 2027, drawn across the whole month); any other row is an
**activity**. Blank rows between swimlanes are fine. Each page
offers **Download the template**. Workbooks in the older layout (C one date or a range such as
`04/20/2027 - 06/20/2027`, D the status) are still read, and the page says which layout it read.

## Your data stays on this computer

LODESTAR runs entirely on your own computer. It serves its pages only to this computer's own browser
(address `127.0.0.1`), it never connects to the internet, and it has **no AI** of any kind. The
lists you load live only in memory while LODESTAR runs; they are gone when it stops. The pages and
every PowerPoint carry the CUI marking by default — switch it with the button at the top when your
list is not CUI. The Excel downloads always keep the CUI marking.

---

LODESTAR is built from the same modules as the One-Pager pages of POLARIS², so both draw the same
slide from the same list. Its fonts (IBM Plex Sans and Mono, Space Grotesk) and icons (Lucide) are
carried inside the program under their own open licences — nothing is fetched. Version 2.0.0.

# LODESTAR — One-Pager Studio

**Created by David Politte.** Questions or issues: [david.j.politte@nasa.gov](mailto:david.j.politte@nasa.gov)

LODESTAR turns a plain Excel list into a one-slide swimlane timeline — and a PowerPoint of the same
slide, built from native, editable shapes. It has two pages:

* **Timeline** — one list becomes one slide: a tinted band per swimlane, a bar per activity, a
  diamond per milestone, each labelled with its name and finish date, a check beside what is
  complete, a month/year header and a red line at the **data date** — your computer's date unless
  you set one with the **Data date** control above the slide (one setting for both pages; the
  slide's caption and legend follow it, and the subtitle says both the data date and the day the
  slide was prepared when they differ).
* **Compare** — two lists (a PRIOR and a CURRENT) on one slide: what slipped, what pulled in, what
  is new and what was removed, every move in calendar days.

On either page you can draw **logic links**: pick two items (or click them on the slide — first the
predecessor, then the successor), choose the type (Finish-to-Start by default, or Start-to-Start,
Finish-to-Finish, Start-to-Finish) and add the link. Add as many pairs as you need (up to 200). Only the links
you add are drawn — on the page and in the PowerPoint export.

The slide always fills the page: a short list gets large bars and text, a long one smaller. Every
link you add is fitted — when the rows leave no clean route the slide makes more room between the
rows, then adds a gutter lane at the right edge, then reorders items within their swimlane (never
across), and says so under "How the logic links were fitted"; a link that still cannot be drawn
clear of the others is drawn **dashed**, with what it covers named on the page and in the slide's
footnote — up to four lines; past them the footnote counts the rest and the page names them (the
PowerPoint carries the footnote too). It is never split onto a second slide.

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

A small window opens and your browser shows LODESTAR's launch page — take a star fix, or skip
straight to the studio (tick *Go straight to the studio next time* and it will). **Leave the small
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
list is not CUI.

---

LODESTAR is built from the same modules as the One-Pager pages of POLARIS², so both draw the same
slide from the same list. Version 1.0.2.

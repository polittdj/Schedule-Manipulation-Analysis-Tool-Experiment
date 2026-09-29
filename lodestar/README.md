# LODESTAR — One-Pager Studio

**Created by David Politte.** Questions or issues: [david.j.politte@nasa.gov](mailto:david.j.politte@nasa.gov)

LODESTAR turns a plain Excel list into a one-slide swimlane timeline — and a PowerPoint of the same
slide, built from native, editable shapes. It has two pages:

* **Timeline** — one list becomes one slide: a tinted band per swimlane, a bar per activity, a
  diamond per milestone, each labelled with its name and finish date, a check beside what is
  complete, a month/year header and a red line at today.
* **Compare** — two lists (a PRIOR and a CURRENT) on one slide: what slipped, what pulled in, what
  is new and what was removed, every move in calendar days.

On either page you can draw **logic links**: pick two items (or click them on the slide — first the
predecessor, then the successor), choose the type (Finish-to-Start by default, or Start-to-Start,
Finish-to-Finish, Start-to-Finish) and add the link. Add as many pairs as you need (up to 200). Only the links
you add are drawn — on the page and in the PowerPoint export.

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

A small window opens and your browser shows LODESTAR. **Leave that window open while you work.** To
stop, press **Quit** on the page, or close the window.

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
slide from the same list. Version 1.0.0.

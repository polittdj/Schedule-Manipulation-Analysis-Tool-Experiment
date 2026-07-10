/* Schedule Forensics — hover explainers on EVERY visual's name, on EVERY page.
 *
 * Operator 2026-07-08: "I want EVERY visual to have a call out show when the user hovers over
 * the name of the visual on EVERY page that tells them what is being shown, provides examples
 * on how to interpret the data, explains how this information could be useful to a project
 * manager." This module carries the catalog (WHAT / EXAMPLE / HOW TO READ / PM USE per visual)
 * and decorates each matching <h2>/<h3> with the shared data-sf-hint callout (hud.css). It
 * watches the DOM, so headings that charts add after their fetch are decorated too. The
 * Mission Control tiles keep their own server-provided hints (already present -> skipped).
 * Dependency-free, air-gap-safe.
 */
"use strict";

(function () {
  function H(what, example, read, use) {
    return "WHAT: " + what + "\nEXAMPLE: " + example + "\nHOW TO READ: " + read + "\nPM USE: " + use;
  }

  // Matched by case-insensitive SUBSTRING against the heading text, first match wins — so
  // dynamic headings ("Driving path: file", "EVM — file") still match on their stable part,
  // and MORE-SPECIFIC keys must sit ABOVE the broader ones they would otherwise lose to
  // (e.g. "finish-date confidence" above "s-curve"). 2026-07-10 coverage audit (ADR-0187):
  // every chart/graph heading on every page now has an entry.
  var CATALOG = [
    // ---- specific-before-broad (collision winners) ----
    ["finish-date confidence", H(
      "The risk-adjusted probability distribution of the project finish from the SRA runs, as a confidence S-curve.",
      "P80 on 2027-03-14 = 80% of simulated futures finish on or before that date.",
      "Read the date at your required confidence level; the gap between P50 and the deterministic date is optimism bias.",
      "Lets you commit to a date with a stated confidence instead of a single hopeful number.")],
    ["assign risk ranking factor", H(
      "The input control that ranks a task's uncertainty 1-5 (or sets explicit Best/Worst days) to feed the simulation.",
      "Ranking a 20-day task a 4 widens its simulated duration spread per the factor table.",
      "0 = no uncertainty (remaining duration is used); 5 = the widest spread; explicit Best/Worst overrides win.",
      "How you encode engineering judgement about which durations are shaky before running the SRA.")],
    ["execution indices", H(
      "BEI, CEI and HMI plotted together across versions — three views of whether the team executes what it plans.",
      "BEI 0.97 with CEI 0.45 = the baseline volume is roughly held, but the near-term plan keeps not happening.",
      "All three read 1.0 when execution matches plan; diverging lines tell you WHICH promise is failing (baseline, current plan, or period hits).",
      "The one chart that separates long-run baseline drift from short-run execution failure.")],
    ["left the critical path", H(
      "Activities that were on the previous version's critical path but are not on this one — drawn as ghost bars at their prior position, each with the reason they left.",
      "A task that left because 'logic removed' without completing deserves a question; one that left because 'completed' is healthy flow.",
      "Dashed struck-through bars are the ghosts; hover the Why column for the change detail.",
      "Path exits that aren't completions are the strongest manipulation tell — this lists every one, cited.")],
    ["critical path —", H(
      "This version's critical path drawn as a standard Gantt on a date axis locked across every version.",
      "Green bars entered the path since the prior version; a ▲ marks a duration change on the path.",
      "Step Prev/Next to watch the path extend as the finish slips; click any row for its full Task Information.",
      "Watching WHERE the path changes version to version localizes what is really driving the finish.")],
    // ---- Trend page charts ----
    ["schedule progress", H(
      "The section of trend charts tracking raw progress across versions: finish movement, completions, criticality and logic health.",
      "Finish slipping while completions stay flat = promises moving without work landing.",
      "Read the four charts together — each names the update where its line stepped.",
      "The at-a-glance progress story across every loaded submittal.")],
    ["cross file comparison", H(
      "Side-by-side population comparisons across the loaded files: status, activity types, variances and execution indices per data date.",
      "The 'complete' share barely moving between two files contradicts an on-plan narrative.",
      "Each bar group is one file, captioned with its data date.",
      "The quickest way to see what actually changed from one submittal to the next.")],
    ["project finish (days", H(
      "Each version's forecast project finish, in working days relative to the first loaded version.",
      "+22 d on the third file = the promised finish has slipped a month of working days since the first submittal.",
      "A rising staircase is steady slippage; a sudden drop without matching completed work deserves scrutiny.",
      "The headline trend: what has each successive update promised, and which update moved it.")],
    ["completed activities", H(
      "The cumulative count of completed activities in each loaded version.",
      "1,240 → 1,241 across a month-long update = essentially no work was finished that period.",
      "The curve should climb steadily between updates; flat segments are stalled periods.",
      "Verifies reported progress corresponds to actual completions, version over version.")],
    ["critical (incomplete)", H(
      "How many incomplete activities are critical in each version.",
      "180 → 320 critical tasks after an update = the network tightened sharply (or float was consumed).",
      "Growth means more of the remaining work has no margin; compare against the finish trend.",
      "A swelling critical population predicts schedule fragility before the dates move.")],
    ["missing logic (activities)", H(
      "Activities with no predecessor or successor, per version (DCMA-01 population).",
      "12 → 60 after an update = the update disconnected part of the network.",
      "Any step up means new open ends — find which tasks in the Ribbon drill.",
      "Open logic is where slips hide; this shows the update that introduced them.")],
    ["activity status by data date", H(
      "The population split (complete / in-progress / not started) at each version's data date.",
      "A barely-moving 'complete' share across three updates contradicts an on-plan story.",
      "Compare the shares version to version; the data-date caption names each file.",
      "A quick reality check that status is actually advancing between submittals.")],
    ["activity type by data date", H(
      "The mix of tasks, milestones and summaries in each version.",
      "A jump in milestone count without scope change may be re-classification, not new work.",
      "Watch for composition changes between versions — they mark restructuring.",
      "Restructuring context for every other trend on this page.")],
    ["schedule variance (svt", H(
      "The time-based schedule variance SV(t) across versions — how far execution runs behind the baseline in working days.",
      "SV(t) −40 d means the program is earning its schedule six working weeks late.",
      "More negative is worse; the slope shows whether the gap is widening.",
      "The EVM-language slippage trend a customer analyst will compute from the same files.")],
    ["mei (milestone", H(
      "Milestone Execution Index per version: of the milestones due, how many were hit.",
      "MEI 0.5 = half the milestones due to date have actually completed.",
      "1.0 is on-plan; falling MEI with a steady finish date means the plan is being reshuffled.",
      "Milestones are the contract's heartbeat — this is their hit rate over time.")],
    ["bei (baseline execution", H(
      "Baseline Execution Index per version: cumulative completions vs the baseline plan (DCMA-13).",
      "BEI 0.87 = 87 tasks finished for every 100 the baseline said should be done by now.",
      "Below ~0.95 is behind; the DCMA threshold treats <0.95 as a flag.",
      "The standard, defendable 'are we executing the baseline' number, trended.")],
    ["epi (execution", H(
      "Execution Performance Index per version — near-term execution against the current plan.",
      "EPI 0.7 = only 70% of the recently-planned work actually happened.",
      "1.0 is on-plan; sustained low EPI means the current plan is aspirational.",
      "Predicts next period's slip from demonstrated current-plan performance.")],
    ["bri (baseline realism", H(
      "Baseline Realism Index per version — how achievable the remaining baseline is given demonstrated performance.",
      "BRI 0.6 says the remaining plan assumes a pace the team has never demonstrated.",
      "Lower is less realistic; watch it after every re-baseline.",
      "Flags a plan that only works on paper before it fails in execution.")],
    ["forecast execution index", H(
      "FEI per version: of the work the PREVIOUS update forecast for this period, how much executed.",
      "FEI 0.4 = the last update's near-term forecast was 60% wrong.",
      "1.0 means updates forecast honestly; persistently low FEI means each update over-promises.",
      "Measures the credibility of each submittal's own near-term forecast.")],
    ["hit or miss index", H(
      "HMI per period: of the activities the baseline placed in this window, how many hit their dates.",
      "HMI 0.62 = 38% of this period's baseline commitments were missed.",
      "1.0 is on-plan; the period-over-period pattern matters more than one value.",
      "The period-level scorecard of promise-keeping against the baseline.")],
    ["float ratio", H(
      "The ratio of total float to remaining duration across the incomplete population, per period.",
      "A ratio falling toward 0 means remaining work is running out of room to absorb slips.",
      "Falling = margin consumed faster than work retires; rising = healthy or re-padded.",
      "An early-warning gauge of margin burn that single-file float counts can't show.")],
    ["start-to-finish ratio", H(
      "How many activities started vs finished in each version's window.",
      "Starting 60 and finishing 15 per period grows work-in-progress fourfold.",
      "A ratio far above 1 means work is being opened, not closed.",
      "Chronic open-not-close is the flow problem behind most bow waves.")],
    ["float sums by version", H(
      "The total working days of float in the network, summed per version.",
      "A 30% drop in one update = the network consumed (or someone removed) a third of its margin.",
      "Watch step changes; gradual decline is normal consumption.",
      "The program's total shock-absorber capacity, trended.")],
    ["% total float by days", H(
      "The share of activities with 0, <5 and <10 working days of total float, per version.",
      "The 0-day share growing 8% → 25% = a quarter of the plan is now margin-less.",
      "Growing low-float shares mean broad tightening, not one bad path.",
      "Shows whether criticality is concentrated or spreading across the plan.")],
    ["% free float by days", H(
      "The share of activities with 0, <5 and <10 working days of FREE float, per version.",
      "High zero-free-float share = most tasks immediately push their successors when they slip.",
      "Free float is the local cushion; its erosion makes daily slips contagious.",
      "Explains why small slips cascade — or why they don't.")],
    // ---- other pages ----
    ["actual vs baseline by month", H(
      "Actual finishes vs baseline finishes bucketed by month.",
      "20 baseline finishes in March vs 6 actuals = the March plan mostly didn't happen.",
      "Bars behind the baseline profile show work sliding right into future months.",
      "Shows the near-term realism of the plan month by month.")],
    ["worst finish variances", H(
      "The activities whose finishes moved furthest from baseline in this file, worst first.",
      "'UID 412: +87 d' finished 87 working days late against baseline.",
      "Scan the top rows — they usually share a cause (one supplier, one review board).",
      "The biggest movers explain most of the slip; start root-cause here.")],
    ["largest start variances", H(
      "The activities whose actual starts moved furthest from their baseline starts.",
      "A start +60 d late on a long task is tomorrow's finish slip announced today.",
      "Late starts precede late finishes; compare against the finish-variance list.",
      "Catches slips at the point they begin instead of when they land.")],
    ["driving path:", H(
      "The driving corridor between the chosen source and target activities, per version.",
      "The chain from 'Award' to 'Ready to Ship' drawn with its every link, stepped across updates.",
      "Step versions to watch the corridor shift; entered activities are outlined.",
      "Shows how the route between two commitments evolved — useful in delay narratives.")],
    ["all driving-tier activities", H(
      "Every activity in the driving-slack tiers to the target, as a drillable table.",
      "34 tasks within 10 d of driving = a broad near-critical front, not one thin path.",
      "Add columns or filter; a fat secondary tier means small slips can re-route the path.",
      "Sizes the management problem around your milestone: one path to watch, or a front.")],
    ["critical-path volatility", H(
      "How much the critical path's MEMBERSHIP churned across versions — entries, exits, tenure and stability.",
      "A path that swaps a third of its members every update without finishing work is being steered.",
      "The tiles below decompose the churn: who entered/left, how long tasks stay, who jumps on and off.",
      "Path churn without completions is the strongest manipulation signature this tool computes.")],
    ["volatility scoreboard", H(
      "The headline churn numbers behind the volatility tiles: entries, exits, stability and tenure stats per transition.",
      "'12 entered / 9 left' between two updates on a ~40-task path = ~25% membership turnover.",
      "Read alongside the finish movement — churn that never improves the date is suspicious.",
      "The citable numbers to quote when questioning path stability.")],
    ["performance analysis summary", H(
      "The IPMR-style performance wall: monthly census, bow wave, execution indices, workoff burden and duration-ratio views, per version.",
      "Step the versions to watch the to-go census hump migrate right — the bow wave forming.",
      "Each chart names its file and data date; the stepper animates all of them in lockstep.",
      "The month-by-month realism check package, automated from the schedule metadata.")],
    ["what-if: work added", H(
      "Activities that JOINED the critical path between the two selected versions, with their dates and drivers.",
      "A task added to the path with a new hard constraint explains a finish move no work caused.",
      "Each row cites the joining activity; compare against the removed list.",
      "Half of the answer to 'why did the path change?' — the other half is what left.")],
    ["what-if: work removed", H(
      "Activities that LEFT the critical path between the two selected versions, and what the finish would be had they stayed.",
      "Removing a 40-day chain from the path 'recovered' three weeks — the counterfactual shows it.",
      "The counterfactual finish quantifies how much of the improvement came from the removals.",
      "Separates real recovery from path surgery, in working days.")],
    ["project rollup", H(
      "The project forecast recalculated bottom-up: each group's exact SPI(t) weighted by its to-go work re-runs IEAC(t), and each group's own throughput extrapolates its own backlog (the latest group finish is the bottleneck answer).",
      "A group-weighted IEAC(t) two months later than the top-down one = the remaining work sits in groups performing worse than the project average.",
      "Compare the rollup column against the top-down column; coverage and unforecastable groups are disclosed under the table.",
      "Catches the classic averaging trap: a healthy project-wide index hiding a struggling group that owns the rest of the plan.")],
    ["execution metrics by field group", H(
      "BEI / HMI / SPI-family execution metrics computed separately for each value of the chosen field (CAM, IPT, custom code …).",
      "CAM 'Jones' at BEI 0.7 while the program reads 0.93 localizes the slip to one account.",
      "Pick the grouping field; each row is that group's own execution scorecard.",
      "Turns 'the program is behind' into 'THIS account is behind', with numbers.")],
    ["working calendar", H(
      "The schedule's working calendar: work weekdays, hours per day, and holidays the CPM respects.",
      "A 4×10 calendar with July shutdowns explains why a '10-day' task spans three weeks.",
      "Every duration and float figure on the site is computed in THESE working days.",
      "Check this first when durations look wrong — the calendar is usually why.")],
    ["one-at-a-time", H(
      "Deterministic sensitivity: each duration is varied alone and the finish movement recorded.",
      "'UID 88: +10 d input → +10 d finish' is fully driving; '+10 → +0' floats free.",
      "1:1 responders are on the driving path; fractional response = partial leverage.",
      "Finds the day-for-day tasks without running a full simulation.")],
    ["issues (current", H(
      "The engine's current concerns for the loaded files — problems that exist now, with citations.",
      "'57 tasks with negative float' is an issue today, not a risk of one tomorrow.",
      "Sort by severity; every claim links to the tasks that prove it.",
      "The working list of what needs fixing in the schedule as it stands.")],
    ["opportunities (", H(
      "Findings where the schedule could realistically improve — early finishes, recoverable logic, unused margin.",
      "A chain finishing 20 d early feeds float the plan isn't using downstream.",
      "Each opportunity cites its tasks; weigh against the effort to capture it.",
      "Recovery planning starts from these, not from wishful re-promising.")],
    ["risks (", H(
      "The engine's forward-looking schedule risks for the loaded files, with severity and citations.",
      "'HIGH — merge point of 9 near-critical chains before integration' names the choke point.",
      "Sort by severity; each risk lists the tasks behind it.",
      "An evidence-backed risk register seeded straight from the schedule's own structure.")],
    ["dcma-14 checks", H(
      "The 14 DCMA schedule-health checks scored on this file, each with its measured value and a pass/fail stoplight.",
      "“Logic — 5% missing links: FAIL” means more than the allowed 5% of tasks have no predecessor or successor.",
      "Green = within the DCMA threshold, red = outside it; hover a row for the threshold, why it matters and pass/fail examples.",
      "A quick contract-grade health screen — fix the red checks before trusting dates or briefing the customer.")],
    ["dcma-14 audit", H(
      "The full DCMA-14 audit table: every check with its count, percentage of the population, and a suggested improvement.",
      "“High Float: 62 of 132 (47%)” says nearly half the detail tasks carry more than 44 days of float.",
      "Compare the % column against each check's threshold; the stoplight board above summarizes the same rows.",
      "Use the suggested-improvement column as a to-do list to raise schedule quality file by file.")],
    ["baseline compliance", H(
      "How execution tracked the baseline plan: counts of activities that started/finished on time, late, or not at all.",
      "“Completed late: 23” = 23 activities finished after their baseline finish date.",
      "Green bars are on-plan, amber late, red missing — bigger late/missing bars mean the baseline is slipping away.",
      "Shows whether the team is executing to the plan or the plan has quietly become fiction.")],
    ["interactive analysis", H(
      "The working surface for one schedule: DCMA stoplights, baseline compliance, the driving-path trace and the full activity grid + Gantt.",
      "Type a UID and press Trace to see exactly which chain of tasks drives that milestone.",
      "Every number is computed locally from the loaded file; click any grid row to drill into its metadata and citation.",
      "This is where an analyst verifies a claim (“why is this late?”) down to the task level.")],
    ["activities & gantt", H(
      "Every activity in the file as a sortable, filterable grid with an MS-Project-style timeline (critical in red, milestones as diamonds).",
      "Filter Total float to “0” to see only the critical chain laid out in time.",
      "The amber vertical line is the data date; bars left of it should be complete — incomplete bars behind it are late.",
      "The ground truth behind every chart on the site; use Columns to add any field, including your custom ones.")],
    ["driving path to uid", H(
      "The chain of activities that actually sets the date of your chosen target UID, tiered by how close each task is to driving it.",
      "A red DRIVING row with slack 0 d moves the target day-for-day if it slips.",
      "Tiers: driving (0 slack to target), secondary/tertiary (near-driving), beyond; the waterfall orders by finish.",
      "Tells you exactly which handful of tasks to manage to protect a milestone — not the whole schedule.")],
    ["activity scatter", H(
      "Each activity plotted by its total float (x) against duration (y); color = critical/normal.",
      "A dot at float 0, duration 60 d is a two-month task with no schedule margin — high risk.",
      "Bottom-left (low float, short) is healthy churn; anything tall on the zero-float line deserves attention.",
      "Spots the long, zero-margin tasks that make the whole plan brittle at a glance.")],
    ["total-float distribution", H(
      "Activities binned by total float in DCMA-aligned bands, so the shape of the float profile is visible.",
      "588 activities in the “> 44 d” band on a 720-task schedule = most of the file floats free — likely missing successor logic.",
      "Mass at “< 0 / 0” is the critical-and-behind core; a huge high band is float padding or open ends (DCMA-06). Click a bar to list that band's tasks on the right and export them to Excel.",
      "Reveals whether the network is really constrained or just loosely wired — before you trust any float number.")],
    ["float analysis", H(
      "Counts of activities in the low-float bands the handbook watches (≤ 5 d, ≤ 10 d, negative).",
      "“Negative float: 57” = 57 activities are already behind a constraint — the plan promises dates it cannot meet.",
      "Watch the negative and ≤5 d counts version to version; growth means the margin is being consumed.",
      "The early-warning gauge for a schedule running out of room.")],
    ["completion performance", H(
      "Throughput measures: how many activities finished vs planned in the status window (hit rates, CEI-style ratios).",
      "A 0.62 hit rate = only 62% of the tasks planned to finish in the window actually finished.",
      "1.0 is on-plan; sustained values below ~0.8 forecast further slippage regardless of what the dates claim.",
      "Predicts near-term slips from demonstrated performance, not promises.")],
    ["structural health checks", H(
      "Network-structure sanity checks: dangling logic, orphans, duplicate links, out-of-sequence progress and similar wiring faults.",
      "“Out-of-sequence progress: 12” = a dozen tasks recorded progress against the declared logic order.",
      "Any non-zero count is a specific list of tasks to fix — click through to see the citations.",
      "Wiring faults make every downstream date suspect; this is the first thing to clean.")],
    ["logic integrity", H(
      "Where the network's logic is weak: missing predecessors/successors, leads, lags, and link-type abuse.",
      "“14 tasks with no successor” means 14 places where a slip silently fails to push anything downstream.",
      "Open ends and leads are the red flags; small lag counts are normal engineering.",
      "Open logic is where schedules hide slips — close these before relying on the critical path.")],
    ["constraint health", H(
      "Every date constraint in the file (Must-Finish-On, Start-No-Earlier-Than, …) and whether it fights the network logic.",
      "A Must-Finish-On sitting 10 days before the logic-driven finish creates −10 d of float — an impossible promise.",
      "Hard constraints (red) pin dates against logic; soft ones (amber) merely delay. Fewer is healthier (DCMA ≤ 5%).",
      "Constraints are how a schedule is made to say what someone wants — audit them before believing the dates.")],
    ["vertical integration", H(
      "Whether the WBS levels tell one consistent story: do summary dates truly roll up from their children?",
      "A summary bar ending before its last child finishes indicates a manually-edited rollup.",
      "Mismatched rollups are listed with the offending UIDs.",
      "Catches hand-painted summary bars that make a briefing chart disagree with the working schedule.")],
    ["schedule variance (time)", H(
      "Per-activity time variance: actual/forecast dates against the baseline, aggregated and listed.",
      "“SV(t) −8 d” on a milestone = it is running eight working days behind the baselined date.",
      "Negative is late; look at the largest movers, not the average.",
      "Turns “are we late?” into a ranked list of exactly what is late and by how much.")],
    ["float erosion", H(
      "How each WBS branch's float has been consumed across versions.",
      "A branch that fell from 30 d to 4 d of average float in two updates is burning margin fast.",
      "Steep downward slopes are the branches to intervene in; flat lines are stable.",
      "Shows where the schedule is quietly spending its safety margin before it shows up as lateness.")],
    ["schedule margin burndown", H(
      "The declared schedule margin (buffer tasks / margin activities) over time against a healthy burn line.",
      "Margin dropping from 40 d to 10 d at 50% complete means the buffer is being spent twice as fast as earned.",
      "Compare the actual burn against the ideal diagonal; below the line = overspending margin.",
      "Margin is the program's shock absorber — this shows whether it will last to the finish.")],
    ["schedule margin", H(
      "Where the schedule keeps its explicit margin/buffer activities and how much remains.",
      "A single 15-day “Schedule Margin” task before delivery is the program's entire buffer.",
      "Check the remaining-duration column — margin that has been re-purposed as work is gone.",
      "Protecting visible margin is cheaper than explaining a slipped delivery later.")],
    ["schedule quality ribbon", H(
      "One row per loaded file scoring the Fuse-style quality measures (Missing Logic, Logic Density™, Critical, Hard Constraints, Negative Float, Lags, Leads, Merge Hotspot, Insufficient Detail™, float stats).",
      "Missing Logic 12% red on File 3 = an eighth of its tasks have open ends.",
      "Green/yellow/red per thresholded measure (legend below); compare columns ACROSS files to see which update introduced a problem.",
      "A one-screen quality scoreboard for every version you loaded — ideal for spotting the update that broke the network.")],
    ["s-curve", H(
      "Cumulative planned vs earned progress over time — the classic S-curve.",
      "The earned curve tracking 2 months right of planned = the program is two months behind in volume terms.",
      "The horizontal gap between curves is schedule slip; a flattening earned curve is stalled work.",
      "The single most-briefed picture of overall progress — and the first place fake progress bends.")],
    ["finish-date confidence", H(
      "The risk-adjusted probability distribution of the project finish from the SRA runs, as a confidence S-curve.",
      "P80 on 2027-03-14 = 80% of simulated futures finish on or before that date.",
      "Read the date at your required confidence level; the gap between P50 and the deterministic date is optimism bias.",
      "Lets you commit to a date with a stated confidence instead of a single hopeful number.")],
    ["finish-date distribution", H(
      "The histogram of simulated project finish dates behind the confidence curve.",
      "A long right tail means a few risk combinations produce very late finishes.",
      "The deterministic finish sitting left of the mode means the plan assumes better-than-typical luck.",
      "Shows how much of the date risk comes from a few scenarios you could buy down.")],
    ["cei", H(
      "Current Execution Index: near-term execution reliability — of the work planned recently, how much actually happened.",
      "CEI 0.55 over the last 4 weeks = barely half the near-term plan executed.",
      "1.0 is on-plan; the trend matters more than any single value.",
      "The best short-range predictor: a plan that isn't executing this month won't execute next month either.")],
    ["earned value management", H(
      "The EVM indices for this file: PV/EV/AC, SPI, CPI, schedule-in-time variants, and forecast (EAC/ETC) where cost is present.",
      "SPI 0.87 = earning 87 cents of planned schedule value per planned dollar-day — behind.",
      "Below 1.0 is behind/over; pair SPI with SPI(t) late in the project (SPI drifts to 1.0 by construction).",
      "The contract-language view of performance — what the customer's analysts will compute from the same data.")],
    ["cost performance", H(
      "Cost-side EVM: actual cost against earned value (CPI) and the resulting at-completion forecast.",
      "CPI 0.92 means every earned dollar cost $1.09 — an 8% overrun trend.",
      "CPI below 1.0 compounds; check the EAC line against the budget line.",
      "Flags cost overrun trends while there is still budget left to act.")],
    ["schedule performance", H(
      "Schedule-side EVM over time: SPI / SPI(t) trends across the loaded versions.",
      "SPI(t) falling 0.98 → 0.91 → 0.85 across updates is a steady loss of schedule performance.",
      "Trend direction is the signal; a recovering index should be corroborated by real finishes, not re-planning.",
      "Distinguishes genuine recovery from baseline surgery.")],
    ["spi(t)", H(
      "Earned-schedule SPI(t) per WBS branch — which parts of the program are earning schedule and which are dragging.",
      "Branch 1.4 at SPI(t) 0.78 while the program shows 0.95 = the slip is concentrated there.",
      "Values below 1.0 are behind in time terms; drill the lowest branches first.",
      "Localizes the schedule problem to the organization that owns it.")],
    ["completion metrics by wbs", H(
      "Per-WBS completion throughput — planned vs actual finishes for each branch.",
      "A branch with 40 planned / 12 actual finishes this period is the bottleneck.",
      "Sort by the biggest plan-vs-actual gap.",
      "Tells you which team's flow to fix, not just that “the program” is behind.")],
    ["schedule-quality trends", H(
      "The DCMA/quality metric values tracked across every loaded version of the schedule.",
      "Hard constraints rising 3 → 9 → 21 across updates = someone is progressively pinning the plan.",
      "Look for step changes between versions — they mark the update where behavior changed.",
      "Trends expose manipulation patterns a single-file audit cannot see.")],
    ["manipulation-trend signals", H(
      "Version-over-version signals associated with schedule manipulation: shortened in-progress durations, deleted logic, added constraints, baseline edits, erased actuals.",
      "“In-progress durations shortened on 17 tasks before the driving path” two updates in a row is a pattern, not noise.",
      "Each signal is cited to its tasks; the Schedule Integrity page adds the counterfactual (what the finish would have been without the changes).",
      "Separates plausible replanning from changes that only make the numbers look better — for review, never accusation.")],
    ["version trend", H(
      "One metric plotted across every loaded version so its history is visible.",
      "Negative-float count 0 → 12 → 57 over three updates: the plan is progressively over-promised.",
      "Step changes locate the exact update to investigate; hover points for values.",
      "The fastest way to see when a problem was introduced.")],
    ["forecast drift", H(
      "How the project's forecast finish moved across versions (each update's promised end date).",
      "A finish that slips 3 weeks every month while reported % complete stays on plan is a classic bow wave.",
      "Rising staircase = steady slippage; flat with late-period jumps = deferred truth.",
      "Compares what each update promised — the record a claims analyst will build anyway.")],
    ["driving-slack degradation", H(
      "How much slack the driving path to the target lost between consecutive versions.",
      "−15 d in one update means the path to your milestone got three weeks tighter.",
      "Consistent negative bars = compounding pressure on the same chain.",
      "Watches the one path that matters instead of the average of everything.")],
    ["completed on the path", H(
      "Which driving-path activities actually completed between versions vs which just moved.",
      "3 completed / 9 slipped on the path this period = the critical work is not flowing.",
      "Completions retire risk; slips push it right — the ratio is the health of the path.",
      "Milestone dates only improve when path tasks finish; this shows if they are.")],
    ["slippage", H(
      "Cumulative start & finish slip curves per version — how much the population moved, when.",
      "A finish curve stepping up 400 task-days each update = broad, systemic slippage.",
      "Steeper is worse; separate start-slip (late starting) from finish-slip (late delivering).",
      "Quantifies whether slippage is a few bad actors or the whole plan drifting.")],
    ["data date finishes", H(
      "The actual-finish curve per version, anchored at each file's data date.",
      "Two versions with identical curves but different data dates = a period with no real progress.",
      "Curves should climb between updates; flat segments are stalls.",
      "Verifies that reported progress corresponds to actual completed work.")],
    ["finishes &", H(
      "Actual vs baseline finishes bucketed by month.",
      "20 baseline finishes in March vs 6 actuals = the March plan mostly didn't happen.",
      "Bars behind the baseline profile show the work sliding right into future months.",
      "Shows the near-term realism of the plan month by month.")],
    ["bow wave", H(
      "Activity finishes by month across versions — watching work pile up in front of the data date.",
      "Each update pushing this quarter's finishes into next quarter builds a wave that eventually breaks the end date.",
      "A growing hump just right of the data date is the wave; healthy plans spread it.",
      "The bow wave is the visual signature of deferred work — catch it before it hits the finish.")],
    ["largest finish variances", H(
      "The activities whose actual finishes moved furthest from baseline (worst first).",
      "“UID 412: +87 d” = that task finished 87 working days late against baseline.",
      "Scan the top 10 — they usually share a cause (one supplier, one facility, one review board).",
      "Root-cause fodder: the biggest movers explain most of the program slip.")],
    ["path analysis", H(
      "The SSI-style directional path workspace: trace predecessors/successors of a focus task with slack tiers, drag, grouping and link lines.",
      "Tracing UID 152 with Driving Slack ≤ 0 shows the exact chain that sets its date; Run Drag Analysis adds each task's day-for-day leverage.",
      "Options mirror the SSI tool (direction, dependency range, ignore constraints/leveling, output modes); red links are on-path.",
      "The forensic microscope for one milestone — what drives it, by how much, and what to shorten first.")],
    ["critical-path evolution", H(
      "How the critical/driving path to the finish changed across versions.",
      "A task on the path in v3 but gone in v4 without completing = the path was changed around it.",
      "Compare membership version to version; the Integrity page computes what the finish would be without those changes.",
      "Path churn without work completing is the strongest manipulation tell.")],
    ["corridor over time", H(
      "The A→B driving corridor between two chosen tasks, animated across versions.",
      "Watch the corridor tighten as intermediate tasks slip — the same chain gets more critical each update.",
      "Use the version stepper or auto-play; entered tasks are highlighted.",
      "Shows how the route between two commitments evolved — useful in delay narratives.")],
    ["driving tiers", H(
      "How many activities sit in each driving-slack tier to the target (driving / secondary / tertiary / beyond).",
      "34 tasks within 10 d of driving = a broad near-critical front, not a single thin path.",
      "A fat secondary tier means small slips anywhere can re-route the path.",
      "Sizes the management problem: one path to watch, or a whole front.")],
    ["quality drill-down", H(
      "Per-file quality metrics with drill-through to the offending activities, animated across versions.",
      "Click the missing-logic count to list exactly which tasks have open ends in that version.",
      "Step versions to see when each population grew.",
      "Turns quality scores into concrete task lists per update.")],
    ["schedule risk & opportunity", H(
      "The SSI-style schedule risk analysis: rank risk factors, set Best/Worst durations, simulate, and read confidence dates.",
      "Ranking a task 5 widens its Best/Worst spread; the S-curve then shows the finish at P50/P80.",
      "Fill the grid (or paste from Excel), run, then read the tornado for the biggest drivers.",
      "Produces defensible confidence dates and a ranked buy-down list instead of gut feel.")],
    ["risk drivers", H(
      "Tornado chart: which activities' uncertainty moves the finish date most in the simulation.",
      "The top bar spanning ±18 d means that one task's spread dominates the finish risk.",
      "Longer bars = bigger leverage; work down from the top.",
      "Your risk-buy-down priority list — spend mitigation money where the bars are long.")],
    ["duration sensitivity", H(
      "One-at-a-time deterministic sensitivity: vary each duration and record the finish movement.",
      "“UID 88: +10 d input → +10 d finish” = fully driving; “+10 → +0” = floats free.",
      "Tasks with 1:1 response are on the driving path; fractional response = partial leverage.",
      "Identifies day-for-day tasks without running a full simulation.")],
    ["risk matrix", H(
      "The likelihood × impact grid of the register's risks and opportunities.",
      "A risk at likelihood 4 / impact 5 sits top-right — act now.",
      "Top-right quadrant = mitigate; bottom-left = monitor; opportunities plot green.",
      "The standard review-board picture for prioritizing the register.")],
    ["risk ranking", H(
      "The register sorted by score (likelihood × impact), highest first.",
      "Score 20 at the top vs 4 at the bottom — the top handful deserve the attention.",
      "Rank order matters more than absolute scores.",
      "Focus scarce mitigation effort where the product is largest.")],
    ["finish forecast", H(
      "The simulated finish forecast for this file: confidence dates and spread from the risk inputs.",
      "P50 2026-11-02, P80 2027-01-19: a 2.5-month gap = wide uncertainty.",
      "A wide P50–P80 spread means the plan's outcome depends on how risks land.",
      "Choose commitments by confidence, and show the customer the honest spread.")],
    ["forecast cards", H(
      "Per-version snapshot cards of the risk-adjusted forecast (P-dates, spread, deterministic gap).",
      "P80 improving two updates in a row = genuine de-risking, not luck.",
      "Compare cards left to right for the trajectory.",
      "The one-glance answer to “is the risk position improving?”")],
    ["forecast spread", H(
      "The latest version's simulated finish spread in detail.",
      "A tight cluster around the deterministic date = the plan carries little modeled risk.",
      "Spread width = uncertainty; skew = which side the surprises are on.",
      "Sets expectations for how firm the current date really is.")],
    ["legacy sra", H(
      "The original Monte-Carlo SRA with multiplicative risk drivers (kept alongside the SSI-style module).",
      "A driver of 0.9–1.3 on a branch multiplies its durations by 90–130% per iteration.",
      "Configure drivers, run, read the same S-curve/tornado outputs.",
      "Useful when risk is better expressed as percentage factors than Best/Worst days.")],
    ["editable schedule grid", H(
      "The SRA input grid: per-task Risk Ranking Factor or explicit Best/Worst durations, Excel-paste enabled.",
      "Paste a factor column from Excel to rank 500 tasks in one gesture.",
      "Factors auto-fill Best/Worst from the table; explicit entries override.",
      "Gets a whole IMS risk-loaded in minutes instead of days.")],
    ["resource loading", H(
      "Resource assignments over time with over-allocation highlighted.",
      "A welder at 130% for three weeks = 30% of that work cannot actually happen as scheduled.",
      "Red segments are over-allocations; the histogram below shows totals per period.",
      "Over-allocated plans are schedules that will slip by construction — find them before they do.")],
    ["loading histogram", H(
      "Total demand per period for the selected resource(s) against capacity.",
      "Demand bars over the capacity line for four straight weeks = a staffing problem, not a scheduling one.",
      "Compare bar heights to the capacity line; sustained excess needs leveling or hiring.",
      "Turns resource arguments into a picture everyone reads the same way.")],
    ["resource roster", H(
      "Every resource in the file with its assignments and utilization.",
      "One person assigned to 40 concurrent tasks is a coordination single-point-of-failure.",
      "Sort by assignment count or peak utilization.",
      "Finds the human bottlenecks the network diagram hides.")],
    ["wbs breakdown", H(
      "The schedule rolled up by WBS branch: counts, dates, float and progress per branch.",
      "Branch 1.3 holding 80% of the negative float localizes the problem instantly.",
      "Expand the worst branches; healthy branches roll up green.",
      "Management happens by branch — this is the org-chart view of schedule health.")],
    ["breakdown by", H(
      "The same schedule grouped by the field you chose (phase, owner, custom code, …).",
      "Grouping by a CA-WBS custom field shows exactly which control account is slipping.",
      "Pick the grouping field at the top; every metric re-aggregates.",
      "Answers “whose problem is this?” in whatever structure your program uses.")],
    ["risks, opportunities & concerns", H(
      "The engine's findings for this file: risks, opportunities and concerns, each with severity, a suggested course of action and citations.",
      "“HIGH — 27 tasks with negative float on the driving path” cites the exact tasks.",
      "Sort by severity; every claim links to the tasks that prove it.",
      "A pre-written, evidence-backed issues list for the next status meeting.")],
    ["risks, issues & opportunities", H(
      "The cross-version register the tool assembles from every loaded file's findings.",
      "The same negative-float finding appearing in three consecutive versions = a standing issue, not noise.",
      "Filter by severity or category; recurring items are flagged.",
      "Tracks whether known problems are being worked or just re-reported.")],
    ["recovery plan", H(
      "Prioritized recovery actions derived from the findings (what to fix first for the most schedule benefit).",
      "“Restore the deleted FS link 412→415” ranks above cosmetic fixes because it re-opens a true path.",
      "Actions are ordered by expected impact on the finish.",
      "Turns analysis into an ordered work list you can hand to the scheduler.")],
    ["schedule health", H(
      "This file's headline health indicators on one card.",
      "Health 62/100 driven mostly by missing logic = a wiring problem, not a performance one.",
      "The sub-scores tell you which family of problems dominates.",
      "The 10-second answer to “how bad is it?” — with pointers to the details.")],
    ["schedule card", H(
      "The summary card for one loaded schedule: task counts, dates, data date, calendar and headline metrics.",
      "Two versions with the same finish but different data dates = a re-promised plan.",
      "Compare cards across versions for the vital signs.",
      "The quick-reference header for every deeper dive.")],
    ["loaded schedules", H(
      "Every schedule version currently loaded in the session, in analysis order.",
      "Load P2 then P5 to unlock every version-over-version trend and integrity check.",
      "The order shown here is the version order used by all trend pages.",
      "Multi-version loading is what turns the tool from an auditor into a forensic analyst.")],
    ["schedule integrity", H(
      "The manipulation-analysis page: per version pair, every cited change signal plus the counterfactual finish (what the date would have been WITHOUT the changes).",
      "“Finish held at 2026-09-01; without the 14 duration cuts it would have been 2026-10-13 — 30 working days of apparent recovery came from the changes, not work.”",
      "Use the exception field (e.g. a BCR number) to badge or hide authorized changes; everything else deserves a question.",
      "Analysis for review, never accusation — it gives the PM the exact questions to ask, with citations.")],
    ["counterfactual", H(
      "The engine reverts the path-shedding changes between two versions and re-runs CPM to show the finish that would have resulted.",
      "Actual 2026-09-01 vs counterfactual 2026-10-13 = the improvement came from edits, not execution.",
      "The delta in working days is the size of the apparent recovery attributable to the changes.",
      "Quantifies exactly how much of a “recovery” was real work versus schedule surgery.")],
    ["trend charts", H(
      "The full set of cross-version trend charts for every computed metric family.",
      "Pick any metric to see its history across the loaded versions.",
      "Step changes mark the update to investigate; hover for values.",
      "The longitudinal record of the schedule's behavior over time.")],
    ["ask the ai", H(
      "Ask questions about the loaded schedules in plain language; answers cite engine facts (mode-dependent figure gating).",
      "“Why did the finish move between P2 and P5?” returns the drivers with task citations.",
      "Strict mode discards unsourced figures; annotate flags them; interpretive returns raw model text.",
      "A fast analyst's assistant — verify anything important against the citations it provides.")],
    ["ai narrative", H(
      "The engine's findings rendered as a readable narrative by the local AI — every figure re-verified against engine citations.",
      "“The 30-day recovery is attributable to duration cuts on 14 in-progress tasks…” with the same numbers the engine computed.",
      "Digits are guaranteed to match the engine; wording is the model's.",
      "Briefing-ready prose without surrendering numerical fidelity.")],
    ["executive briefing", H(
      "The one-page executive summary assembled from the engine's findings across all files.",
      "Topline: finish trend, margin state, the top 3 risks and the recovery actions.",
      "Every figure traces to the engine; the AI only polishes wording.",
      "The artifact you hand leadership — generated, cited, and current.")],
    ["mission control", H(
      "Every visual on one wall: live tiles for the whole tool, scoped by the session-wide filter and target.",
      "Set a Group filter once and every tile re-scopes to it.",
      "Hover any tile's name for its own explainer; Enlarge or open the full page from the tile.",
      "The situation-room view — one glance across performance, paths, risk and quality.")],
  ];

  var lower = CATALOG.map(function (c) { return [c[0].toLowerCase(), c[1]]; });

  function hintFor(text) {
    var t = text.toLowerCase();
    for (var i = 0; i < lower.length; i++) {
      if (t.indexOf(lower[i][0]) >= 0) return lower[i][1];
    }
    return null;
  }

  function decorate(root) {
    var heads = (root || document).querySelectorAll(
      ".panel h2, .panel h3, .chart h3, .tile-head h3, main h2, main h3"
    );
    Array.prototype.forEach.call(heads, function (h) {
      if (h.hasAttribute("data-sf-hint")) return; // Mission tiles carry richer server hints
      var hint = hintFor(h.textContent || "");
      if (!hint) return;
      h.setAttribute("data-sf-hint", hint);
      h.classList.add("viz-hint");
      h.setAttribute("tabindex", "0"); // keyboard users get the callout on focus too
    });
  }

  function start() {
    decorate(document);
    // charts add their headings after fetch — decorate anything that appears later
    if (window.MutationObserver) {
      var mo = new MutationObserver(function () { decorate(document); });
      mo.observe(document.body, { childList: true, subtree: true });
    } else {
      setTimeout(function () { decorate(document); }, 1500);
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();

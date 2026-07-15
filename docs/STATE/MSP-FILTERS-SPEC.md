# Feature #10 — MS Project saved filters/groups (faithful reproduction): GROUND TRUTH + build plan

Verified 2026-07-15 against the operator's real `00_REFERENCE_INTAKE/mpp/Large Test File Leveled.mpp`
via an MPXJ probe (MPXJ 16.2.0, org.mpxj; classpath tools/mpxj/classes:lib/*). Feasible: Java 21 +
MPXJ + the real .mpp are all present. `views_leveled.json` in this scratchpad has the raw dump.

## MPXJ API (verified via javap)
- ProjectFile.getFilters() -> FilterContainer.getTaskFilters()/getResourceFilters(): List<Filter>
- Filter: getName, getShowRelatedSummaryRows, getCriteria()->GenericCriteria, getPrompts()->List<GenericCriteriaPrompt>, isTaskFilter/isResourceFilter
- GenericCriteria: getLeftValue()->FieldType, getOperator()->TestOperator, getValue(0/1), getCriteriaList()->List (children)
  - TestOperator leaf ops: IS_ANY_VALUE, IS_WITHIN, IS_GREATER_THAN, IS_LESS_THAN, IS_GREATER_THAN_OR_EQUAL_TO,
    IS_LESS_THAN_OR_EQUAL_TO, EQUALS, DOES_NOT_EQUAL, CONTAINS, IS_NOT_WITHIN, DOES_NOT_CONTAIN, CONTAINS_EXACTLY
  - Branch ops: AND, OR (node's operator; children in getCriteriaList())
- ProjectFile.getGroups()->GroupContainer (List<Group>); Group: getName, getShowSummaryTasks, getGroupClauses()->List<GroupClause>
  - GroupClause: getField()->FieldType, getAscending, getGroupOn()(int: 0=each value, 2=interval), getGroupInterval(), getStartAt()
- FieldType.getName() returns the RAW MSP name for custom fields (e.g. "Text9","Flag6","Duration8"), not the alias.

## The 10 task filters in the real file (the reproduction target)
- "All Tasks","All Resources": criteria=null (pass-through)
- "SVT-": Task Name CONTAINS 'SVT-'   | "No SVT-": DOES_NOT_CONTAIN 'SVT-' | "SVT": CONTAINS 'SVT'
- "Date Range...": prompts=2, showSummaryRows=True, AND(Finish >= PROMPT('..after:'), Start <= PROMPT('And before:'))
- "CAM_Tasks": AND(Text9 EQUALS 'ZIN', Start <= 2028-09-29T17:00), showSummaryRows=True
- "_MCexportedTasks": Flag6 EQUALS 'true'
- "_MCTasks": AND(Summary=false, Duration9 > Duration8 [FIELD-TO-FIELD], Duration8 >= 0.0d, Duration9 >= 0.0d,
    Text19 EQUALS '', Actual Finish EQUALS None [null test], Active=true, Milestone=false)
- "_RiskRegTasks": AND(Summary=false, Text19 != '', Actual Finish EQUALS None, Active=true)

## 25 groups (samples): "&No Group"(none), "Milestones"(Milestone), "Complete and Incomplete Tasks"(% Complete groupOn=2),
  "Critical"(Critical), "Duration then Priority"(Duration, Priority) — multi-clause, ascending, groupOn/interval per clause.
  Names carry '&' keyboard accelerators (strip for display).

## KEY INTEGRATION CHALLENGE (verify-first finding)
Filters reference RAW MSP field names. Tool's engine/grouping.py `field_value()` resolves custom fields by the
operator's RENAMED label (task.custom_field(label)) + only 6 STANDARD_FIELDS. Need a broad raw-MSP-field -> task-value
resolver covering: Name, Start, Finish, Actual Start/Finish, Duration, % Complete, Summary, Milestone, Active, Critical,
Priority, Constraint*, and the custom families Text1-30/Flag1-20/Number1-20/Duration1-10/Date1-10/Cost1-10/Outline Code.
CHECK whether Task stores custom fields by raw id or only by label, and the raw-id<->label mapping (custom_field_labels).

## Build plan (each its own gate-green PR, AFTER #367 merges to avoid version/installer collision)
1. Java export: extend tools/mpxj (new MpxjViewsWriter or a flag) to dump filters+groups to a sidecar JSON beside the
   MSPDI; wire importers/mpp_mpxj.py to load it; store on Schedule as saved_filters/saved_groups. Value can be a literal
   OR a FieldType (field-to-field) OR a prompt — preserve the distinction (v0type in the probe).
2. model/saved_view.py: SavedFilter(name, criteria: Criterion tree, prompts, show_summary_rows, is_task_filter),
   Criterion(op, field|None, values|field_ref|prompt, children), SavedGroup(name, clauses).
3. engine/msp_filters.py: faithful evaluator — recursive AND/OR, all 12 leaf ops, field-to-field, null/empty, typed
   coercion (dates/durations/booleans/%). Broad raw-field resolver. Tested against THIS file's 10 filters (ground truth).
4. Session-wide grouping (operator choice) mirroring the session-wide filter; A->Z ordering of every field/filter/group
   list; highlight mode (select() marks rather than drops — task names, data cells, gantt bars).
5. UI: /groups pickers listing standard + custom filters & groups (A->Z), interactive prompt inputs for "Date Range..."
   style filters, highlight toggle. 4-theme Chromium DoD.

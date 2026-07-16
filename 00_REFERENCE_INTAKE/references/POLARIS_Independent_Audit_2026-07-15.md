# POLARIS Independent Repository and CoPilot Performance Audit

**Audit date:** 2026-07-15  
**Repository:** `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment`  
**Audited HEAD:** `60728c2b0ecbde7142119b65ba8d701bb981f497`  
**Prior fully documented code state:** `2dc369678dfc294db189d1bc706eba4ab02b752a`, v1.0.43, ADR-0231  
**Delta:** seven intentional deletions of reference XER files; no source-code changes.

## Verdict

**REJECT for unconditional release approval / INSUFFICIENT EXECUTED EVIDENCE for the exact HEAD.**

This does not mean the code is generally poor. The exact HEAD has no attached CI result, the full repository gate could not be executed in this connector-only environment, full P6 parity is currently unavailable, and the prompt’s required metric-contract/oracle registries are not present.

## Reference corpus

Both supplied ZIP archives were recursively inventoried.

- 436 extracted paths
- 175 unique SHA-256 payloads
- 200 XLSX paths / 83 unique
- 141 MPP paths / 40 unique
- 34 XML paths / 10 unique
- 17 DOCX paths / 11 unique
- 11 unique PDFs
- 0 XER files
- No structural-audit parse errors recorded
- The seven repository XER deletions were operator-intentional; replacement real-world XER files remain an open validation dependency.

## CoPilot performance findings

| # | CoPilot finding | Verdict | Correct priority |
|---|---|---|---|
| 1 | CPM becomes O(N·E) | **Refuted** | No change without profiling |
| 2 | Holiday logic causes billions of comparisons | **Materially overstated** | Low/conditional |
| 3 | Repeated path traversals | **Partially valid** | Low |
| 4 | Analysis cache is unbounded | **Valid at portfolio scale** | Medium |
| 5 | Full metrics rerun on every page | **Refuted** | No proposed CPM-only regression |
| 6 | Inline HTML causes Jinja compile lag/O(N²) strings | **Refuted** | Maintainability only |
| 7 | Filter cache invalidation race | **Race refuted; recomputation cost real** | Low–Medium |
| 8 | SRA fixed-iteration Monte Carlo is expensive | **Valid, already partly mitigated** | High |
| 9 | MSPDI full-tree XML parsing has high peak memory | **Valid for large XML** | Medium–High |
| 10 | AI generation lacks streaming/cancellation | **Valid UX/resource issue** | Medium |

## Finding details

### 1. CPM O(N·E): refuted

`compute_cpm` builds predecessor and successor adjacency lists once. The forward pass visits each predecessor list, the backward pass visits each successor list, and free-float computation visits each successor list again. Across the complete network, those list lengths sum to E. The core pass is O(N+E), plus deterministic ready-node sorting.

The meaningful exception is summary-task logic lowering: a summary-to-summary relationship is expanded into a leaf cross-product. The solver remains O(N+E') after expansion, but E' can become very large. This is the real hotspot to benchmark and guard.

A synthetic control-flow benchmark equivalent to the adjacency passes measured approximately:

- 2,126 tasks / 2,702 links: 0.006 seconds
- 10,000 tasks / 50,000 links: 0.11 seconds

These are not full application benchmarks, but they disprove the stated O(N·E) control-flow model.

**Recommendation:** Do not cache dynamic link bounds. For repeated SRA solves, cache/compile only immutable topology, adjacency, summary lowering, and topological order.

### 2. Calendar holiday scanning: overstated

The code does not scan every calendar day. It uses full-week arithmetic, checks fewer than seven remainder days, then scans the holiday tuple. Complexity is O(H) per date-range conversion, not O(tasks × relationships × holidays). Relationship evaluation itself does not invoke the holiday scan.

A synthetic run of 2,000 date-range calculations against 500 holidays completed in approximately 0.066 seconds.

There is still a conditional optimization opportunity because tuple membership and range scans are linear in H.

**Recommendation:** Benchmark real large calendars. If measurable, retain sorted holidays and use `bisect`, plus a set for point membership. Do not add monthly bit arrays absent evidence.

### 3. Path tracing: partially valid

`ancestors_of` and `descendants_of` rebuild adjacency and traverse O(N+E) per call. However, the session’s scoped schedule is memoized, one global target is used, and no evidence supports CoPilot’s assertion that ten target traversals occur per page.

A synthetic ten-target run on a 2,126-task / 2,702-link DAG completed in approximately 0.008 seconds.

**Recommendation:** If profiling identifies repeated traces, cache the adjacency index by schedule identity. Do not cache all-pairs ancestor closures; that can require O(N²) memory.

### 4. Analysis cache: valid at scale

`SessionState.analyses` retains one full `_Analysis` per schedule key with no eviction. `_Analysis` includes CPM timings, audit objects, metrics, findings, narrative, and activity-row dictionaries. The design is lazy and summaries are separately cached, so CoPilot overstated immediate impact; nevertheless, a user who opens detailed analysis for many large versions can retain substantial memory.

The project’s own estimate is roughly 6 KiB per task. One hundred 2,126-task versions are approximately 1.22 GiB before uncertain additional object overhead.

**Recommendation:** Add a stdlib byte-budget or count-bounded LRU for full analyses and polished narratives. Keep parsed schedules and cheap summaries separate. Do not add `cachetools` because the runtime intentionally remains stdlib-only.

### 5. Full metrics rerun on every page: refuted

`_compute_analysis` performs one CPM pass and builds the full analysis once. `SessionState.analysis_for` identity-checks and reuses that object across page navigation. The portfolio path has a separate lazy summary tier and SQLite summary cache.

Some specialized multi-version views perform their own calculations per request, but CoPilot’s claim that every page reruns the full CPM/audit chain is incorrect.

**Recommendation:** Keep the current full-analysis cache. A “CPM-only cache” would increase repeated metric work. Consider lazy subcomponents only after measured profiling.

### 6. HTML/Jinja performance: refuted

The Jinja layout is instantiated at module import as one global `Template`; it is not parsed and compiled on every request. Inline f-strings are direct Python string construction, not Jinja compilation. Moving markup to template files may improve maintainability but does not establish a performance gain.

**Recommendation:** Do not perform a large template migration as a performance fix without profiling.

### 7. Filter invalidation race: refuted diagnosis

The cache and scope operations are protected by an `RLock`, specifically added after reproducing a concurrent filter/render failure. Clearing scoped analyses when the global filter or endpoint changes is correct because the task population and network can change for every schedule.

The cost is real: a new filter causes future accesses to recompute. The proposed “invalidate only affected schedules” is unsafe unless equivalence is proven.

**Recommendation:** First skip invalidation when the requested filter/target is unchanged. If toggling filters is a real workflow bottleneck, cache by `(schedule identity, scope signature)` behind an LRU.

### 8. SRA Monte Carlo: valid, but mitigation partly exists

The SRA executes a complete CPM solve for every iteration. Large schedules are already sent to a reusable worker process at 300+ tasks, preserving server responsiveness and exact seeded output. The worker is intentionally single-process; it prevents UI starvation but does not shorten the simulation.

Adaptive early stopping should not replace the fixed seeded mode because it changes the declared sample and reproducibility. It could be a separately labeled statistical mode.

**Higher-value optimizations:**

1. Compile immutable CPM topology once per SRA run and reuse it.
2. Precompute finish ranks once. Current sensitivity calculation re-sorts the identical finish vector for every activity.
3. Store sampled durations in compact arrays instead of Python integer lists.
4. Consider deterministic iteration-chunk parallelism only after profiling and byte-identical merge tests.

For 2,126 activities:

- 1,000 iterations store about 2.126 million duration samples.
- 10,000 iterations store about 21.26 million samples.
- Rough Python list+integer storage can approach 0.71 GiB at 10,000 iterations, versus about 0.08 GiB in 32-bit arrays.

### 9. MSPDI parser memory: valid

The path currently holds:

1. The complete file bytes.
2. A complete decoded Python string.
3. A complete ElementTree.
4. The final Pydantic object graph.

A synthetic 19.3 MiB XML document produced an approximately 88 MiB ElementTree parse peak under `tracemalloc`, excluding bytes/string allocations made before tracing. A 100 MiB document consuming several hundred MiB is plausible, although the exact 500 MiB claim was not measured.

**Recommendation:** Implement a hardened `iterparse` path that scans for DTD/entity declarations, incrementally clears elements, and preserves resource/assignment/calendar/task dependencies. Keep the existing parser as a fallback until parity is proven.

CoPilot’s other recommendations are weak:

- Python has no `list(capacity=n)` constructor.
- “Batch validating” Pydantic tasks is not demonstrated to reduce peak memory or CPU and does not avoid object construction.

### 10. AI timeout/cancellation: valid

The local backends send non-streaming requests. The browser uses ordinary `fetch` with no `AbortController`. The configured generation timeout defaults to 3,600 seconds, not two minutes.

One synchronous route thread waits for completion; this does not necessarily freeze the entire FastAPI server, but the user’s request remains blocked and the model may consume resources for up to an hour.

**Recommendation:** Add a cancellable generation-job API. Browser abort alone is insufficient because it may not terminate the server-side model request. Streaming is useful, but cancellation and server resource cleanup are the primary requirements. Preserve the operator-configurable long timeout rather than forcing 30 seconds.

## Significant issues CoPilot missed

### A. Multi-calendar CPM fidelity

The base CPM models one schedule-level contiguous calendar. Per-task calendars are honored only in specialized driving-slack logic. Therefore, CPM-derived dates, float, DCMA checks, paths, and risk metrics may not match Microsoft Project or P6 on multi-calendar or multi-shift schedules.

### B. Fail-soft calendar defaults can produce authoritative-looking wrong values

Calendar parsing can degrade to a standard 8-hour Monday–Friday calendar after structural surprises. The schedule still loads and affected metrics are not universally marked provisional or unsupported.

The importer should carry validity warnings into every affected metric.

### C. SRA sensitivity rank recomputation

For every activity, `_spearman` ranks both sampled durations and the same finish series. The finish ranks should be computed once and reused.

### D. SRA sample storage

The simulation stores every activity’s sampled duration for every iteration as Python integers. This becomes a substantial memory load at the allowed 10,000 iterations.

### E. Summary-logic edge explosion

Summary-task relationships are lowered to a leaf cross-product. A large summary-to-summary relationship can create a dense E' even when the source network is sparse.

### F. No dedicated performance regression gate found

The repository has extensive correctness, parity, security, and UI tests, but no identified benchmark gate for:

- Large-file import peak memory
- Large-network CPM latency
- 100-version detail-cache memory
- 1,000/10,000-iteration SRA latency and memory
- Filter toggle/recompute time
- AI cancellation behavior

## Metric and tool parity status

- **SSI:** Strong exact validation exists for specific files, settings, and focus UIDs. It is not universal SSI parity.
- **Acumen Fuse:** Many exported metrics are exact. Some rows remain recorded-golden only, and documented basis variants remain.
- **Microsoft Project:** Native and MSPDI behavior is strong for covered cases, but base CPM multi-calendar fidelity is incomplete.
- **Primavera P6:** Full parity is unsupported until replacement real-world XER files and corresponding P6 oracle exports/settings are supplied. The current synthetic XER fixture proves limited parser behavior only.

## Required action order

1. Add input-validity propagation for defaulted calendars, dropped links, unsupported calendars, and unstable cross-version identities.
2. Restore replacement XER files later and build a real P6 oracle suite.
3. Add a performance benchmark and memory-regression harness before broad optimization.
4. Optimize SRA finish-rank reuse, compact sample storage, and compiled CPM topology.
5. Implement streaming MSPDI parsing with parity and security tests.
6. Add byte-budget analysis-cache eviction.
7. Add cancellable AI jobs and optional streaming.
8. Optimize holiday/path indexing only if benchmarks show measurable benefit.
9. Do not rewrite CPM adjacency logic or HTML templates based on the CoPilot claims.

## Commands and evidence status

### Executed

- GitHub exact-SHA static inspection of relevant modules, tests, ADRs, state docs, and parity docs.
- Commit delta inspection.
- Recursive local ZIP extraction, SHA-256 deduplication, and structural Office/XML/PDF inventory.
- Synthetic control-flow and memory microbenchmarks described above.

### Not executed

- Full repository checkout.
- `ruff`, `mypy`, `pytest`, parity, coverage, Bandit, pip-audit, Node checks, installer tests, browser tests.
- Native executable profiling of the exact application.
- Live Microsoft Project, SSI, Acumen Fuse, or Primavera P6 runs.

The exact HEAD therefore cannot receive unconditional approval under the supplied audit standard.

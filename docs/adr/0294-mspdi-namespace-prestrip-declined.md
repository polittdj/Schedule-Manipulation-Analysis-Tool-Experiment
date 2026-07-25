# ADR-0294 — MSPDI importer profiled; the namespace pre-strip is DECLINED

- **Status:** Accepted (decision: do not implement)
- **Date:** 2026-07-25
- **Closes:** perf backlog item 6 of 7 ("importer profiling"), opened by ADR-0281
- **Related:** ADR-0249 (measure, don't hand-wave), ADR-0290 (a rename declined on the same
  cost/benefit grounds), ADR-0292 (order-dependent measurements lie), ADR-0293 (perf item 5)

## Context

Perf item 6 was "importer profiling". The profile is below; the decision is that **nothing in it
justifies changing the importer**, and this ADR exists so the next session does not re-derive it —
including one candidate that got as far as a working, Law-2-clean implementation before the
end-to-end measurement killed it.

### The profile

MSPDI, the committed 21.45 MB / 2,126-task / 433,254-element golden file. **Unprofiled medians** —
cProfile inflates this workload ~1.4× (it reports 2,721 ms where the real total is 1,410 ms) and
over-weights the many-small-calls helpers (`_text` fires 236,698 times), so it is useful for
*where*, never for *how much*.

| phase | ms | % |
| --- | --- | --- |
| `ET.fromstring` | **913** | **64.7%** |
| `_parse_task` ×2126 | 182 | 12.9% |
| unattributed (baselines, the pydantic `Schedule`, `_in_file_links`) | 179 | 12.7% |
| `_strip_namespaces` | 114 | 8.1% |
| `_build_links` | 15 | 1.1% |
| `_parse_assignments` | 5 | 0.4% |
| **TOTAL** | **1,410** | |

### Five hypotheses, all rejected

1. **Parse bytes instead of str** (the upload path decodes 21 MB and ElementTree re-encodes it) —
   `fromstring(bytes)` is **945 ms** vs `fromstring(str)` **894 ms**. *Slower.*
2. **Selective parsing** (drop subtrees we never read) — `Tasks` is **78.7%** of the DOM,
   `Assignments` 12.4%, `Calendars` 7.6%. There is no large discardable section, so the ceiling
   cannot justify rewriting a parity-critical importer.
3. **A per-Task `{tag: text}` map** replacing ~29 `Element.find()` linear scans — prototyped:
   **13.7 ms saved of 1,410 (1%)**, because `find` is already C and the dict build costs 21 ms.
4. **lxml** — 3–5× faster, but a binary dependency embedded in 9 installers, against the air-gap and
   packaging posture. Declined on ADR-0290's grounds.
5. **Pre-stripping the namespace** — implemented, measured, reverted. See below.

## The candidate that got built, and why it still lost

`_strip_namespaces` walks all 433,254 elements to undo a prefix that comes from a **single**
`xmlns` declaration (`text.count("xmlns")` is literally `1`). Removing that one declaration before
parsing makes the walk unnecessary, and the resulting tree is provably identical — unprefixed
*attributes* are never in a default namespace, so only tags were ever affected. A guarded
`_drop_sole_default_namespace()` was written (three preconditions: exactly one `xmlns` in the whole
document; it is a **default** declaration, not a prefixed one whose tags would lose their prefix;
and it sits in the `<Project` start tag), and it produced **byte-identical `Schedule`s**.

It was reverted anyway, because the components do not add up to a win:

| | ms |
| --- | --- |
| `fromstring` on a namespaced doc | 922.6 |
| `fromstring` on a plain doc | 915.4 |
| **parse-side saving** | **7.1** |
| `text.count("xmlns")` on 21 MB | 7.4 |
| rebuilding the 21 MB string without the 45-byte declaration | 52.9 |
| **new cost paid** | **60.3** |

ElementTree's namespace handling is **almost free** (7 ms) — the whole benefit had to come from
skipping the Python-level walk, and 60 ms of new work eats most of it. The end-to-end A/B on the
real `parse_mspdi_text`, fast path on vs forced off, interleaved:

- **wall-clock:** −28.7 ms (−1.8%) — inside the noise (samples ranged 1,503–4,989 ms);
- **CPU time:** median −55.5 ms (−3.6%), but **min-to-min −8.0 ms**.

When the median and the minimum disagree by 7×, the effect is allocator/GC state, not less work.

## Decision

Leave the importer alone. Ship no code for perf item 6.

Buying an unmeasurable few percent of one importer's time costs: a regex, a mutation of the
document text *before* it is parsed, a new branch, and a new correctness surface (zero-namespace,
multi-namespace, and prefixed-namespace documents) on the tool's **most parity-critical path**.
Law 2 says fidelity over speed; a change whose speed cannot be demonstrated is all risk.

## Consequences

- The five rejected hypotheses are recorded above **so nobody re-tries them**. Item 6 is closed as a
  decision, not as an omission.
- **The previous handoff was wrong and is corrected by this ADR.** It told the next session that the
  namespace pre-strip was "the ONE hypothesis that survived — 114 ms / 8.1%, implement it." That
  figure came from a phase timer *inside* the parse; the end-to-end A/B does not reproduce it. The
  component measurement was not wrong about `_strip_namespaces`' own cost — it was wrong about what
  removing it would buy, because it never priced the replacement work.
- **XER is deliberately unmeasured.** The only fixture is 2 KB (0.3 ms); profiling it would be
  theatre. A large real `.xer` is needed before that importer is touched. Recorded as a gap, not a
  result.
- If the importer ever does need to get faster, the profile says the only target worth the risk is
  the **65%** in `ET.fromstring` — which means a different parser, not a micro-optimisation.

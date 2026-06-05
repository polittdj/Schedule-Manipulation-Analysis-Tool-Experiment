# Reference intake manifest — Drive file IDs (Gate 1 deposit)

Verified present 2026-06-05 in the Google Drive folder **Schedule-Forensics — Reference
Intake** (`1kb24_-j73V5QSK2FC6FjjmsDvKW6SccV`, account `polittdj@gmail.com`). **27 files**
present (= the full screenshot set). Files are non-CUI (data-owner attestation, ADR-0003) and
git-ignored; pull from Drive by ID. `R` = readable via `read_file_content` (text);
`B` = binary/large → download bytes to disk and parse locally (do not base64 into context).

## Source schedules (§6.B native parse) — DEPOSITED 2026-06-05
| File | Drive ID | Size | Notes |
|---|---|---|---|
| Project2.mpp | `1qhrYLEMAAwapunbPdsRAlDn_AJHa7H_C` | 691 KB | modified 2026-05-24 (matches Project2 status date) |
| Project5.mpp | `1alUm2PePzAR9ylpadBjXw0GCQ5klhaBy` | 807 KB | the SSI/Acumen "Project5" target |

> The user's message said "Project2.mpp and **Project4**.mpp", but the folder contains
> **Project2.mpp + Project5.mpp** (no Project4) — treated as a typo; **Project5** is the correct
> target (all golden Acumen/SSI numbers are Project2-vs-Project5). Confirm if wrong.
> Binary (`B`): download bytes to disk and convert via the MPXJ runner (`java -cp
> tools/mpxj/classes:tools/mpxj/lib/* MpxjToMspdi <in.mpp> <out.xml>`) → MSPDI for the importer.

## Golden parity numbers — Acumen Fuse v8.11.0 ("Project 2-5"; Project2 vs Project5)
| File | Drive ID | RW |
|---|---|---|
| Project 2-5 Acumen - DCMA Report.xlsx | `1Hpd67ZUZaweGmZC1q0MHFNHoB2uk64pR` | R |
| Project 2-5 Acumen - Detailed Metric Report.xlsx | `16C23tnTy-Ff3HdugO8jMP9kcpiqSWTpQ` | R |
| Project 2-5 Acumen - Metric History Report.xlsx | `1OG4raH5XKsmOQjIn_IFXEXb-c54upqM9` | R |
| Project 2-5 Acumen - Schedule Quality.xlsx | `1TwBsgirdu6WQQTqonZiC3_u5qDiUGRUh` | R |
| Project 2-5 Acumen - Schedule Quality .xlsx (trailing space) | `1x8-i4PAkDpBkauTT8Vd7GZzuoMXQl0Kx` | R |
| Project 2-5 Acumen Logic Analysis Report.xlsx | `18VA8w0H0tPF3lAtoTrObfg3XjFk8pOJ_` | R |
| Project 2-5 Acumen- Schedule Quality.docx | `1NSJOK2YzO6PUFA5GlTDDZl59wLlePVO0` | R |
| …Perfomance and Change Metrics - Detailed Metric Report.xlsx | `1jnUTds0E1q0cmFwo3POvirCJY4qtNbuV` | R |
| …Perfomance and Change Metrics - Metric History Report.xlsx | `1F_aSvOTmMM_-22Bjbsijh4BvhmvdF2Ts` | R |
| …Perfomance and Change Metrics - Schedule Quality.xlsx | `1qEklywcGoIZ1Cj45ZzTML6pHmkYiB7-_` | R |
| …Perfomance and Change Metrics - Schedule Quality .xlsx (trailing space) | `1Pt30Z3CH2MvU2SzuDp5aYVPeszzmNprh` | R |
| …Perfomance and Change Metrics - Schedule Quality.docx | `1tWoL50K8pF8jwdCFR5j0BplaqH6Bw3qJ` | R |

## Golden parity numbers — SSI driving path (focus UID 143) → see SSI-DRIVING-SLACK.md (DONE)
| File | Drive ID | RW |
|---|---|---|
| SSI - All Dependencies - UID_143_Directional_Path_Analysis_…11.xlsx | `1m38WlBDnSchVwwQu5TnsPn-oIKKdqSGW` | R ✔ analyzed |
| SSI UID_143_Directional_Path_Analysis_…36.xlsx | `1Df94frFQBTCsmvqTRJirbcGzaqQbSN0N` | R ✔ analyzed |

## Metric library / formulas (primary sources for the metric catalog)
| File | Drive ID | RW |
|---|---|---|
| DeltekAcumen811MetricDevelopersGuide.pdf | `17b6FjNaLvHkoIvOoh2Xop6Q6ajYXZdQp` | R ← metric formulas |
| DeltekDECMMetricsOct2025.xlsx | `1zfMWfXctNwOEkRrDkwZZg2ohO-7HV27i` | R ← DCMA/DECM defs |
| DeltekAcumen811CostDataCsvStructure.pdf | `1D63YXrc7EQXuwwNob3f2hVoayJv4g5ZG` | R |
| metric library template.aft | `1np-hX1sJRRAWtKF0nMp2tZR69Y4BD4pq` | B (Acumen template) |
| NASA Metrics_Complete_20260423.aft | `1PUwnVyMue2qvw_o-rpHlRQ6OxT_qFVxe` | B (Acumen template) |

## Power BI reference (extra metrics + example visuals)
| File | Drive ID | RW |
|---|---|---|
| NSATDeploymentRevisionAlpha.pbix | `1g2mkXHr9MPnL0bqXmZiqKdAT88YdUyUG` | B (zip → unzip; read DataModel + Report/Layout) |
| Project5.fieldmap.xml | `1nQU7R2i6PbXOHRkNqL8s4dksOOfSKJY8` | R (field mapping) |

## Background references (handbooks / sample)
| File | Drive ID | RW |
|---|---|---|
| PerformanceAnalysisSummary_Sample Metrics_2026APR.xlsx | `1cnezz_szecUt3mcRRyBm4rFmoLapF83K` | R |
| DeltekAcumenPPMRiskGuide.pdf | `1thUQBtwX79qHBtzSP3Aqp1gR7yaf32Ka` | R |
| DeltekPPMEncryptionConversionUtilityGuide.pdf | `1Odq_dzeOfnEjixZTUAvcohP8oihcw0JW` | R |
| PPC-Handbook.pdf | `1nVk0DuHES0dwRMdn0yYled-HoPjbRG4E` | R (large) |
| schedule-management-handbook.pdf | `1v2AvqDNsrns_aalmHfSzvQkG0JKIu5YG` | R (27 MB — skim/targeted) |
| Joint Cost and Schedule Confidence Level Analysis.pdf | `1vhEH59Q0ggNLMhM2W-SIWm2zjDzCh7Lw` | R |

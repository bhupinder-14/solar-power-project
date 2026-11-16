# Phase C2.2 — Forecasting Data Readiness & Usable History Audit

## Executive verdict

**Decision: B — Partially ready; specific data issues need to be handled before broader EDA or a weather-informed baseline.** There are 749,288 complete paired inverter-target observations across the two acquired objects, kept as separate time blocks. The legacy timestamps are completely regular, and many uninterrupted usable segments exist: the longest spans 117.2 interval-days. A leakage-safe 15-minute-ahead experiment is feasible in principle.

The history is not continuous: the last complete legacy target is 2023-11-16 12:45 and the increment starts 2024-01-01 00:05, leaving 13,095 five-minute labels without a complete paired target. The increment also has 21 timestamp gaps and a long inverter-2 missing period. Weather measurements exist only in the increment, and several otherwise available sensors were flagged for stale or implausible values in the approved April audit. Thus, the data supports a target-only experiment more strongly than a cleared weather-informed feature set. Missing values and gaps must remain explicit.

No raw files, existing pilots, or project modules were modified. No interpolation, imputation, clipping, row removal, EDA, or model training was performed.

## Scope and calculation definitions

Only the approved local System 9068 source objects, existing April pilot outputs, manifests, and metadata were used. The target is the sum of the two primary AC-power channels **only when both are numeric**. Negative and zero values are retained.

Expected five-minute grids are computed separately between each object’s first and last observed timestamp. The increment’s first row is 2024-01-01 00:05 (not 00:00); its within-span expected grid therefore excludes the absent leading 00:00 label. The inter-object period is reported separately and is never joined into a segment.

For sample feasibility, a source label `t` is treated as the start of a five-minute interval. The issue time is `t+5` minutes, after that interval closes. The target interval begins 15 minutes after issue, at `t+20`, or row offset 4 from the latest observed interval label. A 24-hour input history means 288 consecutive five-minute observations ending at `t`. A candidate example requires all 288 historical target values, valid target labels at `t+5`, `t+10`, `t+15`, and `t+20`, and no crossing of a target gap. Weather inputs, where counted, must be present throughout the historical window and are never taken from future timestamps.

## 1. Target availability

| Period | Expected five-minute labels | Actual source rows | Missing source rows on grid | Numeric inverter 1 | Numeric inverter 2 | Complete paired target | Target missing on expected grid |
|---|---:|---:|---:|---:|---:|---:|---:|
| Legacy, 2017-08-23–2023-11-16 | 655,434 | 655,434 | 0 | 622,396 | 629,750 | 613,497 | 41,937 (6.40%) |
| Increment, 2024-01-01–2025-04-30 14:20 | 139,852 | 137,249 | 2,603 | 137,166 | 135,874 | 135,791 | 4,061 (2.90%) |
| **Object spans combined, not stitched** | **795,286** | **792,683** | **2,603** | **759,562** | **765,624** | **749,288** | **45,998 (5.78%)** |

For the increment, the 4,061 unavailable target labels comprise 2,603 timestamps with no source row plus 1,458 existing source rows with at least one null target channel. On existing rows alone, the increment target missingness is 1,458/137,249 = **1.06%**. The combined total row counts exclude the inter-object gap; they do not describe one continuous time series.

| Existing-row target nulls | Legacy | Increment |
|---|---:|---:|
| Inverter 1 null | 33,038 | 83 |
| Inverter 2 null | 25,684 | 1,375 |
| Both null on the same existing row | 16,785 | 0 |
| Only inverter 1 null | 16,253 | 83 |
| Only inverter 2 null | 8,899 | 1,375 |

The increment’s 2,603 missing timestamps are separate from these null values. On those absent-row labels both target channels are unavailable, but they are not rows containing two null cells.

## 2. Missingness and gap analysis

### Consecutive unavailable target periods

Durations in this table are counted as five minutes per missing expected-grid label. Counts use `>` each threshold.

| Period | Combined-target unavailable runs | Longest run | >15 min | >1 hour | >6 hours | >24 hours | >7 days |
|---|---:|---|---:|---:|---:|---:|---:|
| Legacy | 1,394 | 5,208 labels, 2022-03-16 05:30–2022-04-03 07:25 (about 18.1 days) | 220 | 84 | 56 | 34 | 3 |
| Increment | 58 | 705 missing labels, 2024-06-08 00:05–2024-06-10 10:45 (about 58.8 hours between observed boundaries) | 39 | 25 | 13 | 6 | 0 |

The longest null-only paired-target run on existing increment rows is 543 labels, **2024-09-17 12:50–2024-09-19 10:00** (about 45.25 hours of missing intervals). It is inverter-2-only missingness; the combined target remains missing throughout. In legacy, inverter 1’s longest null run is 5,208 labels from 2022-03-16 05:30 to 2022-04-03 07:25; inverter 2’s longest is 3,082 labels from 2021-07-30 18:00 to 2021-08-10 10:45. These are recorded measurement gaps, not rows to interpolate.

### Increment timestamp gaps

The increment has **21** adjacent observed timestamp intervals longer than five minutes, containing **2,603 omitted five-minute labels** by naive-grid arithmetic. The threshold counts below use the elapsed time between the previous and next observed row, not the count of missing grid labels: 19 gaps exceed 15 minutes, 19 exceed one hour, 10 exceed six hours, 3 exceed 24 hours, and none exceeds seven days. The 65-minute jumps on the two March clock-change dates could reflect local-time/DST behavior; source labels have no UTC offset, so that explanation is not confirmed.

| Previous observed timestamp | Next observed timestamp | Elapsed | Five-minute labels absent |
|---|---|---:|---:|
| 2024-03-10 01:55 | 2024-03-10 03:00 | 65 min | 12 |
| 2024-04-06 22:50 | 2024-04-08 09:10 | 34 h 20 min | 411 |
| 2024-04-24 05:25 | 2024-04-24 12:35 | 7 h 10 min | 85 |
| 2024-05-23 03:05 | 2024-05-23 13:40 | 10 h 35 min | 126 |
| 2024-05-24 06:05 | 2024-05-24 12:15 | 6 h 10 min | 73 |
| 2024-05-28 21:20 | 2024-05-29 11:40 | 14 h 20 min | 171 |
| 2024-06-08 00:00 | 2024-06-10 10:50 | 58 h 50 min | 705 |
| 2024-07-11 05:10 | 2024-07-11 16:40 | 11 h 30 min | 137 |
| 2024-09-11 18:35 | 2024-09-12 08:00 | 13 h 25 min | 160 |
| 2024-09-16 13:40 | 2024-09-16 15:50 | 2 h 10 min | 25 |
| 2024-09-19 10:20 | 2024-09-19 12:30 | 2 h 10 min | 25 |
| 2024-10-06 08:10 | 2024-10-07 08:25 | 24 h 15 min | 290 |
| 2024-10-15 07:30 | 2024-10-15 08:55 | 1 h 25 min | 16 |
| 2024-10-26 17:55 | 2024-10-26 19:00 | 65 min | 12 |
| 2025-02-10 10:50 | 2025-02-10 14:30 | 3 h 40 min | 43 |
| 2025-02-11 11:40 | 2025-02-11 11:55 | 15 min | 2 |
| 2025-02-14 09:45 | 2025-02-14 10:55 | 1 h 10 min | 13 |
| 2025-02-19 13:15 | 2025-02-19 17:00 | 3 h 45 min | 44 |
| 2025-03-09 01:55 | 2025-03-09 03:00 | 65 min | 12 |
| 2025-03-26 03:00 | 2025-03-26 03:10 | 10 min | 1 |
| 2025-03-29 02:55 | 2025-03-29 23:00 | 20 h 05 min | 240 |

Legacy has no missing timestamp labels or timestamp gaps within its first-to-last row span. Its missing target periods are rows with null target values. The distinct inter-object gap is **45 days, 11 hours, 20 minutes** from the last paired legacy value (2023-11-16 12:45) to the first paired increment value (2024-01-01 00:05), or **13,095** missing five-minute labels. It is not included in the within-object gap counts above.

## 3. Continuous valid target segments and lookback feasibility

Segments end whenever either inverter target is missing or an expected timestamp is absent. They are never joined across source objects or gaps. The inventory contains **1,394 legacy segments** and **59 increment segments** (1,453 total). Longest uninterrupted segment: **2018-07-02 12:55–2018-10-27 17:55**, 33,757 valid paired intervals (about 117.2 interval-days).

| Continuous lookback requirement | Legacy segments / valid observations within them | Increment segments / valid observations within them | 24h-aligned forecast samples, legacy | 24h-aligned forecast samples, increment | Samples total |
|---|---:|---:|---:|---:|---:|
| 24 hours (288 rows) | 171 / 587,259 | 31 / 134,047 | 537,498 | 125,026 | **662,524** |
| 7 days (2,016 rows) | 76 / 506,108 | 15 / 116,860 | 352,664 | 86,575 | **439,239** |
| 30 days (8,640 rows) | 21 / 277,533 | 4 / 62,753 | 96,030 | 28,181 | **124,211** |

These counts enforce a complete paired target lookback and a valid target horizon, including no target gap between issue and target. They are feasible issue/target examples, not a final training dataset. Samples include recorded zero and negative target values; none were filtered.

## 4. Forecast sample feasibility and chronological sample counts

With 24-hour target history, the target-only source periods provide **662,524** potential samples: 537,498 legacy and 125,026 increment. Requiring a recorded pad-2 raw POA value at every historical lookback timestamp reduces the increment availability count to **124,733** (293 fewer). Adding ambient temperature and the three other back-of-module temperature channels does not reduce that numerical availability count further, because their missing rows overlap existing target breaks in this calculation. Those sensors are nevertheless **not cleared as valid inputs** by this audit; the count is an availability-only diagnostic.

| Issue year / source block | Target-only, 24h lookback samples | Pad-2 POA historical-input availability samples |
|---|---:|---:|
| 2017 legacy (partial) | 30,485 | Not available |
| 2018 legacy | 100,122 | Not available |
| 2019 legacy | 99,069 | Not available |
| 2020 legacy | 71,731 | Not available |
| 2021 legacy | 69,549 | Not available |
| 2022 legacy | 94,052 | Not available |
| 2023 legacy (partial) | 72,490 | Not available |
| 2024 increment | 93,925 | 93,632 |
| 2025 increment through April 30 14:20 | 31,101 | 31,101 |

The candidate weather-informed count uses only past pad-2 POA at or before issue time; it never uses future observed irradiance. No numerical weather prediction forecast is present in the acquired data, so this would be a short-horizon observed-weather-input experiment, not a forecast-weather-input experiment.

## 5. Feature availability matrix

The legacy period has no acquired irradiance or environmental time series. The legacy AC object does contain meter and power-factor channels, but that is not a weather history. The following feature measurements overlap the 2024–2025 increment target by exact, timezone-naive timestamp label. First/last values are Jan 1 2024 00:05 and Apr 30 2025 14:15 for irradiance/environment sensors; the inverter target continues to 14:20.

| Feature / channel | Numeric observations / source rows | Missing on target source timestamps | Timestamp cadence in source | Availability and quality status |
|---|---:|---:|---|---|
| POA pad 1 raw and temperature-compensated (149723/149724) | 137,160 / 137,243 each | 0.065% | 5 min when present; 22 non-5-minute deltas in irradiance object | April audit flagged a 180-minute constant run; not cleared without sensor review. |
| POA pad 2 raw and temperature-compensated (149725/149726) | 135,867 / 137,243 each | 1.007% | 5 min when present; 22 non-5-minute deltas | No >60-minute constant run in April, but small negative dark-offset values and POA shading/tracker-stall representativeness concerns remain. Conditional candidate only. |
| Ambient temperature (149727) | 135,867 / 137,249 | 1.007% | 5 min when present; 21 non-5-minute deltas in environment object | Prior audit flagged a 125-minute constant run; not cleared as a valid feature without review. |
| Module temperature pad 1 sensors 1/2 (149728/149729) | 137,160 / 137,249 each | 0.065% | 5 min when present; 21 non-5-minute deltas | Prior audit flagged 115- and 90-minute constant runs; not cleared as valid inputs. |
| Module temperature pad 2 sensor 2 (149731) | 135,867 / 137,249 | 1.007% | 5 min when present; 21 non-5-minute deltas | Prior audit flagged a 120-minute constant run; not cleared as a valid input. |
| Module temperature pad 2 sensor 1 (149730) | 135,873 / 137,249 | 1.003% | 5 min when present; 21 non-5-minute deltas | Failed in April: 3,276.7 °C constant throughout the observed April span. Exclude pending independent evidence. |
| Revenue-meter AC power (150150; not a weather feature) | 123,872 / 123,872 | 9.803% | 5 min when present; 50 non-5-minute deltas in meter object | Sign and electrical boundary remain unresolved; availability only, not a cleared model feature. |
| Wind channels listed in metadata (149732–149738) | 0 | Unavailable | Not available | Absent from the approved environment CSV. No humidity or cloud-cover columns are present in that object. |

The environment object also has 80 inverter-module thermal channels and 8 inverter-level thermal/status temperature channels. They were not treated as weather features or approved inputs because they were not individually screened for quality here. The raw irradiance, temperature, meter, and target timestamp labels were matched exactly; no timezone localization was applied.

## 6. Chronological validation strategies

### A. Target-only historical baseline

Use only prior inverter target values and any time/calendar inputs available at issue time. Create chronological folds within contiguous segments; train on earlier blocks and validate on later blocks. The legacy period provides 537,498 24-hour-lookback examples, but weather covariates are not available there. The increment provides a later 125,026 target-only examples, but sits after the 45-day-plus gap and has internal breaks. It can serve as a later holdout only if any measurement-definition and distribution differences remain documented. Do not random-split overlapping time samples.

### B. Weather-informed experiment

Restrict to the increment’s exact target/weather timestamp overlap. A pad-2 POA-only 24-hour history has 124,733 availability-qualified candidate samples: 93,632 in 2024 and 31,101 in 2025 through April. Before use, review POA representativeness and approve sensor status; ambient and module temperatures remain flagged and should not be presumed valid. A defensible structure is an earlier contiguous block for fitting, a later block for validation, and the final contiguous block as out-of-time test. The broad 2024 versus 2025 split has these annual sample counts, but final dates should be selected only after checking monthly contiguous coverage and sensor acceptance. No exact split dates are set in this audit.

For either strategy, use only information available by issue time. In particular, do not use weather observations after issue time, and do not let lookback or target windows cross a missing-data segment. At the boundary of a chronological fold, historical observations before issue time may be used as they would be available in production; future labels/features must remain unseen.

## 7. Data acceptance assessment

1. **Target availability:** substantial usable data (749,288 paired rows over both object spans), but 5.78% target unavailability on the sum of within-object expected grids, plus a separate inter-object gap. Long channel outages require explicit treatment.
2. **Continuous segments:** sufficient for 24-hour, 7-day, and 30-day experiments; 202, 91, and 25 segments respectively meet those lengths.
3. **Historical gap:** manageable only when left as a break. There is no overlap to verify level continuity directly.
4. **Weather overlap:** 16 months of numerical overlap and more than 124,000 potential 24-hour target/POA samples, but the POA and temperature feature set is not yet fully quality-cleared. No future weather forecasts were acquired.
5. **Chronological test:** feasible in principle; annual sample counts are documented above. Final boundaries must respect contiguous target/weather availability.
6. **Remaining measurement uncertainty:** target remains combined measured inverter AC power; this audit does not establish gross plant generation/net export. Timezone/DST semantics, hardware continuity, possible long outages, and sensor quality remain documented risks.

**Milestone 1 readiness: B — Partially ready.** The target and usable continuous segments are sufficient for a carefully scoped baseline after explicit data-quality decisions. Weather-informed development should wait until the conditional POA feature and other candidate sensors receive a documented acceptance decision. This phase does not authorize the next implementation or modeling step.

## Outputs

- `ml/data/reports/pvdaq/9068/phase_c2_2/readiness_audit.json` — machine-readable availability, gap, segment, feature, sample, and decision results.
- `ml/data/reports/pvdaq/9068/phase_c2_2/target_segments.csv` — all contiguous paired-target segments, with source object and interval counts.
- `ml/data/reports/pvdaq/9068/phase_c2_2/missing_periods.csv` — consecutive missing periods by source-row gap, channel nulls, paired-target nulls, and target unavailability.
- `ml/data/reports/pvdaq/9068/phase_c2_2/increment_timestamp_gaps.csv` — exact previous/next timestamps and durations for all 21 increment gaps.
- `ml/data/reports/pvdaq/9068/phase_c2_2/feature_availability.csv` — per-channel feature coverage and quality status.
- `ml/data/reports/pvdaq/9068/phase_c2_2/annual_sample_availability.csv` — 24-hour target-only and candidate POA sample counts by issue year.
- `ml/data/reports/pvdaq/9068/phase_c2_2/audit_readiness.py` — reproducible local audit script.

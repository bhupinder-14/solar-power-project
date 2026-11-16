# Phase C2.1 — Legacy AC Data Acquisition & Historical Continuity Audit

## Executive verdict

**Historical target continuity: B — Partially supported, with specific unresolved gaps.** The legacy file contains the same primary inverter metric IDs and exact column names as the 2024–2025 increment, with the same apparent kW units and five-minute labels. Its entire observed timestamp sequence is uniformly five minutes and its ranges are broadly compatible with the later records. No obvious scale change is demonstrated.

The usable target is not a continuous record: there is a 45-day, 10-hour, 20-minute interval between the last nonmissing legacy target pair and the increment’s first observed target pair, with no overlapping timestamps. The legacy object also has 6.40% missing combined target rows, including multiweek one-channel dropouts; the increment has internal timestamp gaps and a separate multi-day channel dropout. A multi-day inverter-1 zero run in October 2023 is corroborated by a reduction in the meter and zero values in a similarly labeled additional AC channel, but its physical cause is not established. These periods must remain missing/flagged; no values were filled or removed.

**Recommendation:** The combined measured inverter AC-power target remains suitable as a candidate for a later forecasting-development phase if training/evaluation use explicitly segmented time ranges and only rows with both channels present. It is not a fully continuous 2017–2025 history, and this audit does not approve or begin model development.

## 1. Acquisition and integrity

- **Object:** `9068_ac_power_data.csv`
- **Exact URL:** [official OEDI object](https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/9068_OEDI/data/9068_ac_power_data.csv)
- Reconfirmed immediately before retrieval with HEAD: HTTP 200; 65,002,925 bytes; ETag `"63ab983741d1a8c2a4e275948179fb65-4"`; Last-Modified `Tue, 02 Jan 2024 17:12:56 GMT`; Content-Type `application/vnd.ms-excel`.
- Download began `2026-11-09T08:51:47.7729946+00:00` UTC. The download returned the complete 65,002,925-byte body.
- Local file size: 65,002,925 bytes, exactly matching preflight and remote Content-Length.
- SHA-256: `d0f7381abfaad9f53ae74fca7c6761aecbc344e595faf316406c3b081f0d1548`; this matches the S3 `x-amz-meta-sha256` value.
- The raw CSV was saved unchanged at `ml/data/raw/pvdaq/9068/source_objects/9068_ac_power_data.csv`. Provenance is in a new, separate file, `9068_ac_power_data_legacy_acquisition_manifest.json`; existing manifests were not overwritten.
- Only this approved time-series object was downloaded. No irradiance, environment, meter, or other-system objects were retrieved.

## 2. Schema and channel identification

The legacy CSV has 17 columns: `measured_on`; AC metrics 150135–150144; inverter power factors 150145 and 150146; and four meter fields (aggregate 150150 and phases 150151–150153). All eight additional channels 150135–150142 are present, as are the two primary target channels:

- `inverter_1_ac_power_(kw)_inv_150143`
- `inverter_2_ac_power_(kw)_inv_150144`

The 2024–2025 AC increment has 13 columns. Its 13 columns are an exact, same-order subset of the legacy header. The only legacy columns absent from the increment AC file are meter aggregate and three phase-meter channels; the increment acquisition separated meter data into its own approved meter object. There are no increment-only columns. Both use `measured_on` with labels formatted as `YYYY-MM-DD HH:MM:SS` and no timezone offset in the text.

The primary metric IDs, names, and apparent units are identical across the two headers (`AC POWER (kW)`). Official System 9068 metadata records them as AC power in kW, average aggregation, and source type INVERTER. Matching headers and static metadata support consistent channel definitions, but do not prove that hardware, wiring, firmware, or measurement boundaries stayed unchanged throughout the years.

## 3. Legacy data quality and cadence

| Measure | Result |
|---|---:|
| Source rows | 655,434 |
| First / last source timestamp | 2017-08-23 18:15 / 2023-11-16 13:40 |
| Timestamp parse failures | 0 |
| Duplicate timestamps | 0 |
| Out-of-order timestamps | 0 |
| Adjacent intervals | 655,433 of 655,433 are exactly 5 minutes |
| Missing timestamp-grid points within first/last labels | 0 |
| Off-grid timestamps | 0 |

The timestamp labels are perfectly regular in this legacy file. This is a statement about the labels only; their timezone and daylight-saving convention remain timezone-naive and unverified.

### Primary-channel and derived-target summary

The derived target is the sum only when **both** channels are present. Otherwise it remains missing.

| Series | Nonmissing / missing | Missing % | Negative | Zero | Min | Max | Mean | Median | P95 / P99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Inverter 1 (kW) | 622,396 / 33,038 | 5.04% | 13,583 | 317,557 | −44 | 1,928 | 487.85 | 0 | 1,828 / 1,845 |
| Inverter 2 (kW) | 629,750 / 25,684 | 3.92% | 14,195 | 322,626 | −45 | 1,907 | 478.14 | 0 | 1,823 / 1,842 |
| Combined, both inputs present (kW) | 613,497 / 41,937 | 6.40% | 21,775 | 301,604 | −81 | 3,791 | 965.11 | 0 | 3,640 / 3,680 |

Negative readings are retained and counted as measured values; they are not replaced with zero. Most zeros occur in long repeated runs, many of which are consistent with zero-output periods, but timestamps are not localized here and zero runs are not automatically classified as night. The distribution summary includes all valid signed values, not only daytime generation.

### Missing and constant-value runs

- Inverter 1’s longest missing run is 5,208 consecutive labels from **2022-03-16 05:30 through 2022-04-03 07:25** (about 18.1 days). Inverter 2 remains populated through this interval, but the combined target is missing because inverter 1 is missing.
- Inverter 2’s longest missing run is 3,082 labels from **2021-07-30 18:00 through 2021-08-10 10:45** (about 10.7 days). Inverter 1 remains populated; the combined target remains missing.
- Both target channels are missing in the final 11 legacy rows, from **2023-11-16 12:50 through 13:40**. Their last nonmissing values are at 12:45 (1,051 and 983 kW respectively). The 12:45 readings are numeric and within the observed range; no subsequent target values exist in the legacy object.
- Inverter 1 has a notable all-zero run from **2023-10-06 14:40 through 2023-10-12 10:45**, 1,682 consecutive five-minute rows. Inverter 1 was 1,562 kW at 14:35 just before the run, zero throughout it, −8 kW at 10:50 after it, and 1,534 kW at 10:55. Inverter 2 remained variable and around 1.35–1.46 MW in the sample window. The revenue meter drops from 2,910 kW to 1,406 kW when inverter 1 goes to zero and returns to 2,619 kW as inverter 1 returns; an additional channel labeled for inverter module group 1 is also zero. **Plausible:** this resembles an inverter-1-specific interruption more than a frozen entire-file feed. **Unresolved:** the cause and independence of the channels are not established; the readings are retained and not classified as invalid.
- Inverter 1 exceeds its documented 1,910 kW AC rating once: **1,928 kW at 2018-04-09 12:00** (18 kW above the metadata rating). Inverter 2 peaks at 1,907 kW. This single exceedance is a flag for review, not proof of an invalid measurement or a hard equipment limit. The largest paired combined value is 3,791 kW on 2019-03-14 11:25, below the sum of the two documented ratings.

### Year-by-year missingness

| Year | Rows | Inverter 1 missing | Inverter 2 missing |
|---:|---:|---:|---:|
| 2017 (partial) | 37,509 | 9.98% | 5.07% |
| 2018 | 105,120 | 1.35% | 0.83% |
| 2019 | 105,120 | 1.09% | 0.57% |
| 2020 (leap year) | 105,408 | 0.95% | 2.47% |
| 2021 | 105,120 | 6.73% | 9.64% |
| 2022 | 105,120 | 6.56% | 1.32% |
| 2023 (partial) | 92,037 | 12.78% | 8.89% |

The higher missingness in 2021–2023 and the prolonged single-channel dropouts indicate time-varying data completeness. They do not, by themselves, establish a sensor replacement or semantic change.

## 4. Legacy-to-increment transition

- **Last legacy source row:** 2023-11-16 13:40; both target fields are blank.
- **Last nonmissing value in either target channel:** 2023-11-16 12:45; both channel readings are present.
- **First increment row and first nonmissing target pair:** 2024-01-01 00:05; both values are zero.
- **Overlap:** none.
- From the last nonmissing legacy pair to the first increment pair: **45 days, 11 hours, 20 minutes**. There are **13,095 intervening five-minute labels** with no paired target observation. From the final legacy row label to the increment’s first label the difference is 45 days, 10 hours, 25 minutes.
- The static metadata’s reported last timestamp is 2023-11-16 13:45, five minutes later than the final legacy row label. Given the documented left interval marker, interval-boundary interpretation may explain the five-minute difference, but the CSV label itself ends at 13:40 and the last target measurements occur at 12:45. This is not evidence of target continuity after 12:45.
- The increment’s first timestamp is 00:05 despite a filename range beginning 2024-01-01. Its April 2025 slice is complete on a five-minute grid, from April 1 00:00 through April 30 14:20 (8,525 rows), matching the earlier pilot. Across the **whole increment**, however, there are 21 adjacent timestamp intervals longer than five minutes, corresponding to about **2,603 missing labels by naive five-minute-grid arithmetic**. The full increment has no duplicate or out-of-order labels. Two 65-minute jumps occur on the March daylight-saving transition dates in 2024 and 2025; these could reflect local-clock semantics, but timezone metadata does not resolve this. Other gaps range from 10 minutes to 2 days 10 hours 50 minutes and indicate absent source timestamps unless a documented clock convention explains them.

The gap is real in the available timestamp labels; it was not filled or interpolated. The final legacy target readings look like ordinary finite values before a trailing blank stretch; the increment begins with zeros. No overlapping period exists to directly test value agreement at the boundary.

## 5. Comparison with the 2024–2025 increment and April pilot

| Period | Rows | Inverter 1 missing | Inverter 2 missing | Combined missing | Combined negative / zero | Combined min / max kW | Combined mean / median kW |
|---|---:|---:|---:|---:|---:|---:|---:|
| Legacy 2017-08-23–2023-11-16 | 655,434 | 5.04% | 3.92% | 6.40% | 21,775 / 301,604 | −81 / 3,791 | 965.11 / 0 |
| Increment 2024-01-01–2025-04-30 14:20 | 137,249 | 0.06% | 1.00% | 1.06% | 1,561 / 71,599 | −50 / 3,798 | 894.51 / 0 |
| April 2025 slice | 8,525 | 0.04% | 0% | 0.04% | 117 / 4,058 | −35 / 3,513 | 1,052.17 / 47 |

The primary channels have similar measurement ranges and signed low-power behavior across the records. Legacy inverter 1’s maximum is slightly above its documented 1,910 kW rating; the later increment’s maximum for each primary channel is 1,904 kW. The combined legacy maximum is 3,791 kW versus 3,798 kW for the increment. Differences in means/medians and percentiles are not direct evidence of a scale change: the periods have different seasonal coverage and the overall medians are dominated by zero-output intervals. No normalization, clipping, or outlier exclusion was used.

The increment has a 543-row inverter-2 missing run, **2024-09-17 12:50 through 2024-09-19 10:00** (about 1.9 days), so its combined target is also missing there. Legacy per-channel missing periods are much longer, as listed above. In the increment’s April pilot, primary inverter 1 has three missing values and inverter 2 none, consistent with the previous pilot audit. Negative readings and zeros occur in both eras; no evidence here establishes a change in sign convention.

## 6. Measurement changes and remaining uncertainty

**Supported by the available files:**

- Both primary metric names/IDs and apparent kW units are unchanged between the legacy and increment headers.
- The legacy timestamp sequence is uniformly five-minute; there is no row-level cadence change within that legacy file.
- The legacy and increment have broadly compatible value ranges and both contain negative, zero, and missing readings.
- The legacy file includes meter aggregate/phase fields that are absent from the increment AC object; the increment’s meter data was delivered as a separate object.

**Not established:**

- Whether hardware was replaced, firmware/configuration changed, or wiring/measurement boundaries changed during 2017–2025. No such change is proven by the files inspected; lack of a record here is not proof that none occurred.
- Exact timezone/DST semantics of the timezone-naive labels. The increment’s two 65-minute spring jumps are suggestive but not conclusive; other internal gaps remain.
- Physical cause of the multi-day inverter-1 zero run and the multi-day missing intervals.
- Whether an apparent numerical compatibility implies identical measurement behavior for all historical years.

## 7. Target integrity and recommendation

The derived target remains:

`total_inverter_ac_power_kw = inverter_1_ac_power_kw + inverter_2_ac_power_kw`

It is present only when both source channel values are present. The eight additional AC channels were not summed. The target remains **combined measured inverter AC power**, not gross plant generation or net export.

**Continuity classification: B — Partially supported, with specific unresolved gaps.** There is no demonstrated metric-name/unit incompatibility, and the legacy five-minute timestamp grid is regular. But the paired target has a genuine 45-day-plus boundary gap, no overlap for direct validation, nontrivial missingness, and long channel-specific dropouts. The 2024–2025 increment itself has internal timestamp gaps.

**Suitability:** The System 9068 combined inverter-power series is a reasonable candidate for a later forecasting-development phase if gaps and missing targets are explicitly respected and analysis is restricted to contiguous usable segments. A continuous seven-plus-year target should not be claimed. Further approval is required before training or implementation work begins.

## Outputs

- `ml/data/raw/pvdaq/9068/source_objects/9068_ac_power_data.csv` — preserved legacy source CSV.
- `ml/data/raw/pvdaq/9068/source_objects/9068_ac_power_data_legacy_acquisition_manifest.json` — acquisition provenance and integrity evidence.
- `ml/data/reports/pvdaq/9068/phase_c2_1/legacy_primary_inverter_history.csv` — four-column target-only extraction, preserving timestamp and source value strings/order; combined target is blank if either channel is blank.
- `ml/data/reports/pvdaq/9068/phase_c2_1/historical_continuity_audit.json` — machine-readable schema, timestamp, data-quality, boundary, per-year, and channel-summary results.
- `ml/data/reports/pvdaq/9068/phase_c2_1/audit_legacy.py` — reproducible read-only audit script.
- `ml/data/reports/pvdaq/9068/phase_c2_1/phase_c2_1_report.md` — this report.

No cleaning, interpolation, clipping, timestamp shifting, row deletion, or model training was performed. The raw legacy CSV, increment, previous pilot datasets, and existing project modules were not modified.

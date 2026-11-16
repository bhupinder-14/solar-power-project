# Phase C2.4 — Target-Only Exploratory Data Analysis & Preprocessing Design

## Executive summary

This audit examined the measured target

`total_inverter_ac_power_kw = inverter_1_ac_power_(kw)_inv_150143 + inverter_2_ac_power_(kw)_inv_150144`

only when both inputs are numeric. Negative readings and zeros were retained. Legacy and increment were analyzed independently, and the statistical pooled summary is labeled as unstitched; no observation or feature crosses the source-object boundary.

The independently reconstructed paired-target counts match Phase C2.2 exactly: **613,497 legacy** and **135,791 increment**. The target has a large zero/low-output mass and strong short-term temporal dependence. Both source periods contain long valid segments sufficient for 15-minute forecasting with lookbacks from one hour to 30 days, but target gaps are common enough that examples must be constructed only inside continuous valid segments. The five-minute history-to-target alignment is feasible; no model was trained.

**C2.5 readiness: A — ready to begin a target-only baseline experiment after explicit approval.** Readiness is limited to a careful exploratory forecast experiment with strict gap-aware sampling. It does not mean the series is production-ready or that timing, timezone, meter boundary, or long-term equipment stability uncertainties are resolved.

## 1. Source periods and target construction

| Period | Source rows / expected grid | First label | Last label | Paired target values | Missing target on grid |
|---|---:|---|---|---:|---:|
| Legacy | 655,434 / 655,434 | 2017-08-23 18:15 | 2023-11-16 13:40 | 613,497 | 41,937 (6.40%) |
| Increment | 137,249 / 139,852 | 2024-01-01 00:05 | 2025-04-30 14:20 | 135,791 | 4,061 (2.90%) |

For every row, the derived target is the sum only if both inverter readings are numeric; otherwise it is missing. The independent maximum absolute calculation discrepancy against this definition is 0 kW. Source values were not changed. Missing target values in existing rows are 41,937 legacy and 1,458 increment. The increment also has 2,603 expected grid labels absent from the source object (21 timestamp gaps). These categories remain distinct.

The last legacy label to first increment label is **45 days, 10 hours, 25 minutes** apart (13,084 intervening five-minute labels). The objects are not joined across this boundary. The pooled statistic below simply summarizes the union of recorded valid values and does not imply continuous history.

## 2. Target statistics

Percentages use valid paired target observations for each period. Standard deviation is sample standard deviation. “Near zero” is defined descriptively as absolute target power ≤10 kW; it is not a physical validity threshold.

| Statistic | Legacy | Increment | Available values, pooled but unstitched |
|---|---:|---:|---:|
| Count | 613,497 | 135,791 | 749,288 |
| Mean (kW) | 965.11 | 894.51 | 952.32 |
| Median (kW) | 0.00 | 0.00 | 0.00 |
| Sample standard deviation (kW) | 1,355.34 | 1,274.41 | 1,341.31 |
| Minimum (kW) | −81 | −50 | −81 |
| P1 (kW) | −29 | −4 | −27 |
| P5 (kW) | 0 | 0 | 0 |
| P25 (kW) | 0 | 0 | 0 |
| P75 (kW) | 2,035 | 1,851 | 1,995 |
| P95 (kW) | 3,640 | 3,478.5 | 3,632 |
| P99 (kW) | 3,680 | 3,768 | 3,683 |
| Maximum (kW) | 3,791 | 3,798 | 3,798 |
| Negative | 21,775 (3.55%) | 1,561 (1.15%) | 23,336 (3.11%) |
| Exactly zero | 301,604 (49.16%) | 71,599 (52.73%) | 373,203 (49.81%) |
| Positive | 290,118 (47.29%) | 62,631 (46.12%) | 352,749 (47.08%) |
| Absolute value ≤10 kW | 310,195 (50.56%) | 72,756 (53.58%) | 382,951 (51.11%) |

The median is zero because nearly half of valid values are exactly zero, and another large share is low or negative. The full-range histograms therefore have a dominant zero bin; the positive-only panel makes variation during recorded positive production visible without discarding those values from the analysis. Box plots show all fliers; no values were excluded from the statistics or charts.

## 3. Distribution and temporal behavior

### Distribution plots

- [Target histograms, full range and positive-only](target_distribution_histograms.png): source periods are separate. The full-range view makes the zero mass clear; the positive-only view reveals the production distribution.
- [Target box plots](target_boxplots.png): legacy and increment shown separately with all fliers represented.
- [Negative and near-zero distributions](target_negative_near_zero.png): includes negatives, exact zeros, and positive values up to 10 kW, per the stated descriptive definition.

### Daily power and energy proxy

The daily file reports mean, minimum, maximum, valid interval count, expected interval count, coverage, and an observed-data energy proxy separately for every calendar-label day and source. A daily mean/max time series is plotted in [daily_power_by_period.png](daily_power_by_period.png); daily energy proxies are in [daily_energy_proxy.png](daily_energy_proxy.png).

Under the adopted convention that each source label *t* identifies the average power over `[t, t+5 min)`, a measured interval contributes `average kW × 5/60 hours`, or kWh. The daily proxy is the sum of those contributions only for observed valid paired intervals. It is **not** extrapolated over missing target intervals. Days at object boundaries and days with gaps can be partial; use the CSV coverage columns before interpreting a daily total.

### Hour, weekday, month, and low-output transitions

[Calendar pattern summaries](calendar_pattern_summaries.png) separate the two objects. Hourly median and mean profiles show a broad daily pattern with low values at some recorded hours and higher output around the recorded middle of day. The legacy mean is highest at recorded hour 12 (2,542 kW) and lowest at hour 0 (about −1 kW); the increment is highest at recorded hour 13 (2,375 kW) and lowest at hour 4 (about −0.02 kW). These are **timestamp-label hours**, not verified local solar time.

Monthly means peak in June for both sources (about 1,379 kW legacy and 1,448 kW increment) and are lowest in December (about 501 and 485 kW). Month-of-year summaries are separated by source and are available in `month_of_year_summary.csv`. The site metadata places the system in Kersey, Colorado, but timestamps remain timezone-naive and the authoritative time convention is unresolved. Therefore these are month-label patterns, not an assertion that a particular clock timezone or season convention has been established. Day-of-week medians are zero in all seven groups; the modest differences in means do not establish a weekly operating effect.

Using a descriptive low-output threshold of **≤50 kW** (not a night label), there were 2,818 transitions from low to above 50 kW and 2,798 in the reverse direction in legacy; increment had 621 and 616. Without verified timezone and sun position, these are low/production transitions rather than confirmed sunrise/sunset events.

## 4. Temporal dependence and rolling behavior

Autocorrelation was computed within contiguous valid five-minute target segments only. Each segment is demeaned independently before accumulating covariance; no pair crosses a missing value, omitted grid label, or object boundary.

| Lag | Legacy ACF | Increment ACF |
|---:|---:|---:|
| 5 min | 0.976 | 0.973 |
| 10 min | 0.962 | 0.957 |
| 15 min | 0.950 | 0.945 |
| 30 min | 0.916 | 0.912 |
| 60 min | 0.838 | 0.838 |
| 3 h | 0.484 | 0.485 |
| 6 h | −0.020 | −0.021 |
| 12 h | −0.540 | −0.563 |
| 24 h | 0.681 | 0.718 |

The high 5–60-minute autocorrelation supports testing short-lag persistence. The 24-hour recurrence supports a seasonal-naive comparison, while the negative 12-hour value is consistent with alternating high/low portions of a daily profile; none of these correlations establishes forecast skill. The large daily-lag correlation is descriptive and may be affected by timezone, daylight-saving, missingness, and period-specific operating behavior.

Partial autocorrelation was not computed because `statsmodels` is not installed in the existing environment. No package was installed for this phase. The ACF and the candidate lag/rolling design provide sufficient initial evidence; PACF can be added later if useful.

[Rolling target examples](rolling_target_example.png) show right-aligned rolling means and standard deviations over 15 minutes, 1 hour, and 24 hours on the beginning of each source’s longest uninterrupted valid segment. These are historical-only windows and stop at the latest closed interval. The underlying data are not reindexed across gaps for those examples.

## 5. Data quality, anomalies, and transitions

### Missingness and valid continuous segments

| Period | Valid segments | Longest valid segment | Segments ≥24 h / ≥7 d / ≥30 d | Longest missing run on expected grid |
|---|---:|---|---:|---|
| Legacy | 1,394 | 33,757 intervals (about 117.2 days), 2018-07-02 12:55 to 2018-10-27 17:55 | 171 / 76 / 21 | 5,208 intervals, 2022-03-16 05:30 to 2022-04-03 07:25 (18 days, 1 hour) |
| Increment | 59 | 25,568 intervals (about 88.8 days), 2024-11-13 16:05 to 2025-02-10 10:40 | 31 / 15 / 4 | 705 intervals, 2024-06-08 00:05 to 2024-06-10 10:45 (58 hours, 45 minutes) |

The legacy target’s 41,937 missing intervals all occur at existing source rows with at least one null channel; no five-minute timestamp labels are omitted in that source. Increment target missingness comprises 1,458 existing rows with a null channel plus 2,603 omitted grid labels from the 21 source timestamp gaps. The 21 gaps are recorded below; two one-hour clock-label jumps in March are compatible with daylight-saving transitions at the Colorado site, but timezone metadata is insufficient to classify them as genuine missing measurements or definitively as DST. Preserve the original labels and investigate before any timezone conversion.

| Previous label → next label | Elapsed label minutes | Omitted five-minute labels |
|---|---:|---:|
| 2024-03-10 01:55 → 03:00 | 65 | 12 |
| 2024-04-06 22:50 → 2024-04-08 09:10 | 2,060 | 411 |
| 2024-04-24 05:25 → 12:35 | 430 | 85 |
| 2024-05-23 03:05 → 13:40 | 635 | 126 |
| 2024-05-24 06:05 → 12:15 | 370 | 73 |
| 2024-05-28 21:20 → 2024-05-29 11:40 | 860 | 171 |
| 2024-06-08 00:00 → 2024-06-10 10:50 | 3,530 | 705 |
| 2024-07-11 05:10 → 16:40 | 690 | 137 |
| 2024-09-11 18:35 → 2024-09-12 08:00 | 805 | 160 |
| 2024-09-16 13:40 → 15:50 | 130 | 25 |
| 2024-09-19 10:20 → 12:30 | 130 | 25 |
| 2024-10-06 08:10 → 2024-10-07 08:25 | 1,455 | 290 |
| 2024-10-15 07:30 → 08:55 | 85 | 16 |
| 2024-10-26 17:55 → 19:00 | 65 | 12 |
| 2025-02-10 10:50 → 14:30 | 220 | 43 |
| 2025-02-11 11:40 → 11:55 | 15 | 2 |
| 2025-02-14 09:45 → 10:55 | 70 | 13 |
| 2025-02-19 13:15 → 17:00 | 225 | 44 |
| 2025-03-09 01:55 → 03:00 | 65 | 12 |
| 2025-03-26 03:00 → 03:10 | 10 | 1 |
| 2025-03-29 02:55 → 23:00 | 1,205 | 240 |

A single target-missing run may combine source-absent labels with adjacent null target rows; the separate machine-readable tables preserve exact missing-run ranges and source timestamp gaps. Never stitch any of these gaps or the 45-day inter-object discontinuity.

### Negative values, zeros, abrupt changes, and high readings

- Negative combined readings are confirmed values in the files: **21,775 legacy** (−81 to −1 kW) and **1,561 increment** (−50 to −1 kW). Preserve their sign. The recorded-label hour counts are concentrated in certain early/late hours, but these cannot be called nighttime without verified timezone semantics. Whether they represent auxiliary draw, meter/measurement behavior, or another physical condition remains outside this target-only analysis.
- Exact zeros are common: **301,604 legacy** and **71,599 increment**. There were 3,415 legacy zero runs and 648 increment zero runs; respectively 2,299 and 484 lasted at least one hour. The longest was 778 intervals (about 64.8 hours) in legacy and 196 intervals (about 16.3 hours) in increment. Long zeros may include normal no-production periods, outages, or data behavior; target-only measurements cannot distinguish those causes.
- Exact constant-value runs of at least one hour numbered 2,376 legacy and 486 increment, including zero runs. These are recorded behaviors, not automatically invalid observations.
- Five-minute target changes greater than 100 / 250 / 500 / 1,000 kW numbered **108,514 / 49,282 / 28,227 / 12,578** in legacy and **23,676 / 10,736 / 6,296 / 2,860** in increment. The largest adjacent changes were 3,736 and 3,558 kW; the 99th percentile absolute changes were 1,492 and 1,535 kW. Such changes may include start/stop transitions, cloud ramps, system behavior, or telemetry effects; they are not removed.
- The largest combined outputs were 3,791 kW legacy and 3,798 kW increment. Prior official equipment metadata documents two inverter records rated 1,910 kW AC each. No combined value exceeds their 3,820 kW summed nameplate reference. That reference is not proof of a hard operating ceiling or measurement validity.
- Distribution changed modestly between source objects: increment has a lower mean and negative rate, a somewhat higher P99, and similar maximum output. Coverage, period, missingness, or equipment/measurement changes could contribute. The available evidence does not establish a cause or confirm that equipment configuration remained unchanged.

Classifications: **confirmed** are recorded negative/zero readings, gaps, long missing and constant runs, and abrupt steps. **Suspicious but unexplained** are long negative or constant sequences and abrupt high ramps. **Valid recorded behavior with uncertain physical interpretation** includes zero and negative power; no observations were deleted or transformed.

## 6. Forecast alignment and leakage-safe sample rule

Adopt the previously reviewed interval convention: a source timestamp `t` labels the five-minute average over `[t, t+5 min)`. This is a working alignment convention from C2.2, while timezone and real-time reporting latency remain unresolved.

- The latest fully observed row has label `t` and closes at issue time `T = t + 5 min`.
- The forecast target interval begins 15 minutes after issue: `T + 15 min = t + 20 min`; its five-minute interval is `[t+20, t+25 min)`.
- It is row offset **+4** from the latest observed row.
- Inputs may include only values available by `T`, including the just-closed interval `y_t`. No future target values are features.
- For retrospective example eligibility, require a complete contiguous historical window and target/horizon alignment. The C2.2 convention also required paired target labels at offsets +1 through +4; those labels affect eligibility only, never the feature vector. Exclude examples with missing values, omitted labels, invalid timestamps, or any source discontinuity.

### Candidate lookback feasibility

Counts below are independently calculated separately for each source, requiring a fully valid historical target lookback plus paired target values through the +4 target label. No gaps are filled.

| History requirement | Legacy examples | Increment examples | Total, still unstitched |
|---|---:|---:|---:|
| 15 min (3 intervals) | 606,966 | 135,468 | 742,434 |
| 30 min (6) | 604,777 | 135,332 | 740,109 |
| 1 h (12) | 601,146 | 135,077 | 736,223 |
| 3 h (36) | 591,462 | 134,091 | 725,553 |
| 6 h (72) | 581,291 | 132,711 | 714,002 |
| 12 h (144) | 564,901 | 129,986 | 694,887 |
| 24 h trailing window (288) | 537,498 | 125,026 | 662,524 |
| Exact 24 h lag plus current value (289 rows) | 537,327 | 124,995 | 662,322 |
| 48 h (576) | 495,128 | 116,404 | 611,532 |
| 7 days (2,016) | 352,664 | 86,575 | 439,239 |
| 30 days (8,640) | 96,030 | 28,181 | 124,211 |

These are sample feasibility counts, not a constructed training set. They show that longer histories are computationally and statistically feasible, while 24 hours is a practical starting point. The exact 24-hour lag requires one additional historical point relative to a 288-interval trailing window; the distinction is recorded in the table and candidate specification.

## 7. Candidate target-only feature specification

Full specification is in [candidate_feature_specification.csv](candidate_feature_specification.csv). Suggested design for a first baseline feature table:

- **Persistence:** latest closed value `y_i` predicts the target; this is a baseline, not an engineered feature requirement.
- **Lags:** 5, 10, 15, 30, 60 minutes; 3, 6, 12, and 24 hours. Exact 24-hour lag is `y_(i−288)` and needs 289 points including the latest `y_i`.
- **Rolling means and standard deviations:** 15 min (3 values), 30 min (6), 1 h (12), 3 h (36), 6 h (72), 24 h (288). Right-aligned at the latest closed observation; require every value in the window. Do not use centered windows. Define the standard-deviation convention (`ddof`) once.
- **Calendar candidates:** recorded hour, weekday, day of year, and month. Timestamp timezone/DST is unresolved, so start without calendar features or treat recorded-label encodings as a documented ablation only. Never call these local-time features until the time zone is verified.

For a feature row at latest observed index `i`, all lag/rolling inputs are functions of `y_i` and earlier observations. The label is `y_(i+4)`. The future offsets +1 through +3 must never enter any feature computation.

## 8. Preprocessing and missing-data design (not implemented)

1. Keep raw source objects immutable; record source-object identity and period with every derived row.
2. Parse and retain original timestamp labels; report parse failures, duplicates, ordering, and off-grid timestamps. Do not silently resolve conflicts.
3. Build a separate five-minute analysis index **within each object only**. Represent absent timestamp labels as missing, distinct from existing rows with blank inverter values.
4. Construct target as a strict sum only where both inverter channels are numeric. Preserve negative and zero values; no clipping, fill, interpolation, or backfill.
5. Assign a continuity/segment identifier that breaks at any missing target, missing grid label, duplicate conflict, or source-object boundary.
6. Build lag/rolling features only within a single valid segment; require the full requested history. Exclude a sample if its target or required horizon/alignment is missing. Do not bridge short gaps or the 45-day inter-object gap.
7. Keep diagnostic flags (e.g. negative, long zero run, abrupt step) as annotations for review, never as automatic deletion rules.
8. Daily energy is an observed-interval proxy only. Report interval coverage and do not scale partial days to full-day estimates.

No preprocessing module or final training table was implemented in this phase.

## 9. Chronological validation proposal

Use chronological splits only. A defensible evaluation should report both:

1. **Within-period holdouts:** split the valid segments chronologically within legacy and within increment, preserving enough initial history for features and enforcing the +15-minute target alignment. This tests later observations under broadly similar acquisition sources; increment has only about 16 months and fewer samples.
2. **Cross-period transport check:** fit on an earlier legacy training window and evaluate on a later legacy holdout, then separately evaluate a model trained on legacy against a held-out increment window. This measures long-range and recent-period transfer, but the increment has a documented 45-day-plus gap from legacy and modest distribution changes.

Report legacy and increment metrics separately; never combine them into one continuous series. Do not use random splitting. Exact cutoff dates should be chosen in C2.5 after a split-specific sample-count and segment audit; the counts above are totals, not counts for proposed cut dates. At each split, ensure feature windows use only past data; purge examples whose target horizon crosses the split boundary.

## 10. Minimal baseline suite for C2.5

1. **Persistence — implement first.** Predict the target from the latest fully closed target value. It provides a strong, transparent short-horizon reference given ACF≈0.97 at five minutes.
2. **Seasonal-naive — implement second.** Use the value at the same recorded 24-hour lag, only when its complete history exists. It tests the measured daily recurrence without external features. Timezone/DST uncertainty must be stated.
3. **Simple statistical regression.** A regularized linear/Ridge regression on target lags and trailing summaries can determine whether several recent observations improve over persistence with clear, inspectable coefficients.
4. **One tree-based regression baseline, if the first baselines justify it.** A modest scikit-learn histogram gradient-boosting regressor on the same lag/rolling inputs can capture nonlinear ramps and output regimes. Keep it small, use chronological validation, and compare to the simple baselines before considering more complex methods.

Do not start with deep learning or advanced boosting. No model was trained in C2.4.

## 11. Remaining uncertainties

- Timezone and daylight-saving interpretation of naive timestamps.
- Confirmation that each interval label is an interval start and when its average becomes available operationally.
- Negative inverter-sum physical meaning and whether equipment/measurement definitions remained stable across the legacy and increment objects.
- Causes of increment timestamp gaps and long target null runs.
- Whether recorded zeros indicate darkness, equipment trips, curtailment, or another state.
- Historical and increment target distributions differ somewhat; the cause is not established.

## 12. Outputs

- [This report](phase_c2_4_report.md)
- [Machine-readable EDA summary](target_only_eda_summary.json)
- [Target statistics and source coverage](target_statistics.json)
- [Daily mean/min/max/coverage/energy proxy](daily_target_summary.csv)
- [Valid continuous target segments](valid_target_segments.csv)
- [Target-missing runs](target_missing_runs.csv)
- [Increment timestamp gaps and exact run diagnostics](target_only_eda_summary.json)
- [Lag/rolling/calendar candidate specification](candidate_feature_specification.csv)
- [Lookback sample feasibility](lookback_sample_feasibility.csv)
- [Autocorrelation values](target_autocorrelation.csv)
- [Partial autocorrelation availability](partial_autocorrelation_summary.json)
- [Negative runs](negative_target_runs.csv)
- [Zero runs](zero_target_runs.csv)
- [Constant runs lasting at least 60 minutes](constant_target_runs_ge60min.csv)
- [Daily power plot](daily_power_by_period.png)
- [Daily observed energy proxy plot](daily_energy_proxy.png)
- [Calendar profiles](calendar_pattern_summaries.png)
- [Rolling mean and standard-deviation examples](rolling_target_example.png)
- [Monthly target availability](monthly_target_availability.png)

The EDA script read only the approved local AC-power objects, independently verified target counts against C2.2, and wrote analysis outputs only into this Phase C2.4 directory. No raw/pilot data or existing modules were modified. No downloads, preprocessing pipeline, model evaluation, or training occurred.

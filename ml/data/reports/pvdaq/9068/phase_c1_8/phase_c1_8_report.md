# Phase C1.8 — AC Channel Mapping & Telemetry Diagnosis

## Executive verdict

**Decision: B — The combined primary inverter target remains the leading candidate, but the extra channels do not fully resolve the concerns.**

The eight added AC series have very strong descriptive relationships with the similarly numbered primary inverter channels. In the four observations flagged as inverter 1 zero, all four channels labeled `inverter_module_1.*` are also zero where observed, and are blank during the same three missing inverter 1 timestamps. On April 9, the meter falls with that group and recovers with it. On April 21, all eight added channels fall and rebound alongside both primary channels while the meter remains near 3.25 MW. These patterns make an isolated error in only the primary channel less likely.

However, the retained project metadata does not include the channel-level definitions or hardware IDs for metrics 150135–150142. The header labels and correlations are not enough to establish whether the channels are independent sensors, subchannels, or derived values. The telemetry investigation therefore cannot call these independent corroborating measurements or decide conclusively between actual inverter/plant behavior and a shared acquisition issue.

## Scope and files inspected

The investigation used only the four approved source objects, their existing April pilot/derived outputs, and acquisition manifests:

- `ml/data/raw/pvdaq/9068/source_objects/9068_ac_power_data_20240101_20250430.csv`
- `ml/data/raw/pvdaq/9068/source_objects/9068_meter_data_20240101_20250430.csv`
- `ml/data/raw/pvdaq/9068/source_objects/9068_irradiance_data_20240101_20250430.csv`
- `ml/data/raw/pvdaq/9068/source_objects/9068_environment_data_20240101_20250430.csv`
- `ml/data/processed/pvdaq/9068/pilot_2025-04_audited/pvdaq_9068_pilot_2025-04.csv`
- `ml/data/processed/pvdaq/9068/pilot_2025-04_inverter_validation/pvdaq_9068_pilot_2025-04_inverter_ac.csv`
- Existing `acquisition_manifest.json`, `ac_power_acquisition_manifest.json`, and C1.6/C1.7 reports.

The official System 9068 metadata URL is recorded in the acquisition manifest and was previously reviewed for the two primary inverter metrics. Its per-metric entries for 150135–150142 are **not present in the metadata snapshots/reports retained in the project**. An attempt to inspect the referenced JSON through the available public-documentation viewer was inaccessible. OEDI's public schema documentation was inspected; it defines the fields held in metric and hardware metadata but does not provide these eight system-specific values. [OEDI PVDAQ schema](https://github.com/openEDI/documentation/blob/main/pvdaq.md)

No new metadata file or time-series object was downloaded. All new outputs are under `ml/data/reports/pvdaq/9068/phase_c1_8/`.

## Metric mapping: confirmed evidence versus interpretation

The IDs and names below are confirmed from the downloaded AC CSV header. The metadata columns are unverified because the corresponding metric records were not available in the retained project metadata. The `inverter_module_1.*` and `inverter_module_2.*` group names are literal CSV labels, not a verified hardware map.

| Metric ID | Exact CSV column name | Confirmed metadata in retained project | Reasonable data-pattern interpretation | Unresolved mapping |
|---:|---|---|---|---|
| 150135 | `inverter_module_1.1_ac_power_(kw)_inv_150135` | Header name/ID; numeric series is present. Header text contains `(kw)` but no metric row is retained. | Strongly tracks primary inverter 1; likely belongs to the header-labeled group 1. | Description, official unit, aggregation, source type, hardware ID, physical scope, and independence. |
| 150136 | `inverter_module_1.2_ac_power_(kw)_inv_150136` | Same evidence as above. | Same group 1 pattern. | Same unresolved fields. |
| 150137 | `inverter_module_1.3_ac_power_(kw)_inv_150137` | Same evidence as above. | Same group 1 pattern. | Same unresolved fields. |
| 150138 | `inverter_module_1.4_ac_power_(kw)_inv_150138` | Same evidence as above. | Same group 1 pattern. | Same unresolved fields. |
| 150139 | `inverter_module_2.1_ac_power_(kw)_inv_150139` | Header name/ID; numeric series is present. Header text contains `(kw)` but no metric row is retained. | Strongly tracks primary inverter 2; likely belongs to the header-labeled group 2. | Description, official unit, aggregation, source type, hardware ID, physical scope, and independence. |
| 150140 | `inverter_module_2.2_ac_power_(kw)_inv_150140` | Same evidence as above. | Same group 2 pattern. | Same unresolved fields. |
| 150141 | `inverter_module_2.3_ac_power_(kw)_inv_150141` | Same evidence as above. | Same group 2 pattern. | Same unresolved fields. |
| 150142 | `inverter_module_2.4_ac_power_(kw)_inv_150142` | Same evidence as above. | Same group 2 pattern. | Same unresolved fields. |

No additional channel was summed with another channel or added to a target.

## April 2025 channel behavior

These are descriptive values from the CSV fields; the header suggests kW, but the additional metrics' official units were not verified.

- Metrics 150135–150138 each have 8,522 numeric April rows and the same three blank timestamps as primary inverter 1: April 2, 11:00, 11:05, and 11:10. Values are nonnegative, from 0 to 415.6–445.6; each has roughly 4,170–4,248 zero readings.
- Metrics 150139–150142 each have 8,525 numeric April rows, no blanks within the source rows, and values from 0 to 477.9–478.8. Each has 4,180–4,270 zero readings.
- All eight have zero negative readings. Long constant runs are zero-value periods at low POA. Their longest zero runs span about 13.5–14 hours; no inference about night time is made from the unverified source clock.
- Across the full April series, group 1 channels correlate 0.99949–0.99958 with primary inverter 1 and 0.99263–0.99284 with primary inverter 2. Group 2 channels correlate 0.99968–0.99974 with primary inverter 2 and 0.99258–0.99298 with primary inverter 1. Above POA 200 W/m², the matching-prefix correlations are about 0.9976–0.9980 and 0.9987–0.9990, respectively.
- At POA > 200 W/m², each added channel’s median value is about 0.252 times the correspondingly labeled primary channel. This supports a likely subordinate or partitioned relationship, but does not establish it. No sums or scale conversions were applied.
- The four group 1 channels’ zero/nonzero status matches primary inverter 1 on 97.8–98.7% of paired April rows; group 2 channels match primary inverter 2 on 98.0–99.1%. This agreement is descriptive and is not proof of independent measurement.

## Four high-irradiance inverter 1 zero events

### April 2, 10:50, 10:55, and 11:15

**Confirmed:** At each timestamp where primary inverter 1 reports zero, all four channels labeled `inverter_module_1.*` are also zero. At 11:00, 11:05, and 11:10, primary inverter 1 and those four channels are all blank. The four channels labeled `inverter_module_2.*` remain numeric and nonzero throughout these three blanks and the zero readings.

POA remains high rather than dropping to darkness: pad 2 is 680.68 W/m² at 10:50, 942.92 at 10:55, 1,070.25 and 1,126.00 at the two blank intervals, 644.28 at 11:10, and 892.28 at 11:15. Primary inverter 2 reads 1,415, 1,756, 1,890, 1,892, 1,160, and 1,615 in the six listed observed slots. The meter falls from 1,599 kW at 10:45 to 733 at 10:50, then ranges 601–974 through 11:10 and is 814 at 11:15. Its phase sum stays close to its aggregate value. At 11:20, primary inverter 1 and its four labeled group channels return to nonzero values; the meter rises to 2,516 kW.

**Plausible hypothesis:** A real inverter-1-specific output interruption is plausible: the four similarly labeled channels share the zeros/missing values, the other labeled group continues, POA is high, and the meter is reduced. A common telemetry/acquisition dropout affecting the primary and related channels remains possible because their hardware independence is not established. The observations do not prove an equipment outage.

### April 9, 08:10

**Confirmed:** Primary inverter 1 and all four group 1 channels are zero for one interval. Primary inverter 2 is 1,268; its four group 2 channels range 317.6–320.7. Meter power falls from 2,961 kW at 08:05 to 1,490 at 08:10, then rises to 3,200 at 08:15. Both POA sensors rise smoothly from about 756 to 775 to 798 W/m² across those intervals. Group 1 and primary inverter 1 recover at 08:15.

**Plausible hypothesis:** The one-interval event is consistent with a brief inverter-specific production interruption or a shared group 1 telemetry event. Because other AC channels may not be independent measurements, it is not possible to decide which. The meter’s partial reduction is supporting context, not proof of an outage.

## April 21, 16:00–17:00

**Confirmed:** At 16:35 both primary inverter readings fall (1,616→637 and 1,617→395 from 16:30), and all eight additional channels fall at the same timestamp. Group 1 channels change from approximately 407–409 to 121.9–206.6; group 2 channels from approximately 407–409 to 89.3–165.3. At 16:40, all eight additional channels and both primary channels return to their prior ranges. No channel is missing in this sequence.

At 16:35, pad 1/pad 2 POA are 647.70/221.54 W/m², down from 1,114.78/1,125.79 at 16:30 and back to about 1,086/1,088 at 16:40. The meter remains 3,245, 3,279, and 3,248 kW across these timestamps; its phase sum is 3,245, 3,261, and 3,222 kW.

**Assessment:** The event is not isolated to the two primary channel fields; all eight added AC series move with them. The simultaneous POA change makes a real short-lived output change plausible. But the meter does not show the same dip, and channel independence is unverified. This supports a common inverter-group/measurement event, not a definitive plant event diagnosis.

## April 6, 07:55–08:55

**Confirmed:** The added channels follow the two primary channels smoothly. At 08:25, primary inverter 1/2 are 1,637/1,592; the four group 1 fields are 409.1–410.9 and the four group 2 fields 397.1–399.6. At 08:35, primary inverter 1/2 are 1,664/1,665 and all eight added values are about 414–421. No missing or abrupt flatline appears in the additional channels.

The meter is 469 kW at 08:25 (phase sum 462) and 664 at 08:35 (phase sum 666), later rising to 2,688 at 08:55 (phase sum 2,697). POA changes during the window, with pad 1 rising earlier than pad 2.

**Assessment:** The extra channels support the recorded primary inverter pattern rather than the meter’s lower readings. This reduces the likelihood that only one primary field is erroneous, but because the added channels may be related or derived, it does not independently validate inverter output or explain the meter discrepancy.

## April 3, 04:30–07:00 negative sequence

**Confirmed:** From 04:50 to 06:40, primary inverter 1 is −6 at 23 consecutive timestamps; it is −5 at 06:45. Primary inverter 2 and all eight added AC fields are zero throughout the −6 sequence. The meter is approximately −7 to −10 kW over the sequence. POA is near zero through most of it; at 06:45 it rises to 11.56 W/m² on pad 2 and 18.94 on pad 1. The added fields remain zero at 06:45 while primary inverter 2 becomes −14 and the meter rises to 35 kW.

**Assessment:** The pattern is isolated to the signed nonzero value on primary inverter 1 among the reported AC fields. At low POA, this is consistent with a small signed residual or a difference in channel reporting behavior. It could also reflect telemetry behavior. No evidence makes the values demonstrably invalid, and no negative values were altered.

## Confirmed facts, hypotheses, and unresolved points

**Confirmed:**

- The source header contains eight distinct metrics 150135–150142 with the exact column names listed above.
- Their source-record availability, numeric ranges, zero counts, and event behavior are as reported.
- The three inverter 1 blanks are shared by the four group 1 fields; group 2 fields remain populated.
- All eight additional series drop and recover in the April 21 event; they remain smooth and aligned with primary inverter patterns on April 6.
- No additional channel is negative in April.

**Plausible hypotheses:**

- The header-labeled group 1 and group 2 channels are subordinate measurements associated with their similarly labeled primary inverters; the approximately quarter-scale ratios and very high correlations support this interpretation.
- The April 2 and April 9 zero events may be genuine inverter 1 output interruptions because group 1 channels and the meter also fall while POA stays high.
- The April 21 common drop may be a real short-lived output reduction associated with the POA transition.

**Unresolved:**

- Official descriptions, units, aggregation, source types, and populated hardware IDs for the eight metrics.
- Whether these are independent sensors, components, rollups, or derived values.
- Whether meter boundary or averaging semantics explain the mismatch.
- Whether the low-power negative readings reflect valid signed behavior or telemetry issues.
- Timezone/DST semantics remain unresolved for all source labels.

## Updated target recommendation and next step

Keep **combined primary inverter AC power** as the leading candidate, described only as combined measured inverter AC power. Do not add the eight channels to the target or call the combined primary reading verified gross generation or net export.

**A further targeted metadata validation is needed** to establish the eight metrics’ official records and hardware associations. The existing project metadata reference points to the System 9068 JSON, but the per-metric rows are not retained locally and the available viewer could not access that JSON. Retrieving or otherwise obtaining a copy of that static metadata would require separate approval under the current scope. No further data acquisition is requested in this phase.

**Decision: B.** The extra channels support the primary measurements descriptively but do not resolve whether they are independent or why the meter differs. Historical acquisition and model development remain out of scope.

## New outputs

- `targeted_event_windows.csv` — event windows with primary and all eight additional AC channels, meter aggregate and phase values, both POA sensors, ambient temperature, and usable module-temperature channels.
- `additional_metric_descriptive_summary.json` — numeric summaries and unverified-metadata flags for metrics 150135–150142.

References: [OEDI PVDAQ schema documentation](https://github.com/openEDI/documentation/blob/main/pvdaq.md); official metadata reference recorded in `ac_power_acquisition_manifest.json`.

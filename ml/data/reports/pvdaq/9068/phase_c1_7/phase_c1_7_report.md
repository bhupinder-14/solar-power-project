# Phase C1.7 — Meter/Inverter Discrepancy Investigation

## Executive verdict

**Decision: B — Combined inverter AC power remains the leading candidate, but further investigation is required before historical review.**

The April pilot confirms two separate, closely tracking inverter AC-power channels with five-minute labels and plausible ranges. It does not explain the large meter/inverter discrepancies. The revenue meter agrees closely with its three phase-power channels, while both inverter channels can move together in ways the meter does not. Some large divergences coincide with abrupt changes and disagreement between POA sensors. These findings leave meter boundary, transient telemetry quality, and channel interval semantics unresolved. No historical time-series data was acquired.

## Scope and files inspected

Only the existing System 9068 source objects, existing April pilot/derived outputs, manifests, and previously reviewed metadata/documentation were used:

- `ml/data/raw/pvdaq/9068/source_objects/9068_meter_data_20240101_20250430.csv`
- `ml/data/raw/pvdaq/9068/source_objects/9068_irradiance_data_20240101_20250430.csv`
- `ml/data/raw/pvdaq/9068/source_objects/9068_environment_data_20240101_20250430.csv`
- `ml/data/raw/pvdaq/9068/source_objects/9068_ac_power_data_20240101_20250430.csv`
- `ml/data/processed/pvdaq/9068/pilot_2025-04_audited/pvdaq_9068_pilot_2025-04.csv`
- `ml/data/processed/pvdaq/9068/pilot_2025-04_inverter_validation/pvdaq_9068_pilot_2025-04_inverter_ac.csv`
- Existing `acquisition_manifest.json`, `ac_power_acquisition_manifest.json`, and C1.6 audit JSON.

The new event-window table, all negative inverter observations, sequence inventory, and this report are saved only under `ml/data/reports/pvdaq/9068/phase_c1_7/`. Raw files and existing pilot datasets were not changed. No other source objects were retrieved.

## Extreme discrepancy events

Windows below include all five-minute labels from 30 minutes before through 30 minutes after the event(s). Meter phase-power channels are included as an internal-consistency check; they are not substituted for the meter total.

### April 6, 08:25 (window 07:55–08:55)

**Confirmed:** At 08:25 inverter 1 was 1,637 kW and inverter 2 was 1,592 kW (sum 3,229 kW); the revenue meter read 469 kW. The three meter phase values summed to 462 kW. Around this time the inverter sum rose smoothly from 2,412 kW at 07:55 to 3,329 kW at 08:35, while the meter rose from 364 kW to 664 kW over the same period, then reached 2,688 kW by 08:55. Meter phase sum closely followed the total meter channel throughout.

Both POA channels were around 450–560 W/m² near 08:25. Pad 1 later rose to 865 W/m² by 08:50 while pad 2 remained near 539 W/m²; by 08:55 they were about 855 and 775 W/m². The inverter channels had no missing values in this window and no flatline; ambient and usable module temperatures changed smoothly.

**Assessment:** The meter was not simply repeating a stale value; it ramped gradually. The changing POA readings may be relevant, but do not explain why the two AC measurement sources diverged by multiple megawatts. No abrupt timestamp gap or duplicate is present. A difference in boundary or telemetry/interval behavior is a **plausible hypothesis**, not a proven cause.

### April 21, 16:30 and 16:35 (covering 16:00–17:05)

**Confirmed:** At 16:30 the inverter sum was 3,233 kW, meter 3,245 kW, and meter phase sum 3,245 kW. At 16:35 inverter 1 fell from 1,616 to 637 kW and inverter 2 from 1,617 to 395 kW; their sum was 1,032 kW. The meter remained at 3,279 kW, with phase sum 3,261 kW. By 16:40 both inverter channels returned to approximately 1,600 kW each and the sum (3,229 kW) again nearly matched the meter (3,248 kW).

This is not a missing-row event. The channels have continuous five-minute timestamps. POA also changed sharply: at 16:30 pad 1/pad 2 were 1,115/1,126 W/m²; at 16:35 they were 648/222 W/m²; at 16:40 they were 1,086/1,088 W/m². The POA sensors therefore disagreed substantially at 16:35, although both fell from 16:30. At 16:20 the inverter sum was 1,149 kW while the meter was 3,247 kW; at 16:25 the sum and meter were 629 and 676 kW respectively.

**Assessment:** Abrupt irradiance changes could be associated with some inverter movement, but cannot explain the meter staying near 3.25 MW at 16:20 and 16:35 while the inverter sum fell. The simultaneous drop and recovery in both inverter channels is consistent with either a real plant event or a common telemetry/measurement issue. The available data cannot distinguish these.

## Other AC-power channels

The AC object header has eight additional columns with metric IDs 150135–150142, labeled in the CSV as `inverter_module_1.1` through `inverter_module_2.4` AC power. The retained acquisition manifest and C1.6 audit contain no per-metric metadata records for these eight IDs. OEDI’s general schema explains what metadata fields exist, but does not provide the specific descriptions, source type, aggregation, units, or populated hardware mapping for these channels. Because the required metric-level semantics could not be established from the approved metadata retained for this project, **none of these eight channels was used** to diagnose or reconcile the events. Their names alone are insufficient evidence that they are independent inverter outputs, module subgroups, or additive measurements.

## Meter phase-channel check

**Confirmed:** In the April meter object, the three phase AC-power channels sum to the aggregate meter channel within 93 kW maximum absolute difference across 8,525 paired records. Their mean phase-sum-minus-total difference is −0.18 kW, median is 0 kW, MAE is 9.21 kW, and 2,664 records match exactly. At the three selected event timestamps, phase sums were within 7, 0, and 18 kW of the aggregate meter reading, respectively (at 16:20 the difference was 35 kW).

This indicates that the aggregate meter values are broadly consistent with the same meter’s phase values in these examples. It does **not** establish where the meter sits electrically or prove its values are correct relative to inverter outputs.

## Quantitative comparison

Error is defined as **combined inverter sum − revenue-meter AC power**. All reported results use complete paired values, with no exclusions or transformations. Irradiance bands use pad 2 POA. One complete power pair had missing POA and is excluded from irradiance-band subsets. “Daytime” here is an operational label for POA > 50 W/m², not a timezone- or solar-position-derived classification. POA > 200 W/m² is a subset of that band.

| Paired subset | n | Pearson r | Mean error kW | Median error kW | MAE kW | RMSE kW |
|---|---:|---:|---:|---:|---:|---:|
| All complete pairs | 8,522 | 0.9900 | −57.64 | 9 | 101.96 | 209.36 |
| POA ≤ 50 W/m² | 4,362 | 0.8708 | 9.93 | 13 | 13.96 | 17.29 |
| POA > 50 W/m² (“daytime” definition) | 4,159 | 0.9722 | −128.50 | −115 | 194.25 | 299.16 |
| POA > 200 W/m² | 3,497 | 0.9500 | −135.47 | −127 | 212.49 | 321.15 |

| Subset | |error| > 100 kW | > 250 kW | > 500 kW | > 1,000 kW |
|---|---:|---:|---:|---:|
| All complete pairs | 2,531 (29.70%) | 933 (10.95%) | 243 (2.85%) | 47 (0.55%) |
| POA ≤ 50 W/m² | 5 (0.11%) | 1 (0.02%) | 0 | 0 |
| POA > 50 W/m² | 2,526 (60.74%) | 932 (22.41%) | 243 (5.84%) | 47 (1.13%) |
| POA > 200 W/m² | 2,294 (65.60%) | 920 (26.31%) | 239 (6.83%) | 46 (1.32%) |

All-complete-pair signed error percentiles (kW) are: minimum −2,247; 1st −600.16; 5th −346.95; 25th −112; median 9; 75th 13; 95th 14; 99th 692.27; maximum 2,760.

Extreme values disproportionately affect RMSE. The 86 largest absolute errors (top 1%, with cutoff 884 kW) account for 12.78% of absolute error and 43.98% of squared error. A diagnostic sensitivity calculation excluding only those 86 rows lowers RMSE from 209.36 to 157.50 kW and MAE from 101.96 to 89.83 kW. This is **not** the official result and does not classify those rows as invalid. The 47 intervals above 1,000 kW account for 34.82% of total squared error.

## Negative and suspicious inverter readings

**Confirmed from the source measurements:**

- Inverter 1 has 93 negative readings (range −24 to −1 kW), grouped into 51 consecutive negative episodes.
- Inverter 2 has 78 negative readings (range −22 to −1 kW), grouped into 50 episodes.
- At pad 2 POA > 50 W/m², there are 9 inverter 1 negatives and 7 inverter 2 negatives. Neither channel has a negative reading at POA > 200 W/m².
- Most negative readings occur at very low irradiance. Their repeated pattern is consistent with a small low-output signed reading, but no metadata establishes what negative inverter power physically represents.
- The requested inverter 1 run contains **23 consecutive −6 kW readings** from April 3 04:50 through 06:40; the next five-minute reading is −5 kW at 06:45. Thus the contiguous negative episode is 24 readings through 06:45. Pad 2 POA over the episode ranges from −1.87 to 11.56 W/m²; the meter ranges from −10 to 35 kW (median −8 kW). This is a repeated low-irradiance value, and a possible telemetry flatline, but it is not demonstrably invalid.
- Inverter 1 has four zero readings with POA > 200 W/m²: April 2 at 10:50, 10:55, and 11:15, and April 9 at 08:10. Inverter 2 is producing 1,268–1,756 kW at those timestamps, while the meter is 733–1,490 kW. These are possible inverter-specific outages or channel-quality events; the observations alone cannot distinguish them.
- The longest constant runs overall are zero-value periods of roughly 13 hours, with low POA. Inverter 1’s 23-sample −6 kW run is the longest nonzero constant sequence of concern.

No negative observation is classified as demonstrably invalid. Negative and zero measurements are retained. The separate `all_negative_inverter_observations.csv` and `negative_sequence_inventory.csv` provide all individual values and their matched irradiance/meter context.

## Measurement semantics and timestamp alignment

**Documented:** The meter metric is AC power from a revenue-grade meter; the two primary metrics are AC power from inverter sources. The reviewed System 9068 metadata marks inverter and meter intervals as left-aligned, and the channels have shared five-minute timestamp labels in April. OEDI documents `measured_on` as local instrumentation time that may involve DST in the standard schema; these prize CSVs use timezone-naive labels and do not provide a UTC offset.

**Unresolved:** The metadata does not establish the exact meter electrical boundary, flow sign, whether site/auxiliary loads are included, or a wiring/topology relationship between the meter and inverter outputs. A revenue meter could plausibly capture a different boundary or additional flows, but this is not proven. The same timestamp labels, five-minute grid, and left-alignment metadata support a direct label comparison; they do not prove common timezone interpretation or identical physical averaging windows. The zero-offset correlation maximum is not treated as proof of either.

## Historical compatibility — metadata only

**Confirmed:** The previously reviewed OEDI inventory lists the legacy System 9068 AC-power object `9068_ac_power_data.csv`. Static System 9068 metadata defines inverter metrics 150143 and 150144, and the 2024–2025 increment’s AC CSV contains those same metric IDs and names. The metadata definitions identify kW average AC power, while hardware records describe two inverters and left-aligned intervals.

**Unresolved:** The legacy time-series file was not downloaded or inspected, so its actual header, metric rows, units in file, cadence, missingness, and timestamps are unverified. The increment does not include a separate versioned metric/hardware-definition file in the approved objects. No reviewed change log documents a replacement or reconfiguration, but absence of a record is not proof that none occurred. The older metadata endpoint (2023-11-16 13:45) and increment start (2024-01-01) leave a potential coverage gap. Metric-ID continuity alone does not establish continuous, consistent historical measurements.

## Remaining uncertainties and target recommendation

The combined inverter series remains the leading candidate for a target described as **combined measured inverter AC power (kW)**. It should not yet be called verified gross plant generation or net export. The major unresolved issues are the large daytime disagreement with a meter that is internally consistent with its phase channels; the four high-POA zero readings on inverter 1; negative-value semantics; unavailable metadata for the eight additional AC channels; and historical timestamp/hardware continuity.

Historical POA and temperature measurements may be used as inputs only when observed by the forecast issue time. Future observations cannot be used as forecast features. This investigation did not change any data, train a model, or begin full EDA.

**Decision: B.** Further investigation is required before a separately authorized historical schema/continuity review. Full historical acquisition is not justified by this April-only investigation.

## References

- [OEDI PVDAQ schema documentation](https://github.com/openEDI/documentation/blob/main/pvdaq.md)
- [OEDI System 9068 metadata JSON](https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/9068_OEDI/metadata/9068_system_metadata.json)
- [OEDI 2025 Solar Data Prize change log](https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/change_log_2023_Solar_Data_Prize_20250627.pdf)
- [pvlib System 9068 example](https://pvlib-python.readthedocs.io/en/v0.15.2/gallery/system-models/oedi_9068.html)

# Phase C2.3 — Weather Sensor Quality & Feature Acceptance Audit

**System:** PVDAQ 9068 (SR_CO)  
**Scope:** Local approved source objects and existing local metadata only. No source objects were changed and no data were downloaded.

## 1. Executive verdict

**Decision B — weather channels remain conditional; target-only is the defensible initial feature scope.** The approved files contain a useful measured-irradiance candidate (Pad 2) and several plausible temperature channels, but their instrumentation/telemetry timing is not documented well enough to establish that a value labeled at time *t* is available at the forecast issue time. Sensor behavior also includes long plateaus, large Pad 1/Pad 2 disagreements, missing intervals and one failed module-temperature channel. No weather channel is classified **A. Acceptable for experimentation** at this point.

Pad 2 raw POA (149725) is the best candidate to revisit after the timestamp/availability convention is established. Do not average it with Pad 1 or use both raw and temperature-compensated versions as independent measurements. Ambient temperature (149727) and module temperatures 149728, 149729 and 149731 are conditional. Module temperature 149730 is rejected for the current experiment. This is a feature-screening conclusion, not a claim that the sensors are definitively defective.

## 2. Evidence and method

Inspected only the approved local irradiance and environmental CSVs, the existing System 9068 metadata JSON, prior pilot diagnostics, and acquisition records. The 2024–2025 objects contain 137,243 irradiance rows and 137,249 environmental rows. Their shared timestamp labels are timezone-naive; irradiance runs from **2024-01-01 00:05** to **2025-04-30 14:15**, while the environmental object ends at **2025-04-30 14:20**.

Both source streams are ordered, have no duplicate timestamps or off-grid timestamp labels, and are predominantly five-minute cadence. Irradiance has 22 non-five-minute adjacent timestamp gaps and 2,608 absent labels on its first-to-last five-minute grid; environment has 21 such gaps and 2,603 absent labels. These source-level gaps are distinct from blank channel values.

Official metadata describes the reviewed measurements as five-minute-resolution system data and identifies their aggregation as `avg`. It supplies channel names, common names, units, `source_type`, and scale/offset. The reviewed POA, ambient and module sensors have `source_type=OTHER` and null `source_id`; metadata has no separate description or sensor hardware mapping. The data do not document when each five-minute average is reported or whether its timestamp denotes interval start, interval end, or availability time. Therefore timing safety for live inference remains unresolved.

## 3. Complete channel inventory

The two approved source objects contain **97 measured channels**: 4 POA irradiance channels and 93 environmental channels. The environment file contains 1 ambient-temperature channel, 4 back-of-module thermocouples, 80 inverter-module temperature channels (IDs 149739–149818), and 8 inverter-level temperature/IGBT channels (IDs 149819–149826). The 88 inverter-temperature measurements are operational telemetry, not weather measurements, and were not accepted as weather features in this audit; their use would require a separate timing and leakage review.

All 97 observed channels, their exact headers and IDs, documented metadata fields, first/last numeric observations, counts, missingness, basic distributions, and timestamp-quality indicators are enumerated in the machine-readable inventory. The inventory explicitly records absent metadata mappings rather than filling them in.

Seven wind metrics are present in the system metadata but absent from both authorized source headers: 149732–149738 (wind speed/direction variants). They are not available as features in these objects. Humidity and cloud cover channels are also absent from the reviewed object headers.

Files:

- [Complete channel inventory CSV](environment_channel_inventory.csv)
- [Metadata-listed channels absent from the approved objects](metadata_environment_channels_absent.csv)

**Metadata facts:** The four POA channels are reported in W/m²; ambient and module channels in °C; reviewed environmental/irradiance metrics have aggregation `avg`. **Interpretation limits:** names such as “Pad 1” and “Pad 2” identify the documented sensor labels, but source IDs are null, so equipment mapping and independent calibration are not established by this metadata.

## 4. POA irradiance quality

The statistics below use all numeric measurements in each channel. Missingness is calculated against the complete five-minute grid spanning the union of the two source files (2024-01-01 00:05 through 2025-04-30 14:20; 139,852 labels). Night/darkness proxy is **either raw Pad 1 or raw Pad 2 >50 W/m²**; it is only a data-context classification, not a solar-position calculation.

| Channel | Numeric / grid labels | Missing | Min / median / mean / max (W/m²) | P1 / P5 / P95 / P99 | Negative / zero | Daylight proxy coverage |
|---|---:|---:|---|---|---:|---:|
| Pad 1 raw, 149723 | 137,160 / 139,852 | 1.925% | −6.23 / 0 / 238.11 / 1,510.13 | −2.45 / −2.05 / 957.67 / 1,055.21 | 66,961 / 5,527 | 61,145 of 61,226 labels (99.87%) |
| Pad 1 temperature-compensated, 149724 | 137,160 / 139,852 | 1.925% | −6.23 / 0 / 238.59 / 1,508.75 | −2.45 / −2.05 / 958.33 / 1,055.48 | 66,960 / 5,529 | 99.87% |
| Pad 2 raw, 149725 | 135,867 / 139,852 | 2.849% | −7.64 / 1.51 / 261.71 / 1,467.16 | −2.56 / −2.13 / 985.60 / 1,057.02 | 66,661 / 37 | 60,492 of 61,226 labels (98.80%) |
| Pad 2 temperature-compensated, 149726 | 135,867 / 139,852 | 2.849% | −7.63 / 1.52 / 262.37 / 1,466.92 | −2.57 / −2.13 / 988.31 / 1,059.45 | 66,661 / 38 | 98.80% |

The small negative POA values cluster around the dark/low-light range (the 1st and 5th percentiles are roughly −2 to −2.6 W/m²); they are retained as recorded and are not presumed invalid. Large step counts are not by themselves proof of sensor failure: cloud and tracker transitions can be real. On the five-minute grid, absolute changes greater than 200 W/m² occurred 3,803 times for Pad 1 raw and 5,020 times for Pad 2 raw; changes greater than 500 W/m² occurred 1,051 and 1,387 times respectively. These counts motivate contextual review and should not be treated as removed records.

Pad 1 has many long nonzero constant runs. The full-increment run inventory includes **298 channel/comparator run records** at least 60 minutes long across the raw and compensated POA variants (some records are paired views of the same underlying plateau). The known April 27 event is confirmed: Pad 1 raw was **659.2 W/m² for 37 consecutive five-minute samples from 15:30 to 18:30**; its compensated counterpart was 661.46 W/m² over the same interval. Pad 1 also held 681.08 W/m² from 12:50 to 15:25 (32 samples). During the 15:30–18:30 plateau, Pad 2 raw varied from 48.07 to 888.16 W/m². Other increment-wide plateaus include Pad 1 at 1165.76 W/m² on May 13, 2024 (25 samples, 120 minutes between labels), while Pad 2 varied by over 1,000 W/m² in that window. These are **confirmed disagreements/flat recordings**; cause (instrument, telemetry, local irradiance/shading, or other) is unresolved.

Daily and monthly numeric coverage for all four POA series is in [poa_daily_coverage.csv](poa_daily_coverage.csv) and [poa_monthly_coverage.csv](poa_monthly_coverage.csv). Plateau runs and contextual windows are in [poa_nonzero_plateau_runs_ge60min.csv](poa_nonzero_plateau_runs_ge60min.csv) and [poa_disagreement_windows.csv](poa_disagreement_windows.csv).

## 5. Pad 1 versus Pad 2

For 135,784 complete paired raw observations:

- Pearson correlation: **0.8905**; Spearman: **0.9566**.
- Pad 1 minus Pad 2: mean **−24.40 W/m²**, median **+0.04**, MAE **46.68**, RMSE **167.72**.
- Difference percentiles: P1 **−962.06**, P5 **−119.66**, P25 **−3.38**, P75 **+0.21**, P95 **+35.76**, P99 **+314.27 W/m²**.
- Absolute disagreement exceeded 50 W/m² in 15,523 pairs, 100 in 10,640, and 200 in 7,444.
- For Pad 2 >50 W/m², the Pad1/Pad2 ratio median was **0.985**, P5 **0**, P95 **1.248** (60,129 paired cases). The lower tail reflects times when Pad 1 was zero or much lower despite Pad 2 being illuminated.

Using the mean of the two readings to define descriptive bands (low ≤50, medium >50–800, high >800 W/m²), correlation is not uniform: low-band Pearson/Spearman 0.807/0.946; medium 0.436/0.494; high 0.513/0.692. In the medium band, mean difference is −71.57 W/m² and MAE 125.70 W/m². The high-band median difference is −11.48 W/m² and MAE 49.40 W/m². Large daylight discrepancies recur across the full increment, not only in the April plateau.

Within each pad, raw and temperature-compensated readings are nearly identical (Pad 1 r=0.999990, MAE 0.56 W/m²; Pad 2 r=0.999992, MAE 0.72 W/m²). They should be treated as near-duplicate versions, not independent sensor confirmation.

**Assessment:** Pad 2 raw is the strongest measured-irradiance candidate because it avoids Pad 1’s confirmed long nonzero plateau, but Pad 2 is not validated against an independent reference and has 2.85% grid missingness plus substantial abrupt transitions. **Pad 2 is conditional**, not fully accepted. Pad 1 and its compensated variant are **rejected for the initial experiment** because of repeated long plateaus and large contemporaneous divergence; this does not prove sensor defect.

## 6. Ambient temperature

Ambient channel 149727 has **135,867 numeric values** and 2.849% missingness on the combined expected grid. Range is **−35.0 to 38.4°C**; P1/P5/median/P95/P99 are **−19.1/−9.6/7.8/29.2/34.5°C**. Negative values are not inherently invalid for the documented Kersey, Colorado site. No independent weather station comparison is available in these objects. The longest exact flatline was **0.9°C from 2025-04-04 01:20 through 03:25** (26 records, 125 minutes). Across the increment there are 64 constant runs of at least 60 minutes; 22 adjacent five-minute changes exceed 5°C, 15 exceed 10°C and 5 exceed 20°C. Large steps merit checking, but are not automatically invalid without sensor cadence/rounding and local context.

**Assessment:** **Conditional.** Range and broad covariation are plausible, but a single unreferenced channel, prolonged repeated value, gaps and unknown reporting delay prevent unconditional acceptance.

## 7. Module temperature

| Channel | Numeric / grid labels | Missing | Min / median / mean / max °C | Longest exact constant run | Other evidence |
|---|---:|---:|---|---|---|
| Pad 1 back-of-module 1, 149728 | 137,160 / 139,852 | 1.925% | −38.4 / 10.4 / 13.90 / 70.0 | 113 records, 560 min, at 0.0°C (Nov 8–9, 2024) | r with ambient 0.860; with Pad 2 POA 0.816 |
| Pad 1 back-of-module 2, 149729 | 137,160 / 139,852 | 1.925% | −38.8 / 10.7 / 15.01 / 74.9 | 94 records, 465 min, at 0.0°C (Mar 29–30, 2025) | r with ambient 0.847; with Pad 2 POA 0.828 |
| Pad 2 back-of-module 1, 149730 | 135,873 / 139,852 | 2.845% | 0 / 3276.7 / 3276.36 / 3276.7 | 25,568 records, 127,835 min, at 3276.7°C (Nov 13, 2024–Feb 10, 2025) | P1–P99 all 3276.7; correlation with ambient 0.007 |
| Pad 2 back-of-module 2, 149731 | 135,867 / 139,852 | 2.849% | −39.0 / 9.6 / 13.69 / 68.4 | 58 records, 285 min, at 0.0°C (Nov 9, 2024) | r with ambient 0.862; with Pad 2 POA 0.814 |

The April pilot finding for 149730 is confirmed and persists: all **8,524 observed April pilot rows** were 3276.7°C; the full increment has 135,873 numeric observations, with the 3276.7°C value dominating the distribution and a long multi-month exact run. This channel is **rejected** as an input. The zero values outside that long run and their transitions are preserved; no value was repaired.

The other three module channels have plausible ranges and coherent broad relationships with ambient/irradiance, but each also has multi-hour zero flatlines and 336–603 five-minute changes greater than 5°C (depending on channel). They remain **conditional** until those runs/steps and actual reporting time are checked. Correlation is not proof of sensor accuracy.

## 8. Feature inventory and acceptance

| Candidate | Class | Evidence and permitted interpretation |
|---|---|---|
| Pad 1 raw POA 149723 | **REJECT** | Recurrent nonzero plateaus, including confirmed 37-sample April plateau; major daylight disagreements with Pad 2. Do not infer the sensor is definitively defective. |
| Pad 1 compensated POA 149724 | **REJECT** | Near-duplicate of Pad 1 raw; same plateau pattern, so compensation does not resolve issue. |
| Pad 2 raw POA 149725 | **CONDITIONAL** | Best candidate among measured POA channels; broad coverage, but no independent reference, missing intervals/disagreements and unresolved availability delay. |
| Pad 2 compensated POA 149726 | **CONDITIONAL** | Almost identical to raw Pad 2; do not use both as distinct inputs. No evidence it remedies source limitations. |
| Ambient 149727 | **CONDITIONAL** | Plausible overall range and broad coverage, but stale 125-minute run, substantial gaps and no corroborating station. |
| Module 149728 | **CONDITIONAL** | Plausible range and relationship, but 560-minute zero run and abrupt changes need scrutiny. |
| Module 149729 | **CONDITIONAL** | Plausible range and relationship, but 465-minute zero run and abrupt changes need scrutiny. |
| Module 149730 | **REJECT** | 3276.7°C across the entire observed April pilot and a long full-increment plateau; plainly unusable as Celsius module temperature. |
| Module 149731 | **CONDITIONAL** | Plausible range and relationship, but 285-minute zero run and abrupt changes need scrutiny. |
| Inverter thermal channels 149739–149826 (88 channels) | **Not accepted as weather features; separate review required** | Metadata calls these inverter temperatures, not weather. They may be equipment-state/operational telemetry. Their timing, relationship to target and prediction-time availability need separate assessment to avoid leakage. |
| Wind metrics 149732–149738 | **Unavailable** | Listed in metadata, absent from the approved source files. No values or features assessed. |

**Measurement versus forecast inputs:** All reviewed POA/temperature channels are measured historical observations, not weather forecasts. Metadata documents `avg` aggregation and five-minute system resolution, but no interval-label convention or reporting latency. No future measured weather is used in this audit. A measurement labeled at or after the issue time cannot be assumed available at issue time; the selected inputs require operational availability confirmation or an explicitly lagged, strictly past observation rule. There is no authorized weather forecast source here.

## 9. Weather-informed sample feasibility

C2.2 reported **662,524** target-only candidate samples with a 24-hour target lookback and 15-minute horizon. That remains the target-only availability baseline; it is not recomputed by this sensor audit.

No channels meet category A, so the sample count using **only accepted weather features is 0**. This means no weather-informed sample set is currently accepted for experimentation, not that the files have no usable measurements.

Conditional-only availability counts from C2.2 remain:

| Conditional feature set | Candidate samples before forecast-time availability/quality confirmation |
|---|---:|
| Pad 2 raw POA only | 124,733 |
| Pad 2 raw POA + ambient | 124,733 |
| Pad 2 raw POA + ambient + module 149728, 149729, 149731 | 124,733 |

These identical counts reflect the prior **availability mask** and do not certify measurement quality, reporting latency, or final feature acceptance. Do not present 124,733 as a validated weather-informed training count.

## 10. Remaining uncertainties and recommendation

**Confirmed:** local channel inventory and IDs; metadata units/average aggregation; source timestamp ranges, cadence gaps and duplicates; POA channel disagreement and plateaus; the April and multi-month 149730 flatline; ambient/module constant runs; missing metadata-listed wind metrics.

**Plausible, not proven:** Pad 1 plateaus may reflect telemetry or instrument behavior; Pad 2 may be a more reliable irradiance proxy than Pad 1; module/ambient broad relationships may reflect real thermal response. These are not sensor calibration findings.

**Unresolved:** sensor placement/calibration/independence; shading/tracker effects over the entire period; timezone interpretation beyond timezone-naive labels; interval start/end and timestamp meaning for these `avg` values; reporting delay and whether measurements are known at the forecast issue time; cause of source gaps, flatlines and steps; whether module channels’ zeros indicate sensor behavior or valid values.

**Milestone 1 feature scope recommendation:** Keep the approved target-only baseline separate. If weather features are later authorized, begin validation with **one** channel, Pad 2 raw POA, and then ambient as a separate conditional addition; do not combine Pad 1/Pad 2 by averaging or treat raw/compensated variants as independent. First establish exact timestamp/interval/reporting semantics and check selected channel runs in context. Do not use module 149730 or the absent wind channels.

## 11. Output files

- [This report](phase_c2_3_report.md)
- [Machine-readable audit summary](weather_sensor_quality_audit.json)
- [Audit script](audit_sensors.py)
- [Complete 97-channel inventory](environment_channel_inventory.csv)
- [Metadata channels absent from these objects](metadata_environment_channels_absent.csv)
- [Daily POA coverage](poa_daily_coverage.csv)
- [Monthly POA coverage](poa_monthly_coverage.csv)
- [POA plateau inventory](poa_nonzero_plateau_runs_ge60min.csv)
- [POA disagreement windows](poa_disagreement_windows.csv)

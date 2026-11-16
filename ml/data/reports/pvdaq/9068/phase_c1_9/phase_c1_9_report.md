# Phase C1.9 — Official System Metadata Retrieval & AC Metric Mapping

## Executive verdict

**CONFIRMED:** The official System 9068 metadata JSON documents metrics 150135–150144 as AC power in kW, with `aggregation_type=avg`, `source_type=INVERTER`, and no populated `source_id`. Metrics 150135–150142 have sensor names that explicitly say “Inverter Module”; IDs 150143 and 150144 are named “Inverter_1” and “Inverter_2”.

**UNRESOLVED:** Although metadata supports the interpretation that the eight additional series are inverter-module-level measurements, it does not populate their source IDs or hardware IDs, nor does it give a module-to-inverter hierarchy. It therefore does not prove that those channels map to the two documented inverter objects, are independent measurements, or form a complete/non-overlapping partition. Their values must not be added to the primary channels.

**Recommendation:** Retain the sum of primary metrics 150143 and 150144 as the leading candidate, named **combined measured inverter AC power**. Do not relabel it gross generation or net export. System 9068 is ready for a separately authorized historical schema/continuity review, but the metadata alone does not establish historical continuity or settle measurement independence.

## Acquisition and integrity evidence

- Authorized URL, matching the existing acquisition manifest: [official OEDI System 9068 metadata JSON](https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/9068_OEDI/metadata/9068_system_metadata.json)
- Retrieval began: `2026-11-09T08:41:47.791850+00:00` (UTC).
- HTTP HEAD and GET status: `200`.
- Remote `Content-Length`: 186,092 bytes; local size: 186,092 bytes.
- HTTP content type: `application/octet-stream` (generic S3 type); payload parsed successfully as JSON and contains `System.system_id=9068`, `public_name=SR_CO`.
- S3 Last-Modified: `Tue, 09 Jan 2024 16:13:17 GMT`; ETag: `"9063b8eae5788fc407613a13abd71479"`.
- SHA-256: `6861ae58145427dd790315257feef95b6ed5067fe5b5378dc5b2fa4acc23937f`.
- The downloaded file was preserved unchanged. No other object was retrieved. Provenance is recorded separately in `9068_system_metadata_acquisition_manifest.json`; no prior manifest was overwritten.

## Metadata structure and interpretation limits

The JSON has top-level sections `System`, `Site`, `Mount`, `Inverters`, `Modules`, `Meters`, `Other Instruments`, and `Metrics`. Its 438 metric entries are keyed by metric name. For the ten requested records, the available fields are `metric_id`, `sensor_name`, `common_name`, `raw_units`, `units`, `calc_scale`, `calc_offset`, `calc_details`, `aggregation_type`, `source_type`, `source_id`, `comments`, and `offline`.

There is no separate `description`, `hardware_id`, or `equipment_id` field on these metric records. `sensor_name` is the available descriptive text. Empty strings and nulls below are shown as unavailable rather than inferred. All ten records have `common_name=AC power`, `raw_units=kW`, `units=kW`, `calc_scale=1.0`, `calc_offset=0.0`, `calc_details=null`, `aggregation_type=avg`, `source_type=INVERTER`, `source_id=null`, `comments=""`, and `offline=false`.

## Complete metric mapping: IDs 150135–150144

| ID | Exact metadata key / source column suffix | `sensor_name` | Common name | Raw / reported units | Aggregation | Source type / source ID | Scale / offset | Calc details | Comments / offline | Hardware mapping |
|---:|---|---|---|---|---|---|---|---|---|---|
| 150135 | `inverter_module_1.1_ac_power_(kw)_inv_150135` | `Inverter Module_1.1_AC POWER (kW)` | AC power | kW / kW | avg | INVERTER / unavailable (null) | 1.0 / 0.0 | unavailable (null) | empty / false | unavailable |
| 150136 | `inverter_module_1.2_ac_power_(kw)_inv_150136` | `Inverter Module_1.2_AC POWER (kW)` | AC power | kW / kW | avg | INVERTER / unavailable (null) | 1.0 / 0.0 | unavailable (null) | empty / false | unavailable |
| 150137 | `inverter_module_1.3_ac_power_(kw)_inv_150137` | `Inverter Module_1.3_AC POWER (kW)` | AC power | kW / kW | avg | INVERTER / unavailable (null) | 1.0 / 0.0 | unavailable (null) | empty / false | unavailable |
| 150138 | `inverter_module_1.4_ac_power_(kw)_inv_150138` | `Inverter Module_1.4_AC POWER (kW)` | AC power | kW / kW | avg | INVERTER / unavailable (null) | 1.0 / 0.0 | unavailable (null) | empty / false | unavailable |
| 150139 | `inverter_module_2.1_ac_power_(kw)_inv_150139` | `Inverter Module_2.1_AC POWER (kW)` | AC power | kW / kW | avg | INVERTER / unavailable (null) | 1.0 / 0.0 | unavailable (null) | empty / false | unavailable |
| 150140 | `inverter_module_2.2_ac_power_(kw)_inv_150140` | `Inverter Module_2.2_AC POWER (kW)` | AC power | kW / kW | avg | INVERTER / unavailable (null) | 1.0 / 0.0 | unavailable (null) | empty / false | unavailable |
| 150141 | `inverter_module_2.3_ac_power_(kw)_inv_150141` | `Inverter Module_2.3_AC POWER (kW)` | AC power | kW / kW | avg | INVERTER / unavailable (null) | 1.0 / 0.0 | unavailable (null) | empty / false | unavailable |
| 150142 | `inverter_module_2.4_ac_power_(kw)_inv_150142` | `Inverter Module_2.4_AC POWER (kW)` | AC power | kW / kW | avg | INVERTER / unavailable (null) | 1.0 / 0.0 | unavailable (null) | empty / false | unavailable |
| 150143 | `inverter_1_ac_power_(kw)_inv_150143` | `Inverter_1_AC POWER (kW)` | AC power | kW / kW | avg | INVERTER / unavailable (null) | 1.0 / 0.0 | unavailable (null) | empty / false | unavailable at metric-record level |
| 150144 | `inverter_2_ac_power_(kw)_inv_150144` | `Inverter_2_AC POWER (kW)` | AC power | kW / kW | avg | INVERTER / unavailable (null) | 1.0 / 0.0 | unavailable (null) | empty / false | unavailable at metric-record level |

The exact metric keys shown above are the JSON metric names. The corresponding CSV headers match those names. No distinct metric description field exists in these records; the `sensor_name` is reproduced verbatim.

## Equipment information and hierarchy

| Documented equipment | ID | Name | Documented rating / details |
|---|---:|---|---|
| Inverter 0 | 29970 | `sco_inv_1` | AC capacity 1,910 kW; type `string`; quantity 1; manufacturer `Unknown`; model and serial unavailable; interval marker `L` |
| Inverter 1 | 29971 | `sco_inv_2` | AC capacity 1,910 kW; type `string`; quantity 1; manufacturer `Unknown`; model and serial unavailable; interval marker `L` |
| PV module entry | 55800 | `sco_mod_1` | Type CdTe; quantity 40,320; nameplate 117.5 W; `inverter_id="None"` (no inverter association) |
| Revenue meter | 3135 | `sco_mtr_1` | Type `revenue grade`; interval marker `L`; manufacturer `Unknown`; model and serial unavailable |

**CONFIRMED:** The system metadata documents two distinct inverter equipment records with different inverter IDs/names, each rated 1,910 kW AC. The system DC nameplate is 4,738 kW. Primary metric names distinguish inverter 1 and inverter 2.

**UNRESOLVED:** The metric records do not set `source_id` to 29970 or 29971. No equipment mapping links metric 150143 to inverter object 29970 or metric 150144 to object 29971, despite their names suggesting that correspondence. The “Inverter Module_1.x” and “Inverter Module_2.x” labels suggest grouping, but the equipment section has no inverter-module objects or parent-child links. The only `Modules` object is the PV module entry and its inverter association is explicitly the string `None`; it does not establish the meaning of “Inverter Module” in the metric labels.

Thus, distinct inverter equipment is documented, but the metadata does not itself prove that the two primary metrics are assigned to those different equipment IDs or that their coverage is non-overlapping. This is a plausible interpretation of the names, not a confirmed metric-to-hardware mapping.

## Reconciliation with Phase C1.8

Phase C1.8 reported:

- 150135–150138 correlate 0.99949–0.99958 with primary inverter 1; 150139–150142 correlate 0.99968–0.99974 with primary inverter 2.
- Above POA 200 W/m², the median additional-channel-to-matching-primary ratio is approximately 0.252.
- Matching groups share zero and blank periods; all ten channels drop together on April 21 at 16:35 and recover at 16:40.

**CONFIRMED:** Those are pilot-data findings from the already completed Phase C1.8 analysis; this phase did not change or recompute the pilot data.

**PLAUSIBLE:** The metric names and four-per-group pattern, together with the approximately quarter-scale values and near-perfect tracking, are consistent with the additional records being subordinate/module-level AC measurements associated with a larger inverter aggregate. Four components near one quarter of a parent value would be numerically compatible with that interpretation.

**UNRESOLVED:** Metadata does not define the “module” boundary, say that the four channels are exhaustive, provide their ratings, or state that their measurements are independent. The common `source_type=INVERTER` and null `source_id` for both additional and primary records do not resolve the hierarchy. Shared zero/blank intervals and the simultaneous April 21 drop can therefore reflect related equipment, shared telemetry, derived signals, or another common cause. Correlation and scale alone cannot distinguish these possibilities.

Do not sum IDs 150135–150142, and do not add them to IDs 150143/150144. Doing so could double-count measurements if the extra channels are subordinate or derived.

## Confirmed, plausible, and unresolved conclusions

### CONFIRMED

- One official metadata JSON was retrieved from the exact manifest-listed URL and validated as System 9068 / SR_CO.
- All ten metric entries identify AC power; use kW raw and reported units; use average aggregation; have source type `INVERTER`; have scale 1 and offset 0; and have null source IDs, empty comments, and `offline=false`.
- The eight additional names explicitly contain `Inverter Module_1.1` through `_1.4` and `Inverter Module_2.1` through `_2.4`; the primary names explicitly contain `Inverter_1` and `Inverter_2`.
- The system metadata documents two inverter equipment records, IDs 29970 and 29971, each with a 1,910 kW AC capacity.
- The records do not contain populated metric source IDs or hardware IDs, and do not establish module-to-inverter relationships.

### PLAUSIBLE

- The two primary AC metrics likely correspond by naming to the two documented inverter objects.
- The eight `Inverter Module` channels likely represent lower-level inverter-associated signals; the pilot scale and correlation patterns are consistent with that interpretation.

### UNRESOLVED

- Whether the eight channels are actual independent module/subsystem measurements, derived/duplicated signals, or a particular control-system reporting structure.
- Whether the four channels in each named group exhaustively partition their respective primary channel.
- Whether the two primary metric channels cover distinct, non-overlapping equipment boundaries.
- Whether pilot anomalies and common drops are physical events or common telemetry behavior.
- Historical continuity, hardware replacement/reconfiguration, and any changes in metric definitions remain unverified by this static metadata snapshot.

## Target recommendation and next decision

Keep **combined measured inverter AC power** (the Phase C1.6/C1.7 sum of primary channels 150143 and 150144) as the leading forecasting target candidate. The static metadata strengthens the case that these are average inverter AC power channels, but does not certify gross plant generation, meter export, independence, or historical continuity. No target was changed in this phase.

**Readiness:** System 9068 is ready for a separately authorized historical schema/continuity review as a candidate. That review should compare the legacy file’s actual headers and records and check for changes over time; the 2024–2025 metadata alone cannot establish continuity. This report does not authorize or perform that acquisition.

## Outputs

- `ml/data/reports/pvdaq/9068/phase_c1_9/phase_c1_9_report.md` — this report.
- `ml/data/raw/pvdaq/9068/metadata/9068_system_metadata.json` — unchanged official JSON.
- `ml/data/raw/pvdaq/9068/metadata/9068_system_metadata_acquisition_manifest.json` — separate provenance record.

Schema reference: [OEDI PVDAQ metadata documentation](https://github.com/openEDI/documentation/blob/main/pvdaq.md).

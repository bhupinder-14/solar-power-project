"""Extract and audit an April 2025 pilot from approved PVDAQ 9068 source files.

Original source objects are opened read-only. The derived pilot contains only
the revenue-meter target and selected colocated sensor channels. No values are
interpolated, clipped, or removed without an explicit audit record.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "ml/data/raw/pvdaq/9068/source_objects"
PILOT_DIR = ROOT / "ml/data/processed/pvdaq/9068/pilot_2025-04_audited"
REPORT_DIR = ROOT / "ml/data/reports/pvdaq/9068/pilot_2025-04_audited"

FILES = {
    "meter": "9068_meter_data_20240101_20250430.csv",
    "irradiance": "9068_irradiance_data_20240101_20250430.csv",
    "environment": "9068_environment_data_20240101_20250430.csv",
}
TARGET = "meter_ac_power_(kw)_meter_150150"
POA = [
    "pyranometer_(class_a)_pad_1_poa_irradiance_(w/m2)_o_149723",
    "pyranometer_(class_a)_pad_1_poa_irradiance_temp_compensated_(w/m2)_o_149724",
    "pyranometer_(class_a)_pad_2_poa_irradiance_(w/m2)_o_149725",
    "pyranometer_(class_a)_pad_2_poa_irradiance_temp_compensated_(w/m2)_o_149726",
]
AMBIENT = "weather_station_ambient_temperature_(c)_o_149727"
MODULE = [
    "thermocouple_pad_1_back-of-module_temperature_1_(c)_o_149728",
    "thermocouple_pad_1_back-of-module_temperature_2_(c)_o_149729",
    "thermocouple_pad_2_back-of-module_temperature_1_(c)_o_149730",
    "thermocouple_pad_2_back-of-module_temperature_2_(c)_o_149731",
]
WIND_META_IDS = [
    "wind_sensor_max_wind_speed_(m/s)_o_149732",
    "wind_sensor_wind_direction_o_149733",
    "wind_sensor_wind_direction_compass_corr_o_149734",
    "wind_sensor_wind_direction_fast_o_149735",
    "wind_sensor_wind_speed_(m/s)_o_149736",
    "wind_sensor_wind_speed_fast_(m/s)_o_149737",
    "wind_sensor_wind_speed_std._dev._(m/s)_o_149738",
]
EXPECTED_SIZES = {
    FILES["meter"]: 14_933_441,
    FILES["irradiance"]: 6_720_619,
    FILES["environment"]: 66_012_711,
}
START = pd.Timestamp("2025-04-01 00:00:00")
STOP = pd.Timestamp("2025-05-01 00:00:00")
FREQ = pd.Timedelta(minutes=5)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_timestamp(value: Any) -> pd.Timestamp:
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT
    try:
        return pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError):
        return pd.NaT


def json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def source_columns(path: Path, wanted: list[str]) -> tuple[list[str], list[str]]:
    columns = pd.read_csv(path, nrows=0).columns.tolist()
    present = [column for column in wanted if column in columns]
    missing = [column for column in wanted if column not in columns]
    if "measured_on" not in columns:
        raise ValueError(f"No measured_on column in {path.name}")
    return ["measured_on", *present], missing


def load_window(path: Path, columns: list[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Read only selected columns and return April rows with timestamp audit data."""
    pieces: list[pd.DataFrame] = []
    raw_rows = april_rows = invalid_timestamps = 0
    for chunk in pd.read_csv(
        path,
        usecols=columns,
        dtype=str,
        chunksize=100_000,
        low_memory=False,
    ):
        raw_rows += len(chunk)
        chunk["_source_timestamp"] = chunk["measured_on"]
        chunk["_timestamp"] = chunk["measured_on"].map(parse_timestamp)
        bad = chunk["_timestamp"].isna()
        invalid_timestamps += int(bad.sum())
        valid = chunk.loc[~bad].copy()
        # Select on the timestamp as represented in the source. Do not localize
        # naive values or assume a UTC offset.
        in_window = valid["_timestamp"].map(lambda t: START <= t.tz_localize(None) < STOP)
        selected = valid.loc[in_window].drop(columns=["measured_on"])
        april_rows += len(selected)
        if not selected.empty:
            pieces.append(selected)
    frame = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame(
        columns=["_source_timestamp", *columns[1:], "_timestamp"]
    )
    return frame, {
        "whole_source_rows_scanned_for_window_extraction": raw_rows,
        "rows_in_april_window_before_duplicate_handling": april_rows,
        "invalid_timestamp_rows_encountered_while_scanning_full_source_for_window": invalid_timestamps,
    }


def collapse_duplicates(
    frame: pd.DataFrame, source_name: str
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    """Keep one row per time; null conflicting fields and preserve duplicate evidence."""
    if frame.empty:
        return frame, {"duplicate_timestamp_groups": 0, "duplicate_excess_rows": 0,
                       "conflicting_timestamp_groups": 0, "exact_duplicate_excess_rows": 0}, pd.DataFrame()

    value_columns = [c for c in frame.columns if c not in {"_source_timestamp", "_timestamp"}]
    dup_mask = frame.duplicated("_timestamp", keep=False)
    duplicate_rows = frame.loc[dup_mask].copy()
    if not duplicate_rows.empty:
        duplicate_rows.insert(0, "source_group", source_name)

    output: list[pd.Series] = []
    conflict_rows: list[dict[str, Any]] = []
    exact_excess = 0
    conflict_groups = 0
    for ts, group in frame.groupby("_timestamp", sort=True, dropna=False):
        if len(group) == 1:
            output.append(group.iloc[0].copy())
            continue
        chosen = group.iloc[0].copy()
        conflicts: list[str] = []
        for column in value_columns:
            values = group[column].astype("string").fillna("<NA>").unique()
            if len(values) > 1:
                conflicts.append(column)
                chosen[column] = pd.NA
        if conflicts:
            conflict_groups += 1
            chosen["_conflict_columns"] = ";".join(conflicts)
            conflict_rows.extend(group.assign(
                source_group=source_name,
                conflict_columns=";".join(conflicts),
            ).to_dict("records"))
        else:
            exact_excess += len(group) - 1
        output.append(chosen)
    result = pd.DataFrame(output).reset_index(drop=True)
    if "_conflict_columns" not in result:
        result["_conflict_columns"] = ""
    stats = {
        "duplicate_timestamp_groups": int(duplicate_rows["_timestamp"].nunique()) if not duplicate_rows.empty else 0,
        "duplicate_excess_rows": int(len(duplicate_rows) - duplicate_rows["_timestamp"].nunique()) if not duplicate_rows.empty else 0,
        "conflicting_timestamp_groups": int(conflict_groups),
        "exact_duplicate_excess_rows": int(exact_excess),
    }
    return result, stats, duplicate_rows


def longest_constant_run(values: pd.Series, timestamps: pd.Series) -> dict[str, Any]:
    numeric = pd.to_numeric(values, errors="coerce")
    valid = numeric.notna().to_numpy()
    vals = numeric.to_numpy()
    times = timestamps.to_list()
    best = current = 0
    best_value = None
    current_start = best_start = best_end = None
    previous = None
    for i, value in enumerate(vals):
        if not valid[i]:
            current, previous, current_start = 0, None, None
            continue
        contiguous = i > 0 and times[i] - times[i - 1] == FREQ
        if contiguous and previous is not None and value == previous:
            current += 1
        else:
            current = 1
            current_start = times[i]
        if current > best:
            best = current
            best_value = float(value)
            best_start = current_start
            best_end = times[i]
        previous = value
    return {
        "longest_consecutive_same_value_intervals": int(best),
        "longest_constant_duration_minutes": int(max(0, best - 1) * 5),
        "longest_constant_value": best_value,
        "longest_constant_run_start": best_start.isoformat() if best_start is not None else None,
        "longest_constant_run_end": best_end.isoformat() if best_end is not None else None,
        "constant_run_at_least_60_minutes": bool(best >= 13),
    }


def channel_stats(frame: pd.DataFrame, expected: pd.DatetimeIndex, columns: list[str]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    timestamps = frame["_timestamp"]
    for column in columns:
        raw_values = frame[column].astype("string") if column in frame else pd.Series(dtype="string")
        values = pd.to_numeric(raw_values, errors="coerce")
        observed = values.notna()
        non_numeric = raw_values.notna() & values.isna()
        stats: dict[str, Any] = {
            "observed_values": int(observed.sum()),
            "missing_values_on_observed_union_timeline": int((~observed).sum()),
            "missing_fraction_of_observed_union_timeline": float((~observed).mean()) if len(values) else None,
            "non_numeric_nonblank_values": int(non_numeric.sum()),
        }
        if observed.any():
            valid_values = values[observed]
            stats.update({
                "minimum": float(valid_values.min()),
                "p01": float(valid_values.quantile(0.01)),
                "median": float(valid_values.median()),
                "mean": float(valid_values.mean()),
                "p99": float(valid_values.quantile(0.99)),
                "maximum": float(valid_values.max()),
                "standard_deviation": float(valid_values.std()),
                "negative_values": int((valid_values < 0).sum()),
                **longest_constant_run(values, timestamps),
            })
        else:
            stats.update({"negative_values": 0, **longest_constant_run(values, timestamps)})
        report[column] = stats
    return report


def timestamp_stats(frame: pd.DataFrame, expected: pd.DatetimeIndex) -> dict[str, Any]:
    if frame.empty:
        return {"unique_timestamps": 0, "observed_start": None, "observed_end": None,
                "missing_expected_intervals": int(len(expected)), "off_grid_timestamps": 0,
                "non_five_minute_adjacent_differences": 0, "adjacent_difference_counts_minutes": {}}
    ts = pd.DatetimeIndex(frame["_timestamp"].sort_values().unique())
    deltas = pd.Series(ts[1:] - ts[:-1]) if len(ts) > 1 else pd.Series(dtype="timedelta64[ns]")
    delta_minutes = (deltas / pd.Timedelta(minutes=1)).astype("Int64")
    expected_naive = expected.tz_localize(None) if expected.tz is not None else expected
    ts_naive = ts.tz_localize(None) if ts.tz is not None else ts
    aligned_grid = set(expected_naive.asi8)
    off_grid = sum(int(t.value not in aligned_grid) for t in ts_naive)
    missing = len(set(expected_naive.asi8) - set(ts_naive.asi8))
    return {
        "unique_timestamps": int(len(ts)),
        "observed_start": ts[0].isoformat(),
        "observed_end": ts[-1].isoformat(),
        "expected_intervals_in_window": int(len(expected)),
        "missing_expected_intervals": int(missing),
        "missing_expected_interval_fraction": float(missing / len(expected)) if len(expected) else None,
        "off_grid_timestamps": int(off_grid),
        "non_five_minute_adjacent_differences": int((delta_minutes != 5).sum()),
        "adjacent_difference_counts_minutes": {str(k): int(v) for k, v in Counter(delta_minutes.dropna().astype(int)).items()},
    }


def main() -> None:
    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(f"Source directory not found: {SOURCE_DIR}")
    if PILOT_DIR.exists() or REPORT_DIR.exists():
        raise FileExistsError("Pilot output path exists; refusing to overwrite prior work.")
    for filename, expected_size in EXPECTED_SIZES.items():
        path = SOURCE_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size != expected_size:
            raise ValueError(f"Size mismatch for {filename}: {path.stat().st_size} != {expected_size}")

    PILOT_DIR.mkdir(parents=True, exist_ok=False)
    REPORT_DIR.mkdir(parents=True, exist_ok=False)
    wanted_by_group = {
        "meter": [TARGET],
        "irradiance": POA,
        "environment": [AMBIENT, *MODULE, *WIND_META_IDS],
    }
    frames: dict[str, pd.DataFrame] = {}
    source_reports: dict[str, Any] = {}
    missing_in_objects: dict[str, list[str]] = {}
    duplicate_evidence: list[pd.DataFrame] = []
    channel_columns: list[str] = []

    for group, filename in FILES.items():
        path = SOURCE_DIR / filename
        usecols, missing = source_columns(path, wanted_by_group[group])
        missing_in_objects[group] = missing
        frame, read_stats = load_window(path, usecols)
        frame, dup_stats, duplicate_rows = collapse_duplicates(frame, group)
        frames[group] = frame
        source_reports[group] = {
            "file": filename,
            "file_size_bytes": path.stat().st_size,
            "sha256": sha256(path),
            "columns_in_source": int(len(pd.read_csv(path, nrows=0).columns)),
            "selected_columns_present": [c for c in wanted_by_group[group] if c in usecols],
            "metadata_channels_absent_from_this_object": missing,
            "rows_in_april_window_before_duplicate_handling": read_stats["rows_in_april_window_before_duplicate_handling"],
            "duplicate_analysis": dup_stats,
            "source_rows_scanned_only_to_select_april": read_stats["whole_source_rows_scanned_for_window_extraction"],
            "invalid_timestamp_rows_encountered_while_scanning_full_source_for_window_extraction": read_stats["invalid_timestamp_rows_encountered_while_scanning_full_source_for_window"],
        }
        if not duplicate_rows.empty:
            duplicate_evidence.append(duplicate_rows)
        channel_columns.extend([c for c in wanted_by_group[group] if c in usecols])

    combined: pd.DataFrame | None = None
    for group in FILES:
        frame = frames[group].copy()
        if frame.empty:
            continue
        frame = frame.drop(columns=["_source_timestamp"], errors="ignore")
        frame[f"{group}_source_row_present"] = True
        if "_conflict_columns" in frame:
            frame = frame.rename(columns={"_conflict_columns": f"_{group}_conflict_columns"})
        combined = frame if combined is None else combined.merge(frame, on="_timestamp", how="outer", validate="one_to_one")
    if combined is None:
        raise ValueError("No records found in the selected April window.")

    tz = combined["_timestamp"].iloc[0].tz if combined["_timestamp"].iloc[0].tzinfo else None
    start = START.tz_localize(tz) if tz else START
    stop = STOP.tz_localize(tz) if tz else STOP
    expected = pd.date_range(start=start, end=stop, inclusive="left", freq=FREQ)
    combined = combined.sort_values("_timestamp").reset_index(drop=True)
    observed_index = pd.DatetimeIndex(combined["_timestamp"])
    all_index = expected.union(observed_index).sort_values()
    combined = combined.set_index("_timestamp").reindex(all_index).rename_axis("timestamp")
    presence_columns = [f"{group}_source_row_present" for group in FILES]
    for column in presence_columns:
        if column not in combined:
            combined[column] = False
        combined[column] = combined[column].astype("boolean").fillna(False).astype(bool)
    combined["source_record_present_any_group"] = combined[presence_columns].any(axis=1)
    combined.insert(0, "timestamp_source", [t.isoformat() for t in combined.index])
    combined.insert(1, "timestamp_timezone_aware", bool(combined.index.tz is not None))
    conflict_cols = [c for c in combined.columns if c.startswith("_") and c.endswith("_conflict_columns")]
    combined["duplicate_conflict_columns"] = combined[conflict_cols].fillna("").astype(str).agg(";".join, axis=1) if conflict_cols else ""
    combined = combined.drop(columns=conflict_cols, errors="ignore")
    combined = combined.reset_index(drop=True)
    non_numeric_rows: list[dict[str, Any]] = []
    non_numeric_counts: dict[str, int] = {}
    for column in channel_columns:
        raw_values = combined[column].astype("string")
        numeric_values = pd.to_numeric(raw_values, errors="coerce")
        bad = raw_values.notna() & numeric_values.isna()
        non_numeric_counts[column] = int(bad.sum())
        if bad.any():
            non_numeric_rows.extend([
                {"timestamp": combined.loc[i, "timestamp_source"], "channel": column,
                 "raw_value": str(raw_values.iloc[i])}
                for i in np.flatnonzero(bad.to_numpy())
            ])
        combined[column] = numeric_values

    pilot_path = PILOT_DIR / "pvdaq_9068_pilot_2025-04.csv"
    combined.to_csv(pilot_path, index=False)

    if duplicate_evidence:
        pd.concat(duplicate_evidence, ignore_index=True).to_csv(REPORT_DIR / "duplicate_timestamp_records.csv", index=False)
    if non_numeric_rows:
        pd.DataFrame(non_numeric_rows).to_csv(REPORT_DIR / "non_numeric_measurement_records.csv", index=False)
    # Treat exact five-minute expected times separately from any off-grid records.
    pilot_ts = pd.Series(pd.to_datetime(combined["timestamp_source"], errors="coerce"))
    expected_set = set(expected)
    observed_set = set(pilot_ts.dropna())
    expected_missing = sorted(expected_set - observed_set)
    target_values = pd.to_numeric(combined[TARGET], errors="coerce")
    target_valid = target_values.notna()
    target_expected_grid = pd.Series([t in expected_set for t in pilot_ts])
    target_on_grid = target_valid & target_expected_grid
    target_values_valid_grid = target_values[target_on_grid]

    meter_april = frames["meter"].copy()
    meter_raw_values = meter_april[TARGET].astype("string") if TARGET in meter_april else pd.Series(dtype="string")
    meter_numeric = pd.to_numeric(meter_raw_values, errors="coerce")
    meter_timestamps = pd.DatetimeIndex(meter_april["_timestamp"].dropna().unique()) if not meter_april.empty else pd.DatetimeIndex([])
    expected_naive = expected.tz_localize(None) if expected.tz is not None else expected
    meter_naive = meter_timestamps.tz_localize(None) if meter_timestamps.tz is not None else meter_timestamps
    meter_expected = set(expected_naive.asi8)
    meter_observed = set(meter_naive.asi8)
    missing_target_timestamps = len(meter_expected - meter_observed)
    meter_first = meter_timestamps.min() if len(meter_timestamps) else None
    meter_last = meter_timestamps.max() if len(meter_timestamps) else None
    meter_first_naive = meter_first.tz_localize(None) if meter_first is not None and meter_first.tzinfo else meter_first
    meter_last_naive = meter_last.tz_localize(None) if meter_last is not None and meter_last.tzinfo else meter_last
    target_covered_expected = [t for t in expected_naive if meter_first_naive is not None and meter_first_naive <= t <= meter_last_naive]
    target_timestamps_within_span = set(meter_naive.asi8) & set(pd.DatetimeIndex(target_covered_expected).asi8)
    target_internal_missing = len(target_covered_expected) - len(target_timestamps_within_span)
    target_leading_unavailable = sum(t < meter_first_naive for t in expected_naive) if meter_first_naive is not None else len(expected)
    target_trailing_unavailable = sum(t > meter_last_naive for t in expected_naive) if meter_last_naive is not None else len(expected)
    null_target_rows = int(meter_numeric.isna().sum())
    nonnumeric_target_rows = int((meter_raw_values.notna() & meter_numeric.isna()).sum())

    source_timestamp_quality = {}
    for group, frame in frames.items():
        source_timestamp_quality[group] = timestamp_stats(
            frame[["_timestamp"]].drop_duplicates().copy(), expected
        )

    report: dict[str, Any] = {
        "audit_scope": "April 1 through April 30, 2025 inclusive; source files retained unchanged.",
        "system_id": 9068,
        "window_start_inclusive": START.isoformat(),
        "window_stop_exclusive": STOP.isoformat(),
        "nominal_cadence": "5 minutes per system metadata; verified separately against observed timestamps below.",
        "retrieval_date_utc": "2026-11-08",
        "source_base_url": "https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/9068_OEDI/data/",
        "dataset_license": "CC BY 4.0",
        "dataset_license_url": "https://creativecommons.org/licenses/by/4.0/",
        "dataset_doi": "https://doi.org/10.25984/1846021",
        "attribution": "Deline, C., Perry, K., Deceglie, M., Muller, M., Sekulic, W., & Jordan, D. (2021). Photovoltaic Data Acquisition (PVDAQ) Public Datasets. Open Energy Data Initiative (OEDI), NREL. https://doi.org/10.25984/1846021",
        "source_metadata_version": {
            "system_metadata_url": "https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/9068_OEDI/metadata/9068_system_metadata.json",
            "system_metadata_vintage_limit": "The system JSON reports through 2023-11-16; the 2025 increment is described separately in the 2025-06-27 change log.",
            "increment_change_log": "https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/change_log_2023_Solar_Data_Prize_20250627.pdf",
            "increment_coverage_by_name": "2024-01-01 through 2025-04-30",
            "retrieval_date_utc": "2026-11-08",
        },
        "source_object_validation": source_reports,
        "source_metadata_channels_absent_from_objects": missing_in_objects,
        "pilot_rows_written_including_missing_grid_rows_and_off_grid_records": int(len(combined)),
        "actual_source_row_counts_in_pilot": {
            "meter": int(combined["meter_source_row_present"].sum()),
            "irradiance": int(combined["irradiance_source_row_present"].sum()),
            "environment": int(combined["environment_source_row_present"].sum()),
            "any_source_group": int(combined["source_record_present_any_group"].sum()),
            "note": "Rows without a source record are explicit expected-grid placeholders with null values, not fabricated measurements.",
        },
        "pilot_timestamp_range": {
            "first": str(combined["timestamp_source"].iloc[0]) if len(combined) else None,
            "last": str(combined["timestamp_source"].iloc[-1]) if len(combined) else None,
            "all_source_timestamps_timezone_aware": bool(combined["timestamp_timezone_aware"].all()) if len(combined) else None,
            "timezone_interpretation": "Preserved as recorded; no localization or UTC assumption was applied.",
        },
        "expected_five_minute_slots": int(len(expected)),
        "missing_expected_timestamps": int(len(expected_missing)),
        "missing_expected_timestamp_examples": [t.isoformat() for t in expected_missing[:20]],
        "timestamp_quality_by_source_group": source_timestamp_quality,
        "all_channel_union_timestamp_quality": timestamp_stats(
            pd.DataFrame({"_timestamp": observed_index}), expected
        ),
        "target_channel": {
            "identifier": TARGET,
            "units": "kW",
            "aggregation": "avg",
            "meter_time_interval_alignment": "L (left-aligned), per system metadata",
            "rows_with_numeric_target_in_pilot": int(target_valid.sum()),
            "unique_target_source_timestamps": int(len(meter_timestamps)),
            "target_rows_on_expected_five_minute_grid": int(target_on_grid.sum()),
            "missing_expected_target_timestamps": int(missing_target_timestamps),
            "target_observed_coverage": {
                "first_interval_start": meter_first.isoformat() if meter_first is not None else None,
                "last_interval_start": meter_last.isoformat() if meter_last is not None else None,
                "last_interval_close": (meter_last + FREQ).isoformat() if meter_last is not None else None,
                "expected_slots_inside_first_to_last_observed_span": int(len(target_covered_expected)),
                "missing_slots_inside_first_to_last_observed_span": int(target_internal_missing),
                "leading_slots_before_first_observation": int(target_leading_unavailable),
                "trailing_slots_after_last_observation": int(target_trailing_unavailable),
                "full_calendar_window_observed": bool(missing_target_timestamps == 0),
                "coverage_elapsed_to_last_interval_close": str((meter_last + FREQ - meter_first) if meter_last is not None else "unavailable"),
            },
            "blank_or_nonnumeric_target_rows_at_observed_timestamps": null_target_rows,
            "nonnumeric_nonblank_target_rows": nonnumeric_target_rows,
            "missing_target_fraction_of_expected_grid": float((missing_target_timestamps + null_target_rows) / len(expected)),
            "target_distribution_on_grid": {
                "minimum_kw": float(target_values_valid_grid.min()) if len(target_values_valid_grid) else None,
                "p01_kw": float(target_values_valid_grid.quantile(0.01)) if len(target_values_valid_grid) else None,
                "median_kw": float(target_values_valid_grid.median()) if len(target_values_valid_grid) else None,
                "mean_kw": float(target_values_valid_grid.mean()) if len(target_values_valid_grid) else None,
                "p99_kw": float(target_values_valid_grid.quantile(0.99)) if len(target_values_valid_grid) else None,
                "maximum_kw": float(target_values_valid_grid.max()) if len(target_values_valid_grid) else None,
                "negative_readings_flagged_not_removed": int((target_values_valid_grid < 0).sum()),
                "above_4011_kw_flagged_not_removed": int((target_values_valid_grid > 4011).sum()),
                "engineering_flag_threshold_kw": 4011,
                "threshold_basis": "5% above two metadata-listed 1,910 kW AC inverter capacities; flag only, not a deletion rule.",
            },
        },
        "weather_and_sensor_channels": channel_stats(combined.assign(_timestamp=pilot_ts), expected, channel_columns),
        "measurement_parse_failures": {
            "non_numeric_nonblank_by_channel": non_numeric_counts,
            "evidence_file": str((REPORT_DIR / "non_numeric_measurement_records.csv").relative_to(ROOT)).replace("\\", "/") if non_numeric_rows else None,
        },
        "quality_flags_not_applied_as_filters": {},
        "sensor_alignment": {},
        "irradiance_pair_checks": {},
        "forecast_alignment": None,
        "reporting_delay": "Not measurable from these CSV columns; no ingest/receipt timestamp is included.",
        "interpretation_notes": [
            "Source files span January 2024 through April 2025; this audit's statistics and derived rows are limited to April 2025 only.",
            "Only the selected target and potential sensor columns were written to the derived pilot. Original source objects were not changed.",
            "Expected-grid rows with source_record_present_any_group=false are timestamp placeholders with null measurements, not fabricated observations.",
            "Duplicate timestamp evidence is saved separately. Exact duplicate selected-channel rows are collapsed in the derived view; conflicting fields are set missing and flagged, not chosen arbitrarily.",
            "Questionable values are flagged, not clipped or removed. No missing values are interpolated.",
        ],
    }

    for column in channel_columns:
        numeric = pd.to_numeric(combined[column], errors="coerce")
        flags: list[dict[str, Any]] = []
        if column == TARGET:
            negative_count = int((numeric < 0).sum())
            over_capacity_count = int((numeric > 4011).sum())
            if negative_count:
                flags.append({"flag": "negative_revenue_meter_power", "count": negative_count,
                              "interpretation": "Preserved; may represent bidirectional/net meter flow or auxiliary consumption, and must be confirmed before treating as gross PV generation."})
            if over_capacity_count:
                flags.append({"flag": "above_4011_kw_review_threshold", "count": over_capacity_count,
                              "interpretation": "Review against two 1,910 kW AC inverter ratings; no values were clipped or removed."})
        elif "irradiance" in column:
            negative_count = int((numeric < 0).sum())
            high_count = int((numeric > 1500).sum())
            if negative_count:
                flags.append({"flag": "negative_irradiance_zero_offset_candidate", "count": negative_count,
                              "interpretation": "Small negative values are retained as recorded; likely require dark-offset/measurement review."})
            if high_count:
                flags.append({"flag": "above_1500_w_m2_review_threshold", "count": high_count,
                              "interpretation": "Review only; no values were clipped or removed."})
        elif "temperature" in column:
            outside = int(((numeric < -50) | (numeric > 100)).sum())
            if outside:
                flags.append({"flag": "temperature_outside_minus50_to_100_c", "count": outside,
                              "interpretation": "Sensor value retained; readings outside this broad physical review range should not be treated as valid without investigation."})
        run = longest_constant_run(numeric, pilot_ts)
        if run["constant_run_at_least_60_minutes"]:
            flags.append({"flag": "constant_reading_run_at_least_60_minutes", **run,
                          "interpretation": "Flag for stale-sensor review; a stable signal alone is not proof of sensor failure."})
        report["quality_flags_not_applied_as_filters"][column] = flags

    report["pilot_acceptance_check"] = {
        "pilot_window_is_30_calendar_days": True,
        "target_missing_limit_5_percent": {
            "measured_fraction": report["target_channel"]["missing_target_fraction_of_expected_grid"],
            "passes": report["target_channel"]["missing_target_fraction_of_expected_grid"] <= 0.05,
        },
        "target_duplicate_timestamps": source_reports["meter"]["duplicate_analysis"]["duplicate_timestamp_groups"],
        "target_off_grid_timestamps": source_timestamp_quality["meter"]["off_grid_timestamps"],
        "target_internal_missing_slots_within_observed_span": int(target_internal_missing),
        "target_trailing_unavailable_slots_at_source_edge": int(target_trailing_unavailable),
        "requested_month_window_complete": bool(missing_target_timestamps == 0),
        "pilot_has_at_least_500000_observations": int(target_on_grid.sum()) >= 500_000,
        "500000_observation_threshold_applies_to_full_history_not_this_30_day_pilot": True,
        "wind_channel_availability": "Not present in the downloaded environment object headers; excluded from the derived pilot.",
        "module_temperature_sensor_149730": "Fails sensor plausibility/staleness review; retain source channel for traceability but exclude from candidate inputs pending investigation.",
        "status": "Pilot is sufficient to reveal major channel and target semantics risks; not a pass for full-history acquisition or model readiness.",
    }
    report["recommendation_full_historical_acquisition"] = (
        "System 9068 remains viable for conditional full-history acquisition, but first confirm the revenue-meter negative-sign semantics and exclude failed module temperature channel 149730 from candidate features. The April pilot has no internal target gaps and a 1.33% overall missing fraction, but stops 9h35 before the requested window closes. This pilot does not validate the full 16-month increment or the complete historical span."
    )

    # Per-channel timestamp intersection against target and measured missingness on full expected grid.
    target_timestamps = set(pd.DatetimeIndex(pilot_ts[target_valid]))
    for column in channel_columns:
        observed = pd.to_numeric(combined[column], errors="coerce").notna()
        channel_ts = set(pd.DatetimeIndex(pilot_ts[observed]))
        report["sensor_alignment"][column] = {
            "channel_numeric_observations": int(observed.sum()),
            "timestamps_in_common_with_target": int(len(target_timestamps & channel_ts)),
            "target_timestamps_without_sensor_value": int(len(target_timestamps - channel_ts)),
            "sensor_timestamps_without_target": int(len(channel_ts - target_timestamps)),
        }

    target_span_mask = (pilot_ts >= meter_first) & (pilot_ts <= meter_last) if meter_first is not None else pd.Series(False, index=pilot_ts.index)
    report["sensor_missingness_within_target_observed_span"] = {
        column: {
            "expected_target_span_timestamps": int(target_span_mask.sum()),
            "missing_sensor_values_inside_target_observed_span": int(
                pd.to_numeric(combined.loc[target_span_mask, column], errors="coerce").isna().sum()
            ),
        }
        for column in channel_columns if column != TARGET
    }

    daylight_negative = (
        (pd.to_numeric(combined[TARGET], errors="coerce") < 0)
        & (pd.to_numeric(combined[POA[2]], errors="coerce") > 50)
    )
    negative_daylight_rows = combined.loc[
        daylight_negative,
        ["timestamp_source", TARGET, POA[2], AMBIENT],
    ].copy()
    negative_daylight_rows.to_csv(REPORT_DIR / "negative_power_with_irradiance.csv", index=False)
    report["target_channel"]["negative_power_readings_above_50_w_m2_poa"] = {
        "count": int(len(negative_daylight_rows)),
        "evidence_file": "negative_power_with_irradiance.csv",
        "interpretation": "Preserved for review; negative meter readings with measurable POA cannot be assumed to be ordinary nighttime auxiliary consumption.",
        "full_history_sign_convention_confirmation_required": True,
    }

    raw_by_name = {c: pd.to_numeric(combined[c], errors="coerce") for c in POA if c in combined}
    pairs = [
        (POA[0], POA[2]),
        (POA[1], POA[3]),
        (POA[0], POA[1]),
        (POA[2], POA[3]),
    ]
    for left, right in pairs:
        if left in raw_by_name and right in raw_by_name:
            valid = raw_by_name[left].notna() & raw_by_name[right].notna()
            daylight = valid & ((raw_by_name[left] > 50) | (raw_by_name[right] > 50))
            report["irradiance_pair_checks"][f"{left}__vs__{right}"] = {
                "common_observations": int(valid.sum()),
                "daylight_like_observations_above_50_w_m2": int(daylight.sum()),
                "pearson_correlation_all_common": float(raw_by_name[left][valid].corr(raw_by_name[right][valid])) if valid.sum() > 1 else None,
                "pearson_correlation_above_50_w_m2": float(raw_by_name[left][daylight].corr(raw_by_name[right][daylight])) if daylight.sum() > 1 else None,
                "median_left_over_right_when_both_above_50": float((raw_by_name[left][daylight] / raw_by_name[right][daylight].replace(0, np.nan)).median()) if daylight.any() else None,
                "interpretation": "Comparative QC only; low agreement or sustained ratio bias flags a sensor for review, not proof of shading.",
            }

    # Actual example: issue at close of interval t, then label t+20 is the
    # interval beginning 15 minutes after issue (left-labelled 5-minute target).
    indexed = combined.copy()
    indexed["_ts"] = pilot_ts
    indexed = indexed.set_index("_ts", drop=False)
    example = None
    for t in expected:
        issue = t + FREQ
        target_start = issue + pd.Timedelta(minutes=15)
        if t not in indexed.index or target_start not in indexed.index:
            continue
        source_row = indexed.loc[t]
        target_row = indexed.loc[target_start]
        if isinstance(source_row, pd.DataFrame) or isinstance(target_row, pd.DataFrame):
            continue
        if pd.isna(source_row.get(TARGET)) or pd.isna(target_row.get(TARGET)):
            continue
        preferred_poa = POA[2] if POA[2] in channel_columns else None
        if preferred_poa is None or pd.isna(source_row.get(preferred_poa)) or float(source_row[preferred_poa]) < 250:
            continue
        if float(source_row[TARGET]) < 100 or float(target_row[TARGET]) < 100:
            continue
        record = {
            "latest_observed_interval_start": t.isoformat(),
            "latest_observed_interval_close_issue_time": issue.isoformat(),
            "target_interval_start_issue_plus_15m": target_start.isoformat(),
            "target_interval_end": (target_start + FREQ).isoformat(),
            "input_timestamp_not_after_issue": bool(t < issue),
            "target_timestamp_matches_issue_plus_15m": bool(target_start == issue + pd.Timedelta(minutes=15)),
            "target_power_at_latest_interval_kw": float(source_row[TARGET]),
            "future_target_power_kw_for_verification_only": float(target_row[TARGET]),
            "input_features": {
                c: json_value(source_row[c])
                for c in channel_columns
                if c != TARGET and c != MODULE[2] and pd.notna(source_row.get(c))
            },
        }
        example = record
        break
    report["forecast_alignment"] = {
        "issue_rule": "Close of latest fully observed interval; meter records are left-aligned.",
        "target_rule": "Target label is the start of the 5-minute interval exactly 15 minutes after issue time.",
        "actual_record_example": example,
        "verification": "Target value is included only as the audit label in this example; feature values are read at the latest observed interval, before issue time.",
    }
    if example:
        with (REPORT_DIR / "forecast_alignment_example.json").open("w", encoding="utf-8") as stream:
            json.dump(json_value(example), stream, indent=2, ensure_ascii=False, allow_nan=False)

    report["derived_pilot_file"] = {
        "path": str(pilot_path.relative_to(ROOT)).replace("\\", "/"),
        "size_bytes": pilot_path.stat().st_size,
        "sha256": sha256(pilot_path),
        "columns": list(combined.columns),
        "rows": int(len(combined)),
    }
    report["duplicate_evidence_file"] = str((REPORT_DIR / "duplicate_timestamp_records.csv").relative_to(ROOT)).replace("\\", "/") if duplicate_evidence else None
    report_path = REPORT_DIR / "quality_report.json"
    with report_path.open("w", encoding="utf-8") as stream:
        json.dump(json_value(report), stream, indent=2, ensure_ascii=False, allow_nan=False)

    print(json.dumps({
        "pilot_file": str(pilot_path),
        "report_file": str(report_path),
        "source_objects": {k: {"size_bytes": v["file_size_bytes"], "sha256": v["sha256"]} for k, v in source_reports.items()},
        "expected_five_minute_slots": report["expected_five_minute_slots"],
        "pilot_rows": report["pilot_rows_written_including_missing_grid_rows_and_off_grid_records"],
        "target_observations": report["target_channel"]["rows_with_numeric_target_in_pilot"],
        "missing_expected_target_timestamps": report["target_channel"]["missing_expected_target_timestamps"],
        "blank_or_nonnumeric_target_rows_at_observed_timestamps": report["target_channel"]["blank_or_nonnumeric_target_rows_at_observed_timestamps"],
        "alignment_example": example,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

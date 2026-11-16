# Phase C2.0 — Historical AC Object Preflight

## Executive result

**The legacy System 9068 AC-power object is present and accessible.** The exact key was verified in the official OEDI S3 bucket listing before issuing a HEAD request. HEAD returned HTTP 200 with `Content-Length` matching the listing. No CSV body was requested or downloaded.

The object appears suitable for a separately authorized download for historical schema/continuity review. Its existence and object metadata do not validate its rows, metric definitions, cadence, or continuity with the 2024–2025 increment.

## Object identity and inventory evidence

- System directory: `9068_OEDI`; source inventory record explicitly identifies the key below.
- Exact object key: `pvdaq/2023-solar-data-prize/9068_OEDI/data/9068_ac_power_data.csv`
- Exact official object URL: <https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/9068_OEDI/data/9068_ac_power_data.csv>
- Official S3 listing query used to verify the key (inventory response only): <https://oedi-data-lake.s3.amazonaws.com/?list-type=2&prefix=pvdaq%2F2023-solar-data-prize%2F9068_OEDI%2Fdata%2F9068_ac_power_data.csv>
- Listing response: HTTP 200; exact matching `<Key>`; one result (`KeyCount=1`); `Size=65,002,925`; ETag `"63ab983741d1a8c2a4e275948179fb65-4"`; `LastModified=2024-01-02T17:12:56Z`; storage class `INTELLIGENT_TIERING`.
- Local inventory reference: `ml/data/reports/pvdaq/9068/phase_c1_7/phase_c1_7_report.md`, which records that the previously reviewed OEDI inventory listed `9068_ac_power_data.csv` as the legacy System 9068 AC-power object. That prior report did not retain the URL or object-level size; the official listing check above now verifies the exact key.
- Identity ambiguity: none apparent in the key or directory. The prefix explicitly associates it with the System 9068 OEDI prize folder; the filename is the legacy AC-power name. The listing and HEAD agree on object identity and size.

## HEAD response (no body retrieved)

- Request method: `HEAD`
- HTTP status: `200`
- Request date header: `Mon, 09 Nov 2026 08:49:22 GMT`
- `Content-Length`: `65,002,925` bytes (about 65.00 MB decimal / 61.99 MiB)
- ETag: `"63ab983741d1a8c2a4e275948179fb65-4"`
- `Last-Modified`: `Tue, 02 Jan 2024 17:12:56 GMT`
- `Content-Type`: `application/vnd.ms-excel`
- Other returned metadata: storage class `INTELLIGENT_TIERING`; server-side encryption `AES256`; version ID `rVLH1pbJwr6I3eHJpf.sx1HZUcvPT.aF`; S3 metadata SHA-256 `d0f7381abfaad9f53ae74fca7c6761aecbc344e595faf316406c3b081f0d1548`; S3 metadata last-modified marker `20231210T181547Z`.
- Accessibility: accessible through HEAD; no object body was retrieved.
- Expected transfer size if separately approved: 65,002,925 bytes.

## Comparison with the acquired increment

The existing manifest for `9068_ac_power_data_20240101_20250430.csv` records:

| Property | Legacy object | 2024–2025 increment |
|---|---|---|
| Key/name | `.../9068_OEDI/data/9068_ac_power_data.csv` | `.../9068_OEDI/data/9068_ac_power_data_20240101_20250430.csv` |
| Object size | 65,002,925 bytes (verified listing and HEAD) | 10,870,311 bytes (existing acquisition manifest) |
| Last modified | 2024-01-02 17:12:56 GMT | 2025-06-27 21:04:43 GMT (existing manifest) |
| Documented family | System 9068 legacy AC-power object | System 9068 AC-power increment; exact downloaded object and metric IDs 150135–150144 previously inspected |
| Actual legacy rows/schema | Not inspected; no download authorized | Already acquired and inspected for April pilot |

**CONFIRMED:** Both objects are listed in the same System 9068 OEDI `data/` group and use the same base AC-power object name, with the increment distinguished by its date suffix. The increment’s acquisition manifest gives its exact source URL, 10,870,311-byte size, and 2025-06-27 modification timestamp.

The local System 9068 metadata JSON reports a latest timestamp of `2023-11-16 13:45:00` and a five-minute resolution. The increment filename starts on `2024-01-01`. If that metadata endpoint represents the final legacy observation and the increment filename reflects its actual first observation, the nominal separation is about 45 days 10 hours 15 minutes. These endpoints are not both verified from the legacy CSV in this preflight, so that interval is a **coverage question**, not a confirmed gap length.

The legacy object’s S3 `Last-Modified` time is file-object metadata, not the time of its final observation. It cannot establish measurement coverage. Likewise, names, inventory position, shared folder, or object dates do not prove schema or time-series continuity.

## Historical questions for the authorized review

After a separate exact-object download approval, inspect the legacy object against the increment for:

1. Actual first and last timestamps and whether the legacy final observation matches System metadata’s 2023-11-16 endpoint.
2. Whether its columns contain primary metrics 150143 and 150144 and whether IDs, names, units, and observed values match the increment.
3. Timestamp cadence, interval labeling, timezone/DST behavior, duplicate rows, missing intervals, and any boundary overlap or gap.
4. Whether metric or equipment definitions, channel availability, or measurement behavior changed across the file boundary.
5. Whether any additional documented system reconfiguration explains changes; absence of documentation would not prove none occurred.

## Recommendation

**Suitable for a separately authorized download:** Yes. The exact official object key and URL are confirmed, it is accessible, and the transfer size is bounded at 65,002,925 bytes. The next step should be a separately approved download of this exact object only, followed by a read-only schema and continuity comparison. This preflight does not authorize that download.

## Scope confirmation

Only the OEDI object listing and a HEAD request to the verified legacy object URL were used for remote checks. The listing returned inventory metadata; HEAD returned response headers. The legacy CSV body and all other files were not downloaded. No existing data, manifests, pilot datasets, or modules were modified. This report is saved separately under `ml/data/reports/pvdaq/9068/phase_c2_0/`.

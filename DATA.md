# DATA.md — data card (work in progress)

## 1. Source
- MarineCadastre / NOAA Office for Coastal Management, Nationwide AIS, from USCG NAIS terrestrial receivers.
- File: `ais-2026-04-15.csv.zst` from `https://noaaocm.blob.core.windows.net/ais/csv2/csv2026/`.
  - 227,742,913 bytes. Its size was checked against the server's Content-Length.
  - Download: `scripts/download.ps1`.
- 2025+ format: zstd-compressed CSV, snake_case columns, longitude before latitude, sentinels stored as null, one position per vessel per minute.

## 2. Day, bounding box, decisions
- **Day:** Wednesday 2026-04-15, as a UTC day from 00:00:00 to 23:59:59.
- **Bounding box (Houston–Galveston approaches):** lat 28.40–29.90, lon −95.60 to −93.70.
- **Presence universe for the coverage test:** the bbox plus a 0.5° margin.

### Block-1 day check (2026-11-08): **GO, keep 2026-04-15**
- **Feed outage check:** the bbox hourly row count stays between 22.9k and 31.2k rows per hour all day. There is no sharp dip. Hours 15–16 UTC are about 12% below the daily mean, which is mild and not an outage.
- **Fog / mass-anchoring check:**
  - Anchored or moored vessels stay between 297 and 342 per hour (about 32–35% of the vessels in the box), with no sudden jump.
  - The share of stationary pings peaks at 81% around 07–11 UTC (02:00–06:00 local time) and drops to 66% in the afternoon. That looks like the normal night-time lull.
  - Independent check: Galveston airport (GLS) and Lake Jackson airport (LBX) reported visibility of 9–10 statute miles in every hourly report that day, with no fog or mist codes. Source: Iowa Environmental Mesonet ASOS archive.
- **Conclusion:** no fog closure and no broken feed, so there is no reason to switch days.

## 3. Row counts per stage
| Stage | Rows | Vessels (MMSI) |
|---|---|---|
| Raw national file | 7,806,560 | 20,527 |
| Ship-range MMSI (201000000–775999999) | 7,801,917 | 20,470 |
| Raw rows inside the bbox | 637,420 | 1,168 (932 Class A, 239 Class B) |
| *Later stages (clean → tracks → universe → gaps → top 50) are filled in block 2* | | |

## 4. What the raw feed looks like (block-1 profile)
- **Schema:** matches the 2025+ data dictionary, with 17 columns. DuckDB reads `.zst` directly and the timestamps parse as UTC `TIMESTAMP`.
- **Sentinels:** there are none. No rows have SOG ≥ 102.2, heading > 359, COG ≥ 360 or |lat|/|lon| out of range. NOAA's nulling is confirmed; the defensive filters stay anyway.
- **Implausible speed:** 38 rows have SOG > 50 kn. They are candidates for aircraft or GPS errors and are handled by the `teleport` flag.
- **Nulls:**
  - `heading`: 49.5%
  - `status`: 36.6% (Class B does not send a nav status)
  - `cog`: 17.9%
  - `draft`: 46.5%
  - `imo`: 62.9%
  - `vessel_type`: 1.0%
  - `sog`: 0.29%
  - positions and timestamps: 0%
- **Non-ship MMSIs:**
  - 36 MMSIs with other 9-digit values (4,349 rows)
  - 20 SART/MOB/EPIRB units with 97x MMSIs (257 rows)
  - 1 AtoN with a 99x MMSI (37 rows)
  - No MMSIs shorter than 9 digits, so no base stations appear in this file.
  - All of these are removed by the ship-range filter.
- **Duplicates:**
  - 1,786 exact duplicate rows.
  - 1,793 (mmsi, timestamp) keys with two or more rows, so only about 7 keys have conflicting values.
- **Transceiver, national:** Class A has 9,740 MMSIs and 5.34 M rows. Class B has 10,802 MMSIs and 2.46 M rows.
- **Vessel mix in the bbox (distinct MMSI):**

| Group | MMSIs |
|---|---|
| tug/tow | 484 |
| pleasure/sail | 181 |
| tanker | 178 |
| other | 135 |
| fishing | 68 |
| cargo | 67 |
| passenger | 42 |
| unknown | 13 |

### Hourly profile of the bbox (UTC)
| Hour | Rows | MMSI | Anchored/moored MMSI | % pings with SOG < 0.5 |
|---|---|---|---|---|
| 00 | 26,860 | 948 | 297 | 71.2 |
| 03 | 26,932 | 938 | 307 | 76.8 |
| 06 | 26,466 | 929 | 312 | 79.6 |
| 09 | 28,749 | 938 | 326 | 80.5 |
| 12 | 27,274 | 975 | 336 | 78.2 |
| 15 | 22,896 | 1,003 | 338 | 78.1 |
| 18 | 24,599 | 1,005 | 327 | 69.3 |
| 21 | 25,472 | 995 | 320 | 65.8 |

The full 24-hour table is produced by `scripts/profile_day.py`.

## 5–9. Feature dictionary, scoring, label counts, training-set notes, known issues
*To be written in blocks 3–6.*

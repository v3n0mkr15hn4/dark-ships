# DATA.md — data card

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
These counts are produced by `python run.py` and written to `out/stage_counts.json`.

| Stage | Rows | Vessels (MMSI) | Dropped because |
|---|---|---|---|
| Raw national file | 7,806,560 | 20,527 | – |
| Ship-range MMSI (201000000–775999999) | 7,801,917 | 20,470 | 4,643 rows from non-ship MMSIs (SART, AtoN, other) |
| Valid position | 7,801,917 | | 0 rows (no out-of-range or 0,0 positions) |
| One row per (mmsi, timestamp) | 7,800,124 | | 1,793 duplicate rows (exact and conflicting copies) |
| Vessels with ≥1 clean ping in the bbox | – | 1,164 | (1,168 raw: 4 non-ship MMSIs) |
| Their full national-day tracks | 708,414 | 1,164 | |
| Presence universe (all vessels, bbox ± 0.5°) | 906,216 | 1,498 | |
| Gaps (K = 10, ≥1 endpoint in the bbox) | 515 | 142 | |
| Top 50 by score, reviewed and labelled | 50 | 23 | |

**Gap-threshold sensitivity** (same tracks, gap if ≥ max(600 s, K × E)):

| K | Gaps |
|---|---|
| 5 | 2,030 |
| **10 (used)** | **515** |
| 20 | 185 |

**Gap mix at K = 10:**
- By expected interval: 404 gaps had a slow expected interval (E = 180 s: anchored, moored or slow) and 111 had a fast one (60 s).
- By class: Class B 377, Class A 138.
- By vessel group: pleasure/sail 316, fishing 65, tug/tow 56, other 28, tanker 23, cargo 14, passenger 13.
- Median gap 42 min, 90th percentile 2.2 h, maximum 16.6 h.
- Implied speed over 50 kn: 0 gaps.

**Known-good check:** the 10 busiest ferries and pilot boats at Bolivar Roads (Galveston–Port Bolivar ferries, pilot boats) are heard all day with **0 gaps** each.

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

## 5. Scoring rule (frozen before review, git tag `weights-frozen`, config_hash `b0ae721a`)

`score = 100 × (0.35·D + 0.30·C + 0.15·U + 0.10·K + 0.10·T) × Π suppressors`

All values come from `config.toml`; the full definitions are in PLAN.md §6.

**Terms:**
- **D (duration):** `clip(log10(gap_ratio)/3, 0, 1)`
- **C (coverage):** `max(coverage_during_gap, 0.5 if heard_today else 0)`
- **U (underway):** 1 if sog0 ≥ 2 kn and status0 is not anchored or moored, otherwise 0
- **K (unaccounted time):** `unaccounted_frac`
- **T (type prior):** 1 for Class A tanker, cargo or fishing; 0.6 for other Class A; 0.3 for Class B or unknown

**Suppressors:**

| Suppressor | Trigger | Factor | Fired on (of 515) |
|---|---|---|---|
| Coverage hole | NOT `heard_today` | ×0.2 | 0 |
| Port, berth or anchorage | (stationary cell AND NOT moving ≥ 2 kn at both ends) OR (anchored/moored at both ends AND moved < 0.5 nm) OR (SOG < 0.5 at both ends) | ×0.2 | 397 |
| Teleport | implied speed > 50 kn | ×0.3 | 0 |
| Shared or spoofed MMSI | more than 5% of consecutive pings imply over 50 kn | ×0.1 | 0 |

**Leave-one-out ablation** (top 50 kept when one part is removed; from `out/ablation.csv`):

| Removed | Top 50 kept | Jaccard |
|---|---|---|
| U (underway) | 36 | 0.56 |
| T (type prior) | 36 | 0.56 |
| Port suppressor | 40 | 0.67 |
| D (duration) | 42 | 0.72 |
| K (unaccounted time) | 44 | 0.79 |
| C (coverage) | 49 | 0.96 |
| Coverage-hole / teleport / MMSI-conflict suppressors | 50 | 1.00 |

**What the ablation shows (before any labelling):**
- **Coverage hardly separates events in this box.** 509 of 515 gaps have `coverage_during_gap` = 1, and every gap has `heard_today` = True. Even gaps more than 30 nm offshore score at least 0.8. The box sits inside the 40–50 mile terrestrial range, and traffic is dense enough that another vessel is almost always heard within about 10 nm. So here, coverage is almost never the explanation for a silence.
  - Caveat: a nearby Class A vessel (12.5 W) being heard does not prove a Class B unit (2 W) would be heard.
- **The port suppressor is the main false-alarm filter.** It fires on 397 of 515 gaps, mostly Class B leisure boats in marinas.

**Top 50 at freeze:**
- 23 distinct vessels.
- By group: fishing 28, cargo 8, pleasure/sail 5, passenger 4, tanker 3, tug/tow 1, other 1.
- By class: Class A 30, Class B 20.
- Score at rank 50 is 66.5; rank 51 is 65.4.

## 6. Feature dictionary
The full table, with formulas and the hypothesis each one tests, is in PLAN.md §5. The `events.parquet` columns are:
- **Identity:** `event_id` (`{mmsi}_{t0:%Y%m%dT%H%M%S}`), `mmsi`, `vessel_name`, `imo`, `call_sign`, `vessel_type`, `vessel_group`, `transceiver`, `length`
- **Gap:** `t0`, `t1` (UTC), `gap_s`, `expected_interval_s`, `gap_ratio`
- **Endpoints:** `lat0/lon0/lat1/lon1`, `sog0/sog1`, `cog0/cog1`, `hdg0/hdg1`, `status0/status1`
- **Movement:** `dist_nm` (haversine), `implied_kn`, `typical_kn`, `speed_ratio`, `unaccounted_frac`, `max_excursion_nm`, `dcog_deg`
- **Coverage:** `n_buckets`, `n_buckets_covered`, `coverage_during_gap`, `heard_today`, `cell_density0/1`, `stationary_cell`
- **Data quality:** `teleport`, `jump_rate`, `mmsi_conflict`
- **Context:** `n_gaps_vessel`, `hour_utc`, `bbox_edge_nm`, `near_day_boundary`, `p0_in_bbox`, `p1_in_bbox`
- **Score:** `D, C, U, K, T`, `sup_*` flags, `suppressors`, `suppress_factor`, `score`, `rank`
- **Provenance:** `config_hash`, `pipeline_version`

## 7. Labels (`out/labels.jsonl`, 50 events)

| Label | Count |
|---|---|
| real | **6** |
| data_artefact | **34** |
| unsure | **10** |

**How the labels were made:**
- **#1** (ACCP 1, rank 1) was labelled directly by the reviewer in the app. Its note was later replaced with the AI evidence text, so all 50 notes have the same style.
- **The other 49** started as AI suggestions (Claude Opus 5.5) built from numeric evidence, then were reviewed and accepted by the reviewer. Those records carry `label_origin`, `ai_rule` and `ai_confidence` fields.
- Each label's `note` holds the evidence behind it. `ai_rule` says which rule the suggestion followed:
  - **R1** `data_artefact`: gap of 15 min or less, steady speed, covered about the distance its speed predicts (short dropout).
  - **R2** `data_artefact`: an innocent cause is visible (parked or moored, edge of receiver range, or a unit only intermittently received, as shown by isolated single reports).
  - **R3** `real`: 45 min or more, moving, other vessels within 3 nm heard during the gap, no innocent cause visible.
  - **R4** `unsure`: everything else, e.g. round trips that could leave coverage, or no neighbours to show reception.

**Precision of the frozen rule** (share labelled `real`):

| Top k | real | real + unsure |
|---|---|---|
| 10 | 0.40 | 0.70 |
| 25 | 0.24 | 0.44 |
| 50 | 0.12 | 0.32 |

**Real events:** only two vessels.
- MORNING LORD (Class A shrimp trawler, East Bay): 5 events, silences of 52 min to 2.2 h while trawling, with Class B boats within 3 nm still heard.
- ACCP 1 (fast 9 m Class B boat): 1 event, 11.9 h silent on a round trip through a well-covered channel.

**False alarms (34 `data_artefact`) by cause:**

| Cause | Events |
|---|---|
| Unit on but only intermittently received: isolated single reports, or poorly received all day even while moving | 16 |
| Short dropout (15 min or less) during steady motion; covered the expected distance | 13 |
| Parked or moored, or coming to rest, across the gap | 4 |
| Edge of receiver range offshore | 1 |

**By transceiver class:**

| Class | real | data_artefact | unsure |
|---|---|---|---|
| A | 5 | 24 | 1 |
| B | 1 | 10 | 9 |

## 8. Training-set notes
- **Keys:** `event_id` = `{mmsi}_{t0:%Y%m%dT%H%M%S}` joins `labels.jsonl` to `events.parquet`. `config_hash` (`b0ae721a`) pins the thresholds and weights that produced each event.
- **Duplicate records:** `labels.jsonl` is append-only. If an event_id appears more than once, the last line wins.
- **Label semantics (agreed with RSKD):**
  - `real` = the ship went dark while its area was reachable (other vessels nearby were heard during the gap) and no innocent cause is visible. This is a **presumption of intent, not proof**.
  - `data_artefact` = an innocent cause is visible: reception, parked or moored, coverage edge, short dropout.
  - `unsure` = one day of data cannot decide.
- **Known biases:**
  - **Selection bias:** labels exist only for the rule's top 50, so they say nothing about recall.
  - **One reviewer, AI-assisted:** 49 of 50 labels started as AI suggestions, so the AI's reasoning patterns can be inherited.
  - **Clustered events:** 23 distinct vessels; one vessel (MORNING LORD) supplies 9 events and all 5 of its `real` labels come from the same trawl pattern.
  - **Limited coverage:** terrestrial receivers only; one day; one region.
  - **Labels saw the rule:** labels were made while looking at the rule's own features.

## 9. Known issues and limitations
- **Gaps need a report on both sides.** Vessels that go dark and never return within the day, or first appear mid-box, are missed. The day+1 and day−1 files would fix this.
- **Coverage cells are too coarse here.** `coverage_during_gap` uses 0.1° cells, about 18 nm across with neighbours, and is 1.0 for 509 of 515 gaps. Labelling therefore relied on a finer check: other vessels heard within 3 nm. A Class B-specific check would be better still, since Class B units transmit 2 W against Class A's 12.5 W.
- **GPS speed noise beats the port rule.** The moving-ship exception added in block 3 relies on speed at both ends. A moored boat reporting 2.4 kn of GPS noise (A-TEAM, #24) escaped the port suppressor. LONGHORN's silence at its spot scored rank 2 or rank 157 depending only on the speeds caught at the two ends.
- **Episodes are not merged.** ACCP 1's single episode appears twice (#50 then #1, split by one isolated report).
- **No per-vessel reception baseline.** The most common false alarm is a unit that is on but poorly received ("flicker"). The scoring rule doesn't model it.
- **Excel can't open the raw file.** The raw CSV (7.8 M rows) is about 7× Excel's row limit, so checks in Excel silently miss most of the day. Use DuckDB, as in `scripts/profile_day.py`.
- **Planned report script not built.** `report.py` (automatic DATA.md tables) was cut for time; the label tables above were computed once and pasted in.

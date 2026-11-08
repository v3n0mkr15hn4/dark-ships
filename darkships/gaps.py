"""Find every transmission gap: consecutive pings of one vessel further apart than expected.

Expected interval E (state at the ping BEFORE the gap, see PLAN.md section 4):
  Class A, underway (sog >= 0.5, status not anchored/moored) -> expected_fast_s (60 s)
  Class A, otherwise                                         -> expected_slow_s (180 s)
  Class B or unknown, sog > 2 kn                             -> expected_fast_s (60 s)
  Class B or unknown, otherwise (incl. sog unknown)          -> expected_slow_s (180 s)
Gap if  gap_s >= max(gap_min_s, k * E).  Only gaps with an endpoint inside the bbox are kept.
"""
from darkships.ingest import bbox_sql


def expected_interval_sql(cfg):
    g = cfg["gaps"]
    return f"""
        CASE
          WHEN transceiver0 = 'A' AND sog0 >= {g['class_a_underway_min_kn']}
               AND coalesce(status0, -1) NOT IN (1, 5)          THEN {g['expected_fast_s']}
          WHEN transceiver0 = 'A'                               THEN {g['expected_slow_s']}
          WHEN sog0 > {g['class_b_moving_min_kn']}              THEN {g['expected_fast_s']}
          ELSE {g['expected_slow_s']}
        END"""


def find_gaps(con, cfg, tracks="tracks", k=None):
    """Return a DataFrame with one row per gap. `k` overrides the config (used for sensitivity)."""
    g = cfg["gaps"]
    k = g["k"] if k is None else k
    return con.execute(f"""
        WITH pairs AS (
            SELECT mmsi,
                   lag(base_date_time) OVER w AS t0,  base_date_time AS t1,
                   lag(latitude)       OVER w AS lat0, latitude       AS lat1,
                   lag(longitude)      OVER w AS lon0, longitude      AS lon1,
                   lag(sog)            OVER w AS sog0, sog            AS sog1,
                   lag(cog)            OVER w AS cog0, cog            AS cog1,
                   lag(heading)        OVER w AS hdg0, heading        AS hdg1,
                   lag(status)         OVER w AS status0, status      AS status1,
                   lag(transceiver)    OVER w AS transceiver0,
                   vessel_name, imo, call_sign, vessel_type, length
            FROM {tracks}
            WINDOW w AS (PARTITION BY mmsi ORDER BY base_date_time)
        ),
        timed AS (
            SELECT *,
                   date_diff('second', t0, t1)        AS gap_s,
                   {expected_interval_sql(cfg)}       AS expected_interval_s
            FROM pairs
            WHERE t0 IS NOT NULL                       -- first ping of the day starts no gap
        )
        SELECT mmsi, t0, t1, gap_s, expected_interval_s,
               gap_s / expected_interval_s             AS gap_ratio,
               lat0, lon0, lat1, lon1, sog0, sog1, cog0, cog1, hdg0, hdg1,
               status0, status1, transceiver0 AS transceiver,
               vessel_name, imo, call_sign, vessel_type, length,
               {bbox_sql(cfg, 'lat0', 'lon0')}         AS p0_in_bbox,
               {bbox_sql(cfg, 'lat1', 'lon1')}         AS p1_in_bbox
        FROM timed
        WHERE gap_s >= greatest({g['gap_min_s']}, {k} * expected_interval_s)
          AND ({bbox_sql(cfg, 'lat0', 'lon0')} OR {bbox_sql(cfg, 'lat1', 'lon1')})
        ORDER BY mmsi, t0
    """).df()

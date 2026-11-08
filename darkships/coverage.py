"""Was this area reachable by the receivers while the ship was silent?

Presence grid (from table `universe` = all vessels in bbox + margin):
    (0.1 deg cell, 10-min bucket) -> n_pings, n_mmsi (distinct), min_mmsi

For a gap of vessel X from t0 to t1:
  coverage_during_gap = share of 10-min buckets overlapping [t0, t1] in which the 3x3 cells
                        around p0 OR around p1 contain a ping from a vessel other than X
  heard_today         = the same test over ALL buckets of the day

"A vessel other than X is in the cell" <=> n_mmsi >= 2 OR min_mmsi <> X.
(Exact: one vessel that is not X, or two+ vessels of which at most one is X.)
"""


def build_presence_grid(con, cfg):
    f = cfg["features"]
    con.execute(f"""
        CREATE OR REPLACE TABLE grid AS
        SELECT floor(longitude * {f['grid_cells_per_deg']})::INT AS cx,
               floor(latitude  * {f['grid_cells_per_deg']})::INT AS cy,
               time_bucket(INTERVAL '{f['bucket_minutes']} minutes', base_date_time) AS b,
               count(*) AS n_pings, count(DISTINCT mmsi) AS n_mmsi, min(mmsi) AS min_mmsi
        FROM universe GROUP BY ALL""")
    return con.execute("SELECT count(*) FROM grid").fetchone()[0]


def register_gap_points(con, events):
    """Expose the gap endpoints to DuckDB as view `gap_points`."""
    g = events[["event_id", "mmsi", "t0", "t1", "lat0", "lon0", "lat1", "lon1"]].copy()
    g["t0"] = g["t0"].dt.tz_localize(None)   # DuckDB timestamps are naive UTC
    g["t1"] = g["t1"].dt.tz_localize(None)
    con.register("gap_points", g)


def coverage(con, cfg, events):
    """Return event_id, n_buckets, n_buckets_covered, coverage_during_gap, heard_today."""
    f = cfg["features"]
    n, step = f["grid_cells_per_deg"], f"INTERVAL '{f['bucket_minutes']} minutes'"
    register_gap_points(con, events)

    near = """((abs(gr.cx - e.cx0) <= 1 AND abs(gr.cy - e.cy0) <= 1)
            OR (abs(gr.cx - e.cx1) <= 1 AND abs(gr.cy - e.cy1) <= 1))"""
    other_vessel = "(gr.n_mmsi >= 2 OR gr.min_mmsi <> e.mmsi)"
    return con.execute(f"""
        WITH e AS (
            SELECT event_id, mmsi, t0, t1,
                   floor(lon0 * {n})::INT AS cx0, floor(lat0 * {n})::INT AS cy0,
                   floor(lon1 * {n})::INT AS cx1, floor(lat1 * {n})::INT AS cy1
            FROM gap_points),
        buckets AS (            -- every 10-min bucket that overlaps [t0, t1]
            SELECT e.*, unnest(generate_series(time_bucket({step}, t0),
                                               time_bucket({step}, t1), {step})) AS b
            FROM e),
        per_bucket AS (
            SELECT e.event_id, e.b, coalesce(bool_or({other_vessel}), false) AS covered
            FROM buckets e LEFT JOIN grid gr ON gr.b = e.b AND {near}
            WHERE e.b < e.t1
            GROUP BY ALL),
        during AS (
            SELECT event_id, count(*) AS n_buckets,
                   count(*) FILTER (covered) AS n_buckets_covered
            FROM per_bucket GROUP BY ALL),
        today AS (
            SELECT e.event_id, coalesce(bool_or({other_vessel}), false) AS heard_today
            FROM e LEFT JOIN grid gr ON {near}
            GROUP BY ALL)
        SELECT during.*, n_buckets_covered / n_buckets AS coverage_during_gap, heard_today
        FROM during JOIN today USING (event_id)
    """).df()


def cell_context(con, cfg, events):
    """Display/suppressor context per endpoint: traffic density and berth/anchorage cells."""
    f = cfg["features"]
    n, s = f["grid_cells_per_deg"], f["stationary_cells_per_deg"]
    register_gap_points(con, events)
    stationary = (f"(st.med < {f['stationary_max_median_kn']} "
                  f"AND st.n >= {f['stationary_min_pings']})")
    return con.execute(f"""
        WITH dens AS (
            SELECT floor(longitude * {n})::INT AS cx, floor(latitude * {n})::INT AS cy,
                   count(DISTINCT mmsi) AS n
            FROM universe GROUP BY ALL),
        stat AS (
            SELECT floor(longitude * {s})::INT AS sx, floor(latitude * {s})::INT AS sy,
                   median(sog) AS med, count(*) AS n
            FROM universe GROUP BY ALL)
        SELECT p.event_id,
               coalesce(d0.n, 0) AS cell_density0, coalesce(d1.n, 0) AS cell_density1,
               coalesce({stationary.replace('st.', 's0.')}, false)
                 OR coalesce({stationary.replace('st.', 's1.')}, false) AS stationary_cell
        FROM gap_points p
        LEFT JOIN dens d0 ON d0.cx = floor(p.lon0 * {n})::INT AND d0.cy = floor(p.lat0 * {n})::INT
        LEFT JOIN dens d1 ON d1.cx = floor(p.lon1 * {n})::INT AND d1.cy = floor(p.lat1 * {n})::INT
        LEFT JOIN stat s0 ON s0.sx = floor(p.lon0 * {s})::INT AND s0.sy = floor(p.lat0 * {s})::INT
        LEFT JOIN stat s1 ON s1.sx = floor(p.lon1 * {s})::INT AND s1.sy = floor(p.lat1 * {s})::INT
    """).df()

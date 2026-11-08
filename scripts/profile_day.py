"""Block 1: look at the raw day before trusting it.

Converts the raw .csv.zst to data/interim/raw.parquet once (reused by run.py later),
then prints a markdown profile: schema, counts, nulls, sentinels, MMSI classes,
duplicates, and an hourly profile of the bounding box (outage / fog check).

Usage:  python scripts/profile_day.py [--config config.toml]
"""
import argparse
import time
import tomllib
from pathlib import Path

import duckdb


def connect(cfg):
    tmp = Path(cfg["data"]["interim_dir"]) / "duckdb_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{cfg['duckdb']['memory_limit']}'")
    con.execute(f"SET threads={cfg['duckdb']['threads']}")
    con.execute(f"SET temp_directory='{tmp.as_posix()}'")
    con.execute("SET preserve_insertion_order=false")  # lets DuckDB stream without buffering
    return con


def raw_to_parquet(con, raw, parquet):
    """One pass over the compressed CSV. Skipped if the parquet already exists."""
    if parquet.exists():
        print(f"_reusing {parquet}_\n")
        return
    t = time.time()
    con.execute(f"""
        COPY (SELECT * FROM read_csv('{raw.as_posix()}', header=true))
        TO '{parquet.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
    """)
    print(f"_converted to parquet in {time.time() - t:.0f}s, "
          f"{parquet.stat().st_size / 2**20:.0f} MB_\n")


def table(con, title, sql):
    df = con.execute(sql).df()
    print(f"### {title}\n")
    print(df.to_string(index=False) if len(df) else "_(no rows)_")
    print()
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.toml")
    cfg = tomllib.loads(Path(ap.parse_args().config).read_text())

    raw = Path(cfg["data"]["raw_file"])
    parquet = Path(cfg["data"]["interim_dir"]) / "raw.parquet"
    b = cfg["bbox"]
    in_bbox = (f"latitude BETWEEN {b['lat_min']} AND {b['lat_max']} "
               f"AND longitude BETWEEN {b['lon_min']} AND {b['lon_max']}")

    con = connect(cfg)
    print(f"# Profile of {raw.name}\n")
    table(con, "Raw CSV schema (as DuckDB sniffs it)",
          f"DESCRIBE SELECT * FROM read_csv('{raw.as_posix()}', header=true)")
    raw_to_parquet(con, raw, parquet)
    con.execute(f"CREATE VIEW raw AS SELECT * FROM read_parquet('{parquet.as_posix()}')")

    table(con, "Whole file", """
        SELECT count(*) AS rows, count(DISTINCT mmsi) AS mmsi,
               min(base_date_time) AS first_ts, max(base_date_time) AS last_ts
        FROM raw""")

    table(con, "Null share per column (%)", """
        UNPIVOT (SELECT round(100 * avg(CASE WHEN COLUMNS(*) IS NULL THEN 1 ELSE 0 END), 2) FROM raw)
        ON COLUMNS(*) INTO NAME column_name VALUE null_pct""")

    table(con, "Sentinel / out-of-range values still present", """
        SELECT count(*) FILTER (sog >= 102.2)            AS sog_ge_102_2,
               count(*) FILTER (heading > 359)           AS heading_gt_359,
               count(*) FILTER (cog >= 360)              AS cog_ge_360,
               count(*) FILTER (abs(latitude) > 90)      AS bad_lat,
               count(*) FILTER (abs(longitude) > 180)    AS bad_lon,
               count(*) FILTER (sog > 50)                AS sog_gt_50
        FROM raw""")

    table(con, "MMSI classes", """
        SELECT CASE
                 WHEN mmsi BETWEEN 201000000 AND 775999999 THEN 'ship (MID 2xx-7xx)'
                 WHEN mmsi < 100000000                     THEN '<9 digits (base station / bad)'
                 WHEN mmsi BETWEEN 990000000 AND 999999999 THEN 'AtoN 99x'
                 WHEN mmsi BETWEEN 970000000 AND 979999999 THEN 'SART/MOB/EPIRB 97x'
                 WHEN mmsi BETWEEN 111000000 AND 111999999 THEN 'SAR aircraft 111'
                 ELSE 'other 9-digit' END AS mmsi_class,
               count(*) AS rows, count(DISTINCT mmsi) AS mmsi
        FROM raw GROUP BY 1 ORDER BY rows DESC""")

    table(con, "Duplicates", """
        SELECT (SELECT count(*) FROM raw) - (SELECT count(*) FROM (SELECT DISTINCT * FROM raw))
                   AS exact_duplicate_rows,
               (SELECT count(*) FROM (SELECT mmsi, base_date_time FROM raw
                                      GROUP BY ALL HAVING count(*) > 1))
                   AS mmsi_time_keys_with_2plus_rows""")

    table(con, "Transceiver class", """
        SELECT transceiver, count(*) AS rows, count(DISTINCT mmsi) AS mmsi
        FROM raw GROUP BY 1 ORDER BY rows DESC""")

    table(con, "Bounding box", f"""
        SELECT count(*) AS rows, count(DISTINCT mmsi) AS mmsi,
               count(DISTINCT mmsi) FILTER (transceiver = 'A') AS mmsi_class_a,
               count(DISTINCT mmsi) FILTER (transceiver = 'B') AS mmsi_class_b
        FROM raw WHERE {in_bbox}""")

    table(con, "Bounding box: vessel type groups (distinct MMSI)", f"""
        SELECT CASE WHEN vessel_type BETWEEN 80 AND 89 THEN 'tanker'
                    WHEN vessel_type BETWEEN 70 AND 79 THEN 'cargo'
                    WHEN vessel_type = 30 THEN 'fishing'
                    WHEN vessel_type IN (31, 32, 52) THEN 'tug/tow'
                    WHEN vessel_type BETWEEN 60 AND 69 THEN 'passenger'
                    WHEN vessel_type IN (36, 37) THEN 'pleasure/sail'
                    WHEN vessel_type IS NULL THEN 'unknown'
                    ELSE 'other' END AS vessel_group,
               count(DISTINCT mmsi) AS mmsi
        FROM raw WHERE {in_bbox} GROUP BY 1 ORDER BY mmsi DESC""")

    table(con, "Bounding box: hourly profile (UTC) - outage / fog check", f"""
        SELECT hour(base_date_time) AS hour_utc,
               count(*) AS rows,
               count(DISTINCT mmsi) AS mmsi,
               count(DISTINCT mmsi) FILTER (status IN (1, 5)) AS mmsi_anchored_or_moored,
               round(100 * avg(CASE WHEN sog < 0.5 THEN 1 ELSE 0 END), 1) AS pct_pings_sog_lt_0_5
        FROM raw WHERE {in_bbox} GROUP BY 1 ORDER BY 1""")


if __name__ == "__main__":
    main()

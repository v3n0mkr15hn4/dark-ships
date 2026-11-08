"""Read the raw day once, then cut out the two working sets.

- tracks:   full national-day track of every vessel seen at least once inside the bbox
- universe: every vessel's pings inside the bbox + margin (used later for the coverage test)
"""
import time
from pathlib import Path

import duckdb


def connect(cfg):
    """DuckDB connection with a memory cap; spills to data/interim/duckdb_tmp if needed."""
    tmp = Path(cfg["data"]["interim_dir"]) / "duckdb_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{cfg['duckdb']['memory_limit']}'")
    con.execute(f"SET threads={cfg['duckdb']['threads']}")
    con.execute(f"SET temp_directory='{tmp.as_posix()}'")
    con.execute("SET preserve_insertion_order=false")
    return con


def bbox_sql(cfg, lat="latitude", lon="longitude", margin=0.0):
    """SQL condition: point (lat, lon) inside the bbox, optionally widened by `margin` degrees."""
    b = cfg["bbox"]
    return (f"({lat} BETWEEN {b['lat_min'] - margin} AND {b['lat_max'] + margin} "
            f"AND {lon} BETWEEN {b['lon_min'] - margin} AND {b['lon_max'] + margin})")


def load_raw(con, cfg, force=False):
    """Convert the raw .csv.zst to parquet once (slow step), then expose it as view `raw`."""
    raw = Path(cfg["data"]["raw_file"])
    parquet = Path(cfg["data"]["interim_dir"]) / "raw.parquet"
    if force or not parquet.exists():
        t = time.time()
        con.execute(f"""
            COPY (SELECT * FROM read_csv('{raw.as_posix()}', header=true))
            TO '{parquet.as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")
        print(f"  raw -> {parquet} in {time.time() - t:.0f}s")
    else:
        print(f"  reusing cached {parquet} (pass --force to rebuild)")
    con.execute(f"CREATE OR REPLACE VIEW raw AS SELECT * FROM read_parquet('{parquet.as_posix()}')")


def select_tracks_and_universe(con, cfg):
    """From table `clean`, build tables `tracks` and `universe` and save both as parquet."""
    interim = Path(cfg["data"]["interim_dir"])
    margin = cfg["bbox"]["presence_margin_deg"]

    con.execute(f"CREATE OR REPLACE TABLE bbox_mmsi AS "
                f"SELECT DISTINCT mmsi FROM clean WHERE {bbox_sql(cfg)}")
    con.execute("CREATE OR REPLACE TABLE tracks AS "
                "SELECT * FROM clean WHERE mmsi IN (SELECT mmsi FROM bbox_mmsi)")
    con.execute(f"CREATE OR REPLACE TABLE universe AS "
                f"SELECT mmsi, base_date_time, latitude, longitude, sog "
                f"FROM clean WHERE {bbox_sql(cfg, margin=margin)}")

    for name in ("tracks", "universe"):
        con.execute(f"COPY {name} TO '{(interim / f'{name}.parquet').as_posix()}' (FORMAT parquet)")

    return {
        "bbox_vessels": con.execute("SELECT count(*) FROM bbox_mmsi").fetchone()[0],
        "track_rows": con.execute("SELECT count(*) FROM tracks").fetchone()[0],
        "universe_rows": con.execute("SELECT count(*) FROM universe").fetchone()[0],
        "universe_vessels": con.execute("SELECT count(DISTINCT mmsi) FROM universe").fetchone()[0],
    }

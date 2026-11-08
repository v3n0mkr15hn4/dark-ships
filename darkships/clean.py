"""Clean the raw pings: real ship MMSIs, valid positions, sentinels -> NULL, one row per (mmsi, minute)."""


def mmsi_ok_sql(cfg):
    """SQL condition for a real ship MMSI (9 digits, MID 201-775, not on the denylist)."""
    c = cfg["clean"]
    cond = f"mmsi BETWEEN {c['mmsi_min']} AND {c['mmsi_max']}"
    if c["mmsi_denylist"]:
        cond += f" AND mmsi NOT IN ({', '.join(str(m) for m in c['mmsi_denylist'])})"
    return f"({cond})"


POSITION_OK = ("(latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180 "
               "AND NOT (latitude = 0 AND longitude = 0) AND base_date_time IS NOT NULL)")


def clean(con, cfg, src="raw", dst="clean"):
    """Create table `dst` from `src`. Returns row counts after each step."""
    mmsi_ok = mmsi_ok_sql(cfg)
    counts = con.execute(f"""
        SELECT count(*)                                   AS raw_rows,
               count(*) FILTER ({mmsi_ok})                AS valid_mmsi_rows,
               count(*) FILTER ({mmsi_ok} AND {POSITION_OK}) AS valid_position_rows
        FROM {src}""").df().iloc[0].to_dict()

    # Sentinels are already NULL in 2025+ files; these CASEs are cheap insurance.
    # Duplicates: keep one row per (mmsi, timestamp); exact copies and conflicting copies alike.
    con.execute(f"""
        CREATE OR REPLACE TABLE {dst} AS
        SELECT mmsi, base_date_time, latitude, longitude,
               CASE WHEN sog >= 102.2 THEN NULL ELSE sog END     AS sog,
               CASE WHEN cog >= 360 THEN NULL ELSE cog END       AS cog,
               CASE WHEN heading > 359 THEN NULL ELSE heading END AS heading,
               vessel_name, imo, call_sign, vessel_type, status, length, width, draft, cargo,
               transceiver
        FROM {src}
        WHERE {mmsi_ok} AND {POSITION_OK}
        QUALIFY row_number() OVER (PARTITION BY mmsi, base_date_time
                                   ORDER BY latitude, longitude, sog) = 1""")
    counts["dedup_rows"] = con.execute(f"SELECT count(*) FROM {dst}").fetchone()[0]
    return {k: int(v) for k, v in counts.items()}

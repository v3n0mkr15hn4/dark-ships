"""Per-gap features: the ones the brief requires, then the extras that separate real from innocent."""
import numpy as np
import pandas as pd

from darkships.coverage import cell_context, coverage
from darkships.geo import angle_diff_deg, haversine_nm


def vessel_group(vessel_type):
    """Map an NMEA vessel-type code to a readable group."""
    if pd.isna(vessel_type):
        return "unknown"
    t = int(vessel_type)
    if 80 <= t <= 89:
        return "tanker"
    if 70 <= t <= 79:
        return "cargo"
    if t == 30:
        return "fishing"
    if t in (31, 32, 52):
        return "tug_tow"
    if 60 <= t <= 69:
        return "passenger"
    if t in (36, 37):
        return "pleasure_sail"
    return "other"


def add_required_features(gaps):
    """Distance, implied speed, ids and groups. Input/output: one row per gap."""
    df = gaps.copy()
    df["t0"] = pd.to_datetime(df["t0"]).dt.tz_localize("UTC")
    df["t1"] = pd.to_datetime(df["t1"]).dt.tz_localize("UTC")
    df.insert(0, "event_id", df["mmsi"].astype(str) + "_" + df["t0"].dt.strftime("%Y%m%dT%H%M%S"))
    df["dist_nm"] = haversine_nm(df["lat0"], df["lon0"], df["lat1"], df["lon1"])
    df["implied_kn"] = df["dist_nm"] / (df["gap_s"] / 3600)
    df["vessel_group"] = df["vessel_type"].map(vessel_group)
    df["transceiver"] = df["transceiver"].fillna("unknown")
    assert df["event_id"].is_unique, "event_id must be unique"
    assert (df["gap_s"] > 0).all() and np.isfinite(df["implied_kn"]).all()
    return df


def vessel_stats(con, cfg):
    """Per vessel: typical speed (median SOG while moving) and share of impossible jumps."""
    f = cfg["features"]
    tr = con.execute("SELECT mmsi, base_date_time AS t, latitude AS lat, longitude AS lon, sog "
                     "FROM tracks ORDER BY mmsi, base_date_time").df()
    typical = tr[tr["sog"] > 1].groupby("mmsi")["sog"].median().rename("typical_kn")

    prev = tr.groupby("mmsi")[["t", "lat", "lon"]].shift()
    dt_s = (tr["t"] - prev["t"]).dt.total_seconds()
    pair = (dt_s > 0) & (dt_s < f["jump_max_dt_s"])          # consecutive pings, no gap between
    speed = haversine_nm(prev["lat"], prev["lon"], tr["lat"], tr["lon"]) / (dt_s / 3600)
    jumps = (speed > f["teleport_kn"]) & pair
    jump_rate = (jumps.groupby(tr["mmsi"]).sum() / pair.groupby(tr["mmsi"]).sum()).rename("jump_rate")
    return pd.concat([typical, jump_rate], axis=1).reset_index()


def add_extra_features(df, con, cfg):
    """Coverage, context and behaviour features. See PLAN.md section 5 for each hypothesis."""
    f, b = cfg["features"], cfg["bbox"]
    df = df.merge(vessel_stats(con, cfg), on="mmsi", how="left")
    df = df.merge(coverage(con, cfg, df), on="event_id", how="left")
    df = df.merge(cell_context(con, cfg, df), on="event_id", how="left")

    gap_h = df["gap_s"] / 3600
    df["jump_rate"] = df["jump_rate"].fillna(0)
    df["mmsi_conflict"] = df["jump_rate"] > f["mmsi_conflict_jump_rate"]
    df["speed_ratio"] = df["implied_kn"] / df["typical_kn"]

    # Share of the gap not explained by a straight transit at the observed speed.
    mean_sog = df[["sog0", "sog1"]].mean(axis=1).where(lambda s: s > 0)
    df["unaccounted_frac"] = (1 - (df["dist_nm"] / mean_sog) / gap_h).clip(0, 1)

    # Semi-minor axis of the ellipse reachable from p0 to p1 at typical speed:
    # how far off the straight line the ship could have gone (out of range and back).
    reach_nm = df["typical_kn"] * gap_h
    df["max_excursion_nm"] = 0.5 * np.sqrt((reach_nm ** 2 - df["dist_nm"] ** 2).clip(lower=0))

    df["teleport"] = (df["implied_kn"] > f["teleport_kn"]) & ~df["vessel_type"].between(40, 49)
    df["dcog_deg"] = angle_diff_deg(df["cog0"], df["cog1"])
    df["n_gaps_vessel"] = df.groupby("mmsi")["event_id"].transform("count")
    df["hour_utc"] = df["t0"].dt.hour

    def edge_nm(lat, lon):  # distance to nearest bbox side, 0 if outside
        cos = np.cos(np.radians(lat))
        d = np.minimum.reduce([lat - b["lat_min"], b["lat_max"] - lat,
                               (lon - b["lon_min"]) * cos, (b["lon_max"] - lon) * cos]) * 60
        return np.clip(d, 0, None)
    df["bbox_edge_nm"] = np.minimum(edge_nm(df["lat0"], df["lon0"]), edge_nm(df["lat1"], df["lon1"]))
    minutes0 = df["t0"].dt.hour * 60 + df["t0"].dt.minute
    minutes1 = df["t1"].dt.hour * 60 + df["t1"].dt.minute
    df["near_day_boundary"] = (minutes0 < 30) | (minutes1 > 23 * 60 + 30)

    for col in ("heard_today", "stationary_cell"):
        df[col] = df[col].fillna(False).astype(bool)
    return df

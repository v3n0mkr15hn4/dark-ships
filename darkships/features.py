"""Per-gap features. Block 2 = the features the brief requires; extras arrive in block 3."""
import numpy as np
import pandas as pd

from darkships.geo import haversine_nm


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

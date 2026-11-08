"""Gap detection on small synthetic tracks, run through the real clean -> select -> gaps SQL."""
import tomllib
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from darkships.clean import clean
from darkships.coverage import build_presence_grid, coverage
from darkships.features import add_required_features
from darkships.gaps import find_gaps
from darkships.ingest import select_tracks_and_universe
from darkships.score import coverage_term

ROOT = Path(__file__).resolve().parents[1]
DAY = pd.Timestamp("2026-04-15")


@pytest.fixture
def cfg(tmp_path):
    cfg = tomllib.loads((ROOT / "config.toml").read_text())
    cfg["data"]["interim_dir"] = str(tmp_path)  # keep test parquet out of the real data folder
    return cfg


def pings(mmsi=367000001, minutes=range(60), sog=10.0, status=0, transceiver="A",
          lat=29.0, lon=-94.5, start="00:00"):
    """One ping per entry in `minutes` (minutes after `start`), drifting north inside the bbox."""
    t0 = DAY + pd.Timedelta(start + ":00")
    rows = [{
        "mmsi": mmsi, "base_date_time": t0 + pd.Timedelta(minutes=m),
        "longitude": lon, "latitude": lat + 0.001 * i,
        "sog": sog, "cog": 0.0, "heading": 0, "vessel_name": "TEST", "imo": None,
        "call_sign": None, "vessel_type": 80, "status": status, "length": 200, "width": 30,
        "draft": 10.0, "cargo": 80, "transceiver": transceiver,
    } for i, m in enumerate(minutes)]
    return pd.DataFrame(rows)


def run_gaps(df, cfg):
    con = duckdb.connect()
    con.register("raw_df", df)
    con.execute("CREATE TABLE raw AS SELECT * FROM raw_df")
    clean(con, cfg)
    select_tracks_and_universe(con, cfg)
    return find_gaps(con, cfg)


HOLE = [*range(0, 21), *range(50, 60)]  # 1-min pings with silence 00:20 -> 00:50


def test_one_hole_gives_one_gap_of_right_length(cfg):
    g = run_gaps(pings(minutes=HOLE), cfg)
    assert len(g) == 1 and g.loc[0, "gap_s"] == 30 * 60


def test_shuffled_input_gives_same_gaps(cfg):
    g = run_gaps(pings(minutes=HOLE).sample(frac=1, random_state=1), cfg)
    assert len(g) == 1 and g.loc[0, "gap_s"] == 30 * 60


def test_duplicate_rows_give_same_gaps(cfg):
    df = pings(minutes=HOLE)
    g = run_gaps(pd.concat([df, df, df.head(5)]), cfg)
    assert len(g) == 1 and g.loc[0, "gap_s"] == 30 * 60


def test_anchored_vessel_reporting_every_20_min_has_no_gaps(cfg):
    df = pings(minutes=range(0, 360, 20), sog=0.0, status=1)
    assert len(run_gaps(df, cfg)) == 0


def test_track_ending_at_23_00_has_no_trailing_gap(cfg):
    df = pings(minutes=range(61), start="22:00")  # last ping exactly 23:00
    assert len(run_gaps(df, cfg)) == 0


def test_aton_mmsi_is_removed_by_clean(cfg):
    g = run_gaps(pings(mmsi=993123456, minutes=HOLE), cfg)
    assert len(g) == 0


# --- coverage hole (PLAN.md section 10, case 5) -------------------------------------------

def run_coverage(df, cfg):
    """Gap of vessel X (00:20 -> 00:50, buckets 00:20, 00:30, 00:40) plus its coverage features."""
    con = duckdb.connect()
    con.register("raw_df", df)
    con.execute("CREATE TABLE raw AS SELECT * FROM raw_df")
    clean(con, cfg)
    select_tracks_and_universe(con, cfg)
    build_presence_grid(con, cfg)
    ev = add_required_features(find_gaps(con, cfg))
    ev = ev.merge(coverage(con, cfg, ev), on="event_id")
    assert len(ev) == 1
    row = ev.iloc[0]
    c = coverage_term(row["coverage_during_gap"], row["heard_today"], cfg["score"]["quiet_coverage_c"])
    return row, float(c)


X = dict(mmsi=367000001, minutes=HOLE)
Y = dict(mmsi=367000002, lat=29.01)  # another vessel in the same cell as X


def test_other_vessel_heard_during_gap_means_covered(cfg):
    row, c = run_coverage(pd.concat([pings(**X), pings(**Y, minutes=range(60))]), cfg)
    assert row["n_buckets"] == 3 and row["coverage_during_gap"] == 1.0 and c == 1.0


def test_area_heard_only_outside_gap_is_neutral(cfg):
    row, c = run_coverage(pd.concat([pings(**X), pings(**Y, minutes=range(60, 70))]), cfg)
    assert row["coverage_during_gap"] == 0 and row["heard_today"] and c == 0.5


def test_no_other_vessel_all_day_is_a_coverage_hole(cfg):
    # Only X's own pings are in the cells: self-exclusion must not count them as coverage.
    row, c = run_coverage(pings(**X), cfg)
    assert row["coverage_during_gap"] == 0 and not row["heard_today"] and c == 0.0


def test_weak_coverage_never_scores_below_quiet(cfg):
    # Y heard in 1 of 3 buckets (00:31-00:35): C = max(1/3, 0.5) = 0.5, monotonic.
    row, c = run_coverage(pd.concat([pings(**X), pings(**Y, minutes=range(31, 36))]), cfg)
    assert row["n_buckets_covered"] == 1 and c == 0.5

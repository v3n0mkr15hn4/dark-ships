"""One command, whole pipeline:  python run.py --config config.toml  [--force]

raw .csv.zst -> (cached) parquet -> clean -> bbox vessels' tracks + universe
             -> presence grid -> gaps -> features -> score (+ ablation) -> out/events.parquet
"""
import argparse
import hashlib
import json
import time
import tomllib
from pathlib import Path

from darkships import PIPELINE_VERSION
from darkships.clean import clean
from darkships.coverage import build_presence_grid
from darkships.features import add_extra_features, add_required_features
from darkships.gaps import find_gaps
from darkships.ingest import connect, load_raw, select_tracks_and_universe
from darkships.score import ablation, score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.toml")
    ap.add_argument("--force", action="store_true", help="rebuild the cached raw parquet")
    args = ap.parse_args()

    cfg_text = Path(args.config).read_text()
    cfg = tomllib.loads(cfg_text)
    out = Path(cfg["data"]["out_dir"])
    out.mkdir(exist_ok=True)
    t = time.time()

    print("1/5 load raw")
    con = connect(cfg)
    load_raw(con, cfg, force=args.force)

    print("2/5 clean")
    counts = clean(con, cfg)

    print("3/5 select bbox vessels' tracks + presence universe + presence grid")
    counts |= select_tracks_and_universe(con, cfg)
    counts["grid_cell_buckets"] = build_presence_grid(con, cfg)

    print("4/5 gaps + features")
    gaps = find_gaps(con, cfg)
    counts["gaps"] = len(gaps)
    counts["gap_vessels"] = int(gaps["mmsi"].nunique())
    events = add_extra_features(add_required_features(gaps), con, cfg)

    print("5/5 score + ablation")
    events = score(events, cfg)
    events["config_hash"] = hashlib.sha256(cfg_text.encode()).hexdigest()[:8]
    events["pipeline_version"] = PIPELINE_VERSION
    events.to_parquet(out / "events.parquet", index=False)
    (out / "stage_counts.json").write_text(json.dumps(counts, indent=2))
    abl = ablation(events, cfg)
    abl.to_csv(out / "ablation.csv", index=False)

    print("\nStage counts:")
    for k, v in counts.items():
        print(f"  {k:<22}{v:>12,}")
    print(f"\nTop 10 of {len(events):,} gaps:")
    cols = ["rank", "score", "mmsi", "vessel_group", "transceiver", "gap_s", "sog0",
            "dist_nm", "coverage_during_gap", "heard_today", "D", "C", "U", "K", "T", "suppressors"]
    print(events[cols].head(10).to_string(index=False))
    print("\nAblation (top-50 overlap when one part is removed):")
    print(abl.to_string(index=False))
    print(f"\nwrote {out / 'events.parquet'} "
          f"({(out / 'events.parquet').stat().st_size / 2**20:.1f} MB) in {time.time() - t:.0f}s")


if __name__ == "__main__":
    main()

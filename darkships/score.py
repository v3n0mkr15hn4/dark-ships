"""Suspicion score. Block 2 = crude D x U (steel thread); the full rule arrives in block 3."""
import numpy as np


def duration_term(gap_ratio):
    """D: log-scaled silence relative to the expected interval, 0..1 (ratio 1000 -> 1)."""
    return np.clip(np.log10(gap_ratio) / 3, 0, 1)


def underway_term(sog0, status0):
    """U: 1 if the vessel was moving (>= 2 kn) and not anchored/moored when it went silent."""
    return ((sog0 >= 2) & ~status0.isin([1, 5])).astype(float)


def crude_score(df):
    """score = 100 * D * U, then rank (1 = most suspicious; ties broken by longer gap)."""
    df = df.copy()
    df["D"] = duration_term(df["gap_ratio"])
    df["U"] = underway_term(df["sog0"], df["status0"])
    df["score"] = (100 * df["D"] * df["U"]).round(1)
    df = df.sort_values(["score", "gap_s"], ascending=False).reset_index(drop=True)
    df["rank"] = np.arange(1, len(df) + 1)
    return df

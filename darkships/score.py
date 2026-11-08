"""Suspicion score (PLAN.md section 6).

score = 100 * (wD*D + wC*C + wU*U + wK*K + wT*T) * product(suppressor factors)

  D  duration          clip(log10(gap_ratio) / 3, 0, 1)
  C  coverage          max(coverage_during_gap, 0.5 if heard_today else 0)
  U  underway          1 if sog0 >= 2 kn and status0 not anchored/moored
  K  unaccounted time  unaccounted_frac (0 if speed unknown)
  T  type prior        1 Class A tanker/cargo/fishing, 0.6 other Class A, 0.3 Class B/unknown

Suppressors (known false alarms): coverage hole, port/berth/anchorage, teleport, MMSI conflict.
All weights and thresholds live in config.toml.
"""
import copy

import numpy as np
import pandas as pd

TERMS = ["D", "C", "U", "K", "T"]
SUPPRESSORS = ["coverage_hole", "port", "teleport", "mmsi_conflict"]


def duration_term(gap_ratio):
    """D: log-scaled silence relative to the expected interval, 0..1 (ratio 1000 -> 1)."""
    return np.clip(np.log10(gap_ratio) / 3, 0, 1)


def coverage_term(coverage_during_gap, heard_today, quiet_c=0.5):
    """C: others heard here during the gap; never below quiet_c if the area was heard today."""
    return np.maximum(np.nan_to_num(coverage_during_gap, nan=0.0),
                      np.where(heard_today, quiet_c, 0.0))


def underway_term(sog0, status0, min_kn=2.0):
    """U: 1 if the vessel was moving and not anchored/moored when it went silent."""
    return ((sog0 >= min_kn) & ~status0.isin([1, 5])).astype(float)


def type_term(transceiver, vessel_group, s):
    """T: commercial Class A vessels must transmit; Class B leisure boats switch off routinely."""
    class_a = transceiver.eq("A")
    priority = vessel_group.isin(s["priority_groups"])
    return np.select([class_a & priority, class_a],
                     [s["t_class_a_priority"], s["t_class_a_other"]], s["t_other"])


def suppressor_flags(df, s):
    """One boolean column per known false-alarm type."""
    anchored_both = df["status0"].isin([1, 5]) & df["status1"].isin([1, 5])
    stopped_both = (df["sog0"] < s["port_max_sog_kn"]) & (df["sog1"] < s["port_max_sog_kn"])
    return pd.DataFrame({
        "coverage_hole": ~df["heard_today"],
        "port": df["stationary_cell"] | (anchored_both & (df["dist_nm"] < s["port_max_dist_nm"]))
                | stopped_both,
        "teleport": df["teleport"],
        "mmsi_conflict": df["mmsi_conflict"],
    }, index=df.index)


def score(df, cfg):
    """Add D, C, U, K, T, suppressor flags, suppress_factor, score and rank; sort by rank."""
    s = cfg["score"]
    w, factors = s["weights"], s["factors"]
    df = df.copy()
    df["D"] = duration_term(df["gap_ratio"])
    df["C"] = coverage_term(df["coverage_during_gap"], df["heard_today"], s["quiet_coverage_c"])
    df["U"] = underway_term(df["sog0"], df["status0"], s["underway_min_kn"])
    df["K"] = df["unaccounted_frac"].fillna(0)
    df["T"] = type_term(df["transceiver"], df["vessel_group"], s)

    flags = suppressor_flags(df, s)
    df["suppress_factor"] = np.prod([np.where(flags[k], factors[k], 1.0) for k in SUPPRESSORS], axis=0)
    df["suppressors"] = flags.apply(lambda r: ",".join(k for k in SUPPRESSORS if r[k]), axis=1)
    for k in SUPPRESSORS:
        df[f"sup_{k}"] = flags[k]

    weighted = sum(w[t] * df[t] for t in TERMS)
    df["score"] = (100 * weighted * df["suppress_factor"]).round(1)
    df = df.sort_values(["score", "gap_s"], ascending=False).reset_index(drop=True)
    df["rank"] = np.arange(1, len(df) + 1)
    return df


def ablation(df, cfg, n=50):
    """Remove one term (weight 0) or one suppressor (factor 1) at a time; compare the top n."""
    base = set(score(df, cfg)["event_id"].head(n))
    rows = []
    for kind, names, section, off in (("term", TERMS, "weights", 0.0),
                                      ("suppressor", SUPPRESSORS, "factors", 1.0)):
        for name in names:
            c = copy.deepcopy(cfg)
            c["score"][section][name] = off
            top = set(score(df, c)["event_id"].head(n))
            rows.append({"removed": f"{kind} {name}", "top50_kept": len(base & top),
                         "jaccard": round(len(base & top) / len(base | top), 2)})
    return pd.DataFrame(rows)

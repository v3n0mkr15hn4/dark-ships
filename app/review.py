"""Review app with two pages:
  Dashboard      - results overview from out/events.parquet + out/labels.jsonl (app/dashboard.py)
  Review events  - one gap event at a time, map + context, label real / data_artefact / unsure

Run from the repo root:   streamlit run app/review.py
Use another labels file:  streamlit run app/review.py -- --labels path/to/labels.jsonl
Labels are appended to out/labels.jsonl; the review page resumes at the first unlabelled event.
"""
import argparse
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd
import pydeck as pdk
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import dashboard  # noqa: E402  (app/dashboard.py, same folder)
from darkships.labels import LABELS, append_label, first_unlabelled, load_labels  # noqa: E402

TOP_N = 50
REVIEWER = "vasanth"
LOCAL_TZ = "America/Chicago"           # vessel local time, shown next to UTC
EVENTS = ROOT / "out" / "events.parquet"
TRACKS = ROOT / "data" / "interim" / "tracks.parquet"
UNIVERSE = ROOT / "data" / "interim" / "universe.parquet"
CFG = tomllib.loads((ROOT / "config.toml").read_text())

STATUS = {0: "under way (engine)", 1: "at anchor", 2: "not under command", 3: "restricted",
          4: "constrained by draught", 5: "moored", 6: "aground", 7: "fishing",
          8: "under way (sail)", 11: "towing astern", 12: "pushing/towing alongside", 15: "undefined"}
BLUE, ORANGE, RED, GREY = [30, 100, 220], [240, 140, 20], [220, 30, 30], [90, 90, 90, 110]


def labels_path():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default=str(ROOT / "out" / "labels.jsonl"))
    return Path(ap.parse_known_args()[0].labels)


@st.cache_data
def load_all_events():
    return pd.read_parquet(EVENTS).sort_values("rank").reset_index(drop=True)


def load_events(n):
    return load_all_events().head(n).reset_index(drop=True)


@st.cache_data
def load_track(mmsi):
    return duckdb.execute(
        f"SELECT base_date_time AS t, latitude AS lat, longitude AS lon, sog "
        f"FROM read_parquet('{TRACKS.as_posix()}') WHERE mmsi = ? ORDER BY t", [int(mmsi)]).df()


@st.cache_data
def load_coverage_pings(mmsi, t0, t1, lat0, lon0, lat1, lon1):
    """Other vessels' pings in the 3x3 grid cells around p0 / p1 while this ship was silent."""
    n = CFG["features"]["grid_cells_per_deg"]
    near = lambda lat, lon: (f"(abs(floor(longitude*{n}) - floor({lon}*{n})) <= 1 "
                             f"AND abs(floor(latitude*{n}) - floor({lat}*{n})) <= 1)")
    return duckdb.execute(f"""
        SELECT mmsi, base_date_time AS t, latitude AS lat, longitude AS lon
        FROM read_parquet('{UNIVERSE.as_posix()}')
        WHERE mmsi <> ? AND base_date_time > ? AND base_date_time < ?
          AND ({near(lat0, lon0)} OR {near(lat1, lon1)})""",
        [int(mmsi), t0, t1]).df()


def fmt_time(ts):
    ts = pd.Timestamp(ts)
    return f"{ts:%H:%M} UTC ({ts.tz_convert(LOCAL_TZ):%H:%M} local)"


def fmt_dur(seconds):
    h, m = divmod(int(seconds) // 60, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def num(x, fmt="{:.1f}", none="–"):
    return none if pd.isna(x) else fmt.format(x)


def status_name(s):
    return "–" if pd.isna(s) else f"{int(s)} {STATUS.get(int(s), '')}"


def build_map(ev, track, cov):
    t0, t1 = ev.t0.tz_localize(None), ev.t1.tz_localize(None)
    before = track[track.t <= t0][["lon", "lat"]].values.tolist()
    after = track[track.t >= t1][["lon", "lat"]].values.tolist()
    b = CFG["bbox"]
    box = [[b["lon_min"], b["lat_min"]], [b["lon_max"], b["lat_min"]], [b["lon_max"], b["lat_max"]],
           [b["lon_min"], b["lat_max"]], [b["lon_min"], b["lat_min"]]]
    ends = pd.DataFrame({"lon": [ev.lon0, ev.lon1], "lat": [ev.lat0, ev.lat1],
                         "name": ["p0: last ping before gap", "p1: first ping after gap"],
                         "color": [BLUE, ORANGE]})
    layers = [
        pdk.Layer("PathLayer", [{"path": box, "name": "bounding box"}], get_path="path",
                  get_color=[0, 0, 0, 70], width_min_pixels=1),
        pdk.Layer("ScatterplotLayer", cov, get_position=["lon", "lat"], get_fill_color=GREY,
                  get_radius=60, radius_min_pixels=2, pickable=True),
        pdk.Layer("PathLayer", [{"path": before, "name": "track before gap"}], get_path="path",
                  get_color=BLUE, width_min_pixels=3, pickable=True),
        pdk.Layer("PathLayer", [{"path": after, "name": "track after gap"}], get_path="path",
                  get_color=ORANGE, width_min_pixels=3, pickable=True),
        pdk.Layer("LineLayer", [{"from": [ev.lon0, ev.lat0], "to": [ev.lon1, ev.lat1],
                                 "name": "gap (straight line p0 -> p1)"}],
                  get_source_position="from", get_target_position="to", get_color=RED,
                  get_width=3, pickable=True),
        pdk.Layer("ScatterplotLayer", ends, get_position=["lon", "lat"], get_fill_color="color",
                  get_radius=150, radius_min_pixels=6, pickable=True),
    ]
    # Centre on the gap and the hour of track either side of it.
    window = track[(track.t >= t0 - pd.Timedelta(hours=1)) & (track.t <= t1 + pd.Timedelta(hours=1))]
    pts = pd.concat([window[["lon", "lat"]], ends[["lon", "lat"]]]).values.tolist()
    view = pdk.data_utils.compute_view(pts, view_proportion=1)
    view.zoom = min(view.zoom, 13)
    return pdk.Deck(layers=layers, initial_view_state=view, map_provider="carto",
                    map_style=pdk.map_styles.CARTO_LIGHT, tooltip={"text": "{name}"})


def feature_card(ev):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Gap**")
        st.write(f"Silent {fmt_dur(ev.gap_s)}: {fmt_time(ev.t0)} → {fmt_time(ev.t1)}")
        st.write(f"Expected interval {int(ev.expected_interval_s)} s · ratio {ev.gap_ratio:.0f}×")
        st.write(f"Moved {ev.dist_nm:.2f} nm · implied {ev.implied_kn:.1f} kn "
                 f"(typical {num(ev.typical_kn)} kn)")
        st.write(f"Unaccounted time {num(ev.unaccounted_frac, '{:.0%}')} · "
                 f"max excursion {num(ev.max_excursion_nm)} nm")
    with c2:
        st.markdown("**Before → after**")
        st.write(f"SOG {num(ev.sog0)} → {num(ev.sog1)} kn")
        st.write(f"COG {num(ev.cog0, '{:.0f}')} → {num(ev.cog1, '{:.0f}')}° "
                 f"(Δ {num(ev.dcog_deg, '{:.0f}')}°) · heading {num(ev.hdg0, '{:.0f}')} → "
                 f"{num(ev.hdg1, '{:.0f}')}°")
        st.write(f"Status {status_name(ev.status0)} → {status_name(ev.status1)}")
        st.write(f"Stationary cell {'yes' if ev.stationary_cell else 'no'} · "
                 f"edge of box {ev.bbox_edge_nm:.1f} nm")
    with c3:
        st.markdown("**Coverage**")
        st.write(f"Others heard nearby in {int(ev.n_buckets_covered)} of {int(ev.n_buckets)} "
                 f"10-min slots ({ev.coverage_during_gap:.0%})")
        st.write(f"Heard nearby at any time today: {'yes' if ev.heard_today else 'no'}")
        st.write(f"Vessels in cell over the day: {int(ev.cell_density0)} (p0) · "
                 f"{int(ev.cell_density1)} (p1)")
        st.write(f"Gaps for this vessel today: {int(ev.n_gaps_vessel)}")
    w = CFG["score"]["weights"]   # ev["T"], not ev.T: on a pandas row .T means "transpose"
    st.markdown(f"**Score {ev.score:.1f}** = 100 × ({w['D']}·D {ev['D']:.2f} + {w['C']}·C {ev['C']:.2f} + "
                f"{w['U']}·U {ev['U']:.0f} + {w['K']}·K {ev['K']:.2f} + {w['T']}·T {ev['T']:.1f}) × "
                f"{ev.suppress_factor:.2f}   ·   suppressors: {ev.suppressors or 'none'}")


def review_page():
    path = labels_path()
    events = load_events(TOP_N)
    ids = events.event_id.tolist()
    labels = load_labels(path)

    if "idx" not in st.session_state:          # resume at the first unlabelled event
        nxt = first_unlabelled(ids, labels)
        st.session_state.idx = 0 if nxt is None else nxt

    with st.sidebar:
        st.header(f"Reviewed {sum(i in labels for i in ids)} / {len(ids)}")
        st.caption(f"Labels file: {path}")
        options = [f"#{r.rank}  {r.score:.1f}  "
                   f"{'unnamed' if pd.isna(r.vessel_name) else r.vessel_name} ({r.vessel_group})  "
                   f"{'✓ ' + labels[r.event_id]['label'] if r.event_id in labels else '·'}"
                   for r in events.itertuples()]
        pick = st.selectbox("Event", range(len(ids)), index=st.session_state.idx,
                            format_func=lambda i: options[i])
        if pick != st.session_state.idx:
            st.session_state.idx = pick
            st.rerun()
        nxt = first_unlabelled(ids, labels, start=st.session_state.idx)
        if st.button("Next unlabelled", disabled=nxt is None):
            st.session_state.idx = nxt
            st.rerun()

    ev = events.iloc[st.session_state.idx]
    name = "unnamed" if pd.isna(ev.vessel_name) else ev.vessel_name
    st.subheader(f"#{ev['rank']} · {name} · MMSI {ev.mmsi} · "
                 f"{ev.vessel_group} · Class {ev.transceiver} · {num(ev.length, '{:.0f}')} m")
    st.caption(f"event_id {ev.event_id}")
    current = labels.get(ev.event_id, {})
    if current:
        badge = {"real": "orange", "unsure": "green", "data_artefact": "blue"}[current["label"]]
        st.badge(f"Saved label: {dashboard.LABEL_NAME[current['label']]}", color=badge)
        st.markdown(f"**Note:** {current.get('note', '')}")
    else:
        st.badge("Not labelled yet", color="gray")

    track = load_track(ev.mmsi)
    cov = load_coverage_pings(ev.mmsi, ev.t0.tz_localize(None), ev.t1.tz_localize(None),
                              ev.lat0, ev.lon0, ev.lat1, ev.lon1)
    shown = cov.sample(n=min(len(cov), 3000), random_state=0)   # keep the map fast on long gaps
    st.pydeck_chart(build_map(ev, track, shown), height=520)
    st.caption(f"Blue = track before the gap · orange = after · red = straight line across the gap · "
               f"grey = {cov.mmsi.nunique()} other vessels heard near p0/p1 during the gap "
               f"({len(cov):,} pings, {len(shown):,} drawn)")
    feature_card(ev)

    with st.form(key=f"form_{ev.event_id}"):
        st.markdown("**Change label**" if current else "**Label this event**")
        label = st.radio("Label", LABELS, horizontal=True,
                         index=LABELS.index(current["label"]) if current else None)
        note = st.text_input("One-line note", value=current.get("note", ""))
        if st.form_submit_button("Save & next", type="primary"):
            if label is None or not note.strip():
                st.error("Pick a label and write a one-line note.")
            else:
                append_label(path, {
                    "event_id": ev.event_id, "mmsi": int(ev.mmsi), "rank": int(ev["rank"]),
                    "score": float(ev.score), "label": label,
                    "note": " ".join(note.split()),
                    "reviewer": REVIEWER,
                    "labelled_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                    "config_hash": ev.config_hash, "pipeline_version": ev.pipeline_version,
                })
                labels = load_labels(path)
                nxt = first_unlabelled(ids, labels, start=st.session_state.idx)
                if nxt is not None:                # stay put once all events are labelled
                    st.session_state.idx = nxt
                st.rerun()


def dashboard_page():
    dashboard.render(load_all_events(), load_events(TOP_N), load_labels(labels_path()), CFG, open_event)


def open_event(i):
    """Jump from the dashboard to the review page at top-50 index i."""
    st.session_state.idx = i
    st.switch_page(REVIEW_PAGE)


st.set_page_config(page_title="Dark-ship review", layout="wide")
DASHBOARD_PAGE = st.Page(dashboard_page, title="Dashboard", icon=":material/insights:", default=True)
REVIEW_PAGE = st.Page(review_page, title="Review events", icon=":material/fact_check:")
st.navigation([DASHBOARD_PAGE, REVIEW_PAGE]).run()

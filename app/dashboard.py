"""Dashboard page: what the pipeline found and how the top 50 were labelled.

Reads only out/events.parquet and out/labels.jsonl, so it works without the raw data.
"""
import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

# One colour per label, used by every chart and the map. Categorical slots 1-3 of the
# reference palette, checked with the dataviz validator (CVD + normal vision, light and dark).
LABEL_ORDER = ["real", "unsure", "data_artefact"]
LABEL_NAME = {"real": "Real", "unsure": "Unsure", "data_artefact": "Data artefact"}
COLORS = {
    "light": {"real": "#eb6834", "unsure": "#1baf7a", "data_artefact": "#2a78d6"},
    "dark": {"real": "#d95926", "unsure": "#199e70", "data_artefact": "#3987e5"},
}
SURFACE = {"light": "#ffffff", "dark": "#0e1117"}   # Streamlit page backgrounds (2 px mark gaps)
GROUP_NAME = {"fishing": "Fishing", "cargo": "Cargo", "tanker": "Tanker", "tug_tow": "Tug / tow",
              "passenger": "Passenger", "pleasure_sail": "Pleasure / sail", "other": "Other",
              "unknown": "Unknown"}
RULES = {  # short name for the axis, full definition for the tooltip
    "R1": ("Short dropout", "<= 15 min, steady speed, covered the expected distance"),
    "R2": ("Innocent cause visible", "parked, edge of receiver range, or unit only intermittently received"),
    "R3": ("Dark in a reachable area", ">= 45 min, others heard within 3 nm, no innocent cause"),
    "R4": ("Cannot decide", "one day of data cannot separate the explanations"),
}


def theme():
    t = getattr(getattr(st.context, "theme", None), "type", None)
    return "dark" if t == "dark" else "light"


def label_scale():
    c = COLORS[theme()]
    return alt.Scale(domain=[LABEL_NAME[k] for k in LABEL_ORDER], range=[c[k] for k in LABEL_ORDER])


def hex_rgb(h, alpha=230):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [alpha]


def labelled_table(top, labels):
    lab = pd.DataFrame(labels.values()) if labels else pd.DataFrame(columns=["event_id", "label", "note"])
    keep = [c for c in ("event_id", "label", "note", "ai_rule") if c in lab.columns]
    df = top.merge(lab[keep], on="event_id", how="left")
    df["label"] = df["label"].fillna("unlabelled")
    df["Label"] = df["label"].map(LABEL_NAME).fillna("Unlabelled")
    df["vessel"] = df["vessel_name"].fillna("unnamed")
    df["vessel_group"] = df["vessel_group"].map(GROUP_NAME).fillna(df["vessel_group"])
    df["gap_h"] = (df["gap_s"] / 3600).round(2)
    return df


def kpis(all_events, df):
    counts = df["label"].value_counts()
    cols = st.columns(6)
    cols[0].metric("Gaps detected", f"{len(all_events):,}", help="All silences of >= max(10 min, 10 x expected interval) with an endpoint in the box")
    cols[1].metric("Vessels with gaps", f"{all_events['mmsi'].nunique():,}")
    cols[2].metric("Reviewed", f"{(df['label'] != 'unlabelled').sum()} / {len(df)}", help="Top-ranked events reviewed")
    cols[3].metric("Real", int(counts.get("real", 0)))
    cols[4].metric("Unsure", int(counts.get("unsure", 0)))
    cols[5].metric("Data artefact", int(counts.get("data_artefact", 0)))


def bars_by_group(df):
    g = df[df["label"] != "unlabelled"].groupby(["vessel_group", "Label"]).size().reset_index(name="events")
    g["order"] = g["Label"].map({LABEL_NAME[k]: i for i, k in enumerate(LABEL_ORDER)})
    return (alt.Chart(g).mark_bar(cornerRadius=2, stroke=SURFACE[theme()], strokeWidth=2)
            .encode(y=alt.Y("vessel_group:N", sort="-x", title=None, scale=alt.Scale(paddingInner=0.3),
                            axis=alt.Axis(labelOverlap=False, labelPadding=6)),
                    x=alt.X("sum(events):Q", title="Events in the top 50", axis=alt.Axis(tickMinStep=1)),
                    color=alt.Color("Label:N", scale=label_scale(), legend=alt.Legend(orient="top", title=None)),
                    order=alt.Order("order:Q"),
                    tooltip=[alt.Tooltip("vessel_group:N", title="Vessel type"),
                             alt.Tooltip("Label:N"), alt.Tooltip("events:Q", title="Events")])
            .properties(height=260))


def score_by_rank(df):
    d = df[df["label"] != "unlabelled"]
    return (alt.Chart(d).mark_circle(size=90, opacity=1, stroke=SURFACE[theme()], strokeWidth=1.5)
            .encode(x=alt.X("rank:Q", title="Rank (1 = most suspicious)", scale=alt.Scale(domain=[0, len(df) + 1])),
                    y=alt.Y("score:Q", title="Score", scale=alt.Scale(zero=False)),
                    color=alt.Color("Label:N", scale=label_scale(), legend=alt.Legend(orient="top", title=None)),
                    tooltip=[alt.Tooltip("rank:Q", title="Rank"), alt.Tooltip("vessel:N", title="Vessel"),
                             alt.Tooltip("Label:N"), alt.Tooltip("score:Q", title="Score"),
                             alt.Tooltip("gap_h:Q", title="Gap (h)")])
            .properties(height=260))


def rules_chart(df):
    if "ai_rule" not in df:
        return None
    rule_label = {"R1": "data_artefact", "R2": "data_artefact", "R3": "real", "R4": "unsure"}
    r = df.dropna(subset=["ai_rule"]).groupby("ai_rule").size().reset_index(name="events")
    r["Reason"] = r["ai_rule"] + " " + r["ai_rule"].map(lambda k: RULES[k][0])
    r["Definition"] = r["ai_rule"].map(lambda k: RULES[k][1])
    r["Label"] = r["ai_rule"].map(rule_label).map(LABEL_NAME)
    return (alt.Chart(r).mark_bar(cornerRadiusEnd=4)
            .encode(y=alt.Y("Reason:N", sort=list(r.sort_values("ai_rule")["Reason"]), title=None,
                            scale=alt.Scale(paddingInner=0.3), axis=alt.Axis(labelLimit=220, labelOverlap=False)),
                    x=alt.X("events:Q", title="Events", axis=alt.Axis(tickMinStep=1)),
                    color=alt.Color("Label:N", scale=label_scale(), legend=alt.Legend(orient="top", title=None)),
                    tooltip=[alt.Tooltip("Reason:N"), alt.Tooltip("Definition:N"), alt.Tooltip("Label:N"),
                             alt.Tooltip("events:Q", title="Events")])
            .properties(height=200))


def precision_table(df):
    rows = []
    for k in (10, 25, 50):
        top = df.head(k)
        rows.append({"Top k": k, "Real": int((top["label"] == "real").sum()),
                     "Real share": f"{(top['label'] == 'real').mean():.0%}",
                     "Real + unsure share": f"{top['label'].isin(['real', 'unsure']).mean():.0%}"})
    return pd.DataFrame(rows)


def gap_map(df, cfg):
    c = COLORS[theme()]
    d = df.copy()
    d["color"] = d["label"].map(lambda k: hex_rgb(c.get(k, "#898781")))
    d["tip"] = ("#" + d["rank"].astype(str) + " " + d["vessel"] + " · " + d["Label"]
                + " · silent " + d["gap_h"].astype(str) + " h")
    d["src"] = d[["lon0", "lat0"]].values.tolist()
    d["dst"] = d[["lon1", "lat1"]].values.tolist()
    b = cfg["bbox"]
    box = [[b["lon_min"], b["lat_min"]], [b["lon_max"], b["lat_min"]], [b["lon_max"], b["lat_max"]],
           [b["lon_min"], b["lat_max"]], [b["lon_min"], b["lat_min"]]]
    layers = [
        pdk.Layer("PathLayer", [{"path": box, "tip": "bounding box"}], get_path="path",
                  get_color=[137, 135, 129, 160], width_min_pixels=1),
        pdk.Layer("LineLayer", d, get_source_position="src", get_target_position="dst",
                  get_color="color", get_width=3, pickable=True),
        pdk.Layer("ScatterplotLayer", d, get_position=["lon0", "lat0"], get_fill_color="color",
                  get_line_color=[255, 255, 255], line_width_min_pixels=1, stroked=True,
                  get_radius=250, radius_min_pixels=5, pickable=True),
    ]
    lats = pd.concat([d["lat0"], d["lat1"]])
    lons = pd.concat([d["lon0"], d["lon1"]])
    view = pdk.ViewState(latitude=(lats.min() + lats.max()) / 2 - 0.08,   # centre on the gap endpoints
                         longitude=(lons.min() + lons.max()) / 2, zoom=8.6)
    style = pdk.map_styles.CARTO_DARK if theme() == "dark" else pdk.map_styles.CARTO_LIGHT
    return pdk.Deck(layers=layers, initial_view_state=view, map_provider="carto", map_style=style,
                    tooltip={"text": "{tip}"})


def render(all_events, top, labels, cfg, open_event):
    """Draw the dashboard. `open_event(i)` jumps to the review page at top-50 index i."""
    df = labelled_table(top, labels)
    st.title("Dark-ship review: results")
    b = cfg["bbox"]
    st.caption(f"MarineCadastre AIS · {cfg['data']['day']} (UTC) · Houston–Galveston box "
               f"lat {b['lat_min']}–{b['lat_max']}, lon {b['lon_min']} to {b['lon_max']} · "
               f"config {top['config_hash'].iloc[0]} · top {len(top)} of {len(all_events)} gaps reviewed")
    kpis(all_events, df)

    left, right = st.columns(2)
    with left:
        st.subheader("Labels by vessel type")
        st.altair_chart(bars_by_group(df), height=320)
    with right:
        st.subheader("Where the labels sit in the ranking")
        st.altair_chart(score_by_rank(df), height=320)

    st.subheader("Where the top-50 gaps are")
    st.pydeck_chart(gap_map(df, cfg), height=440)
    st.caption("Each line joins the last report before a silence to the first report after it; "
               "the dot marks where the vessel went quiet. Colour = label (legend above). Hover for details.")

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Why: the rule behind each label")
        chart = rules_chart(df)
        if chart is not None:
            st.altair_chart(chart, height=240)
    with right:
        st.subheader("Precision of the ranking")
        st.dataframe(precision_table(df), hide_index=True)
        st.caption("Share of the top k labelled real. Weights were frozen before review.")

    st.subheader("All reviewed events")
    f1, f2, f3, f4 = st.columns([2, 1, 2, 2])
    pick_labels = f1.pills("Label", [LABEL_NAME[k] for k in LABEL_ORDER], selection_mode="multi",
                           default=[LABEL_NAME[k] for k in LABEL_ORDER])
    pick_class = f2.pills("Class", sorted(df["transceiver"].unique()), selection_mode="multi",
                          default=sorted(df["transceiver"].unique()))
    pick_group = f3.multiselect("Vessel type", sorted(df["vessel_group"].unique()),
                                default=sorted(df["vessel_group"].unique()))
    search = f4.text_input("Vessel name contains", "")
    view = df[df["Label"].isin(pick_labels) & df["transceiver"].isin(pick_class)
              & df["vessel_group"].isin(pick_group)
              & df["vessel"].str.contains(search, case=False, regex=False)]
    cols = ["rank", "vessel", "vessel_group", "transceiver", "gap_h", "score", "Label", "note"]
    sel = st.dataframe(
        view[cols], hide_index=True, on_select="rerun", selection_mode="single-row", key="events_table",
        column_config={
            "rank": st.column_config.NumberColumn("Rank", width="small"),
            "vessel": "Vessel", "vessel_group": "Type",
            "transceiver": st.column_config.TextColumn("Class", width="small"),
            "gap_h": st.column_config.NumberColumn("Gap (h)", format="%.2f", width="small"),
            "score": st.column_config.NumberColumn("Score", format="%.1f", width="small"),
            "Label": st.column_config.TextColumn("Label", width="small"),
            "note": st.column_config.TextColumn("Note (evidence)", width="large"),
        })
    st.caption(f"{len(view)} of {len(df)} events shown. Select a row to open it on the map.")
    rows = sel.selection.rows if sel is not None else []
    if rows:
        r = view.iloc[rows[0]]
        if st.button(f"Open #{int(r['rank'])} {r['vessel']} in Review events", type="primary"):
            open_event(int(r["rank"]) - 1)

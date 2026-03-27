from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from lila_viz.loader import build_file_index, load_match_events, normalize_match_time_ms
from lila_viz.mapping import MAPS
from lila_viz.viz import HeatmapConfig, add_heatmap_overlay, make_match_figure, world_df_to_pixels


st.set_page_config(page_title="LILA BLACK — Player Journey Viz", layout="wide")


def _image_to_data_url(image_path: Path) -> str:
    b = image_path.read_bytes()
    ext = image_path.suffix.lower().lstrip(".")
    mime = "image/png" if ext == "png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(b).decode('ascii')}"


@st.cache_data(show_spinner="Indexing data files (one-time)…")
def get_index_df(data_dir_str: str) -> pd.DataFrame:
    return build_file_index(Path(data_dir_str))


@st.cache_data(show_spinner="Loading match telemetry…")
def get_match_df(index_df: pd.DataFrame, match_id: str) -> pd.DataFrame:
    df = load_match_events(index_df, match_id)
    df = normalize_match_time_ms(df)
    return df


def main() -> None:
    st.title("LILA BLACK — Player Journey Visualization")
    st.caption("Filters + playback + heatmaps for movement and combat telemetry.")

    import os
    data_dir = Path(os.getenv("LILA_PLAYER_DATA_DIR", "data"))
    if not data_dir.exists():
        st.error(f"Data directory not found: `{data_dir}`")
        st.stop()

    minimaps_dir = data_dir / "minimaps"
    if not minimaps_dir.exists():
        st.error(f"Minimaps folder not found: `{minimaps_dir}`")
        st.stop()

    index_df = get_index_df(str(data_dir))
    if index_df.empty:
        st.error("No telemetry files found.")
        st.stop()

    # ---------------- SIDEBAR ----------------
    with st.sidebar:
        st.header("Explore")

        map_id = st.selectbox("Map", options=list(MAPS.keys()), index=0)

        map_index = index_df[index_df["map_id"] == map_id]
        day_options = sorted(map_index["date_folder"].dropna().unique().tolist())
        date_folder = st.selectbox("Date", options=day_options, index=0)

        day_index = map_index[map_index["date_folder"] == date_folder]
        match_options = sorted(day_index["match_id"].dropna().unique().tolist())
        match_id = st.selectbox("Match", options=match_options, index=0)

        st.divider()

        show_humans = st.checkbox("Show humans", True)
        show_bots = st.checkbox("Show bots", True)
        show_paths = st.checkbox("Show paths", True)
        show_events = st.checkbox("Show event markers", True)

        st.divider()

        heat_metric = st.selectbox(
            "Heatmap",
            ["Off", "Traffic", "Kills", "Deaths", "Storm deaths"],
            index=0
        )
        heat_opacity = st.slider("Heatmap opacity", 0.15, 0.85, 0.55, 0.05)
        heat_bins = st.slider("Heatmap resolution", 60, 220, 140, 10)

    # ---------------- LOAD MATCH ----------------
    match_df = get_match_df(day_index, match_id)

    if match_df.empty:
        st.warning("No data for this match.")
        st.stop()

    # Convert coords
    match_df = world_df_to_pixels(match_df, map_id)

    # ---------------- PLAYBACK (FIXED) ----------------
    unique_ts = match_df["ts"].sort_values().unique()

    frame_idx = st.slider(
        "Playback Frame",
        0,
        len(unique_ts) - 1,
        len(unique_ts) - 1
    )

    current_ts = unique_ts[frame_idx]

    # Filter data up to selected frame
    filtered_df = match_df[match_df["ts"] <= current_ts]

    # ---------------- MAP ----------------
    minimap_url = _image_to_data_url(
        minimaps_dir / MAPS[map_id].image_filename
    )

    # ---------------- FIGURE ----------------
    fig = make_match_figure(
        filtered_df,
        map_id,
        minimap_url,
        None,
        show_paths=show_paths,
        show_events=show_events,
        show_bots=show_bots,
        show_humans=show_humans,
    )

    if heat_metric != "Off":
        fig = add_heatmap_overlay(
            fig,
            filtered_df,
            map_id,
            heat_metric,
            cfg=HeatmapConfig(
                bins=int(heat_bins),
                opacity=float(heat_opacity)
            ),
        )

    # ---------------- LAYOUT ----------------
    c1, c2 = st.columns([3, 2])

    with c1:
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Match summary (filtered)")

        cur = filtered_df[
            (filtered_df["user_id"].notna()) &
            (filtered_df["user_id"] != "")
        ]

        def count(ev: str) -> int:
            return int((cur["event"] == ev).sum())

        st.metric("Players (humans)", int(cur["user_id"].nunique()))
        st.metric("Kills", count("Kill"))
        st.metric("Deaths", count("Killed"))
        st.metric("Bot kills", count("BotKill"))
        st.metric("Deaths to bots", count("BotKilled"))
        st.metric("Storm deaths", count("KilledByStorm"))
        st.metric("Loot pickups", count("Loot"))

    st.caption("Tip: move slider to replay match step-by-step.")


if __name__ == "__main__":
    main()

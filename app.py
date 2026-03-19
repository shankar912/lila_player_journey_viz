from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from lila_viz.loader import build_file_index, get_data_dir, load_match_events, normalize_match_time_ms
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
        st.error("No telemetry files found. Expected `February_*` folders with `*.nakama-0` files.")
        st.stop()

    with st.sidebar:
        st.header("Explore")
        map_id = st.selectbox("Map", options=list(MAPS.keys()), index=0)

        map_index = index_df[index_df["map_id"] == map_id] if "map_id" in index_df.columns else index_df
        day_options = sorted(map_index["date_folder"].dropna().unique().tolist())
        date_folder = st.selectbox("Date", options=day_options, index=0)

        day_index = map_index[map_index["date_folder"] == date_folder]
        match_options = sorted(day_index["match_id"].dropna().unique().tolist())
        match_id = st.selectbox("Match", options=match_options, index=0)

        st.divider()
        show_humans = st.checkbox("Show humans", value=True)
        show_bots = st.checkbox("Show bots", value=True)
        show_paths = st.checkbox("Show paths", value=True)
        show_events = st.checkbox("Show event markers", value=True)

        st.divider()
        heat_metric = st.selectbox("Heatmap", ["Off", "Traffic", "Kills", "Deaths", "Storm deaths"], index=0)
        heat_opacity = st.slider("Heatmap opacity", min_value=0.15, max_value=0.85, value=0.55, step=0.05)
        heat_bins = st.slider("Heatmap resolution", min_value=60, max_value=220, value=140, step=10)

    match_df = get_match_df(day_index, match_id)
    if match_df.empty:
        st.warning("No rows loaded for this match.")
        st.stop()

    # Map coords → pixels
    match_df = world_df_to_pixels(match_df, map_id)

    # Playback
    t_max = int(match_df["t_ms"].max()) if "t_ms" in match_df.columns else 0
    t_end = st.slider("Playback time (seconds)", 0, max(1, t_max // 1000), value=max(1, t_max // 1000), step=1)
    t_ms = int(t_end * 1000)

    minimap_url = _image_to_data_url(minimaps_dir / MAPS[map_id].image_filename)

    fig = make_match_figure(
        match_df,
        map_id,
        minimap_url,
        t_ms,
        show_paths=show_paths,
        show_events=show_events,
        show_bots=show_bots,
        show_humans=show_humans,
    )
    if heat_metric != "Off":
        fig = add_heatmap_overlay(
            fig,
            match_df[match_df["t_ms"] <= t_ms],
            map_id,
            heat_metric,
            cfg=HeatmapConfig(bins=int(heat_bins), opacity=float(heat_opacity)),
        )

    c1, c2 = st.columns([3, 2], vertical_alignment="top")
    with c1:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c2:
        st.subheader("Match summary (filtered by playback time)")

    cur = match_df[
        (match_df["t_ms"] <= t_ms) &
        (match_df["user_id"].notna()) &
        (match_df["user_id"] != "")
    ]

    human_players = cur["user_id"].nunique()
    bot_players = 0

    def count(ev: str) -> int:
        return int((cur["event"] == ev).sum())

    st.metric("Players (humans)", int(human_players))
    st.metric("Players (bots)", int(bot_players))
    st.metric("Kills (human→human)", count("Kill"))
    st.metric("Deaths (human killed)", count("Killed"))
    st.metric("Bot kills (human→bot)", count("BotKill"))
    st.metric("Deaths to bots (human)", count("BotKilled"))
    st.metric("Storm deaths", count("KilledByStorm"))
    st.metric("Loot pickups", count("Loot"))

    st.divider()
    st.caption("Tip: reduce playback time to see early-game rotations and first-contact zones.")

if __name__ == "__main__":
    main()


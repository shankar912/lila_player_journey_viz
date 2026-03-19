from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .mapping import MAPS, is_bot_user_id


EVENT_STYLE = {
    "Kill": dict(symbol="x", color="#e11d48", size=10),
    "Killed": dict(symbol="circle-open", color="#fb7185", size=10),
    "BotKill": dict(symbol="x", color="#f97316", size=10),
    "BotKilled": dict(symbol="circle-open", color="#fdba74", size=10),
    "Loot": dict(symbol="diamond", color="#22c55e", size=9),
    "KilledByStorm": dict(symbol="triangle-up", color="#38bdf8", size=11),
}


@dataclass(frozen=True)
class HeatmapConfig:
    bins: int = 140
    opacity: float = 0.55
    colorscale: str = "Hot"


def _add_minimap_background(fig: go.Figure, image_url: str, size_px: int = 1024) -> None:
    fig.update_xaxes(range=[0, size_px], showgrid=False, zeroline=False, visible=False)
    fig.update_yaxes(range=[size_px, 0], showgrid=False, zeroline=False, visible=False, scaleanchor="x")
    fig.update_layout(
        width=820,
        height=820,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        images=[
            dict(
                source=image_url,
                xref="x",
                yref="y",
                x=0,
                y=0,
                sizex=size_px,
                sizey=size_px,
                sizing="stretch",
                layer="below",
                opacity=1.0,
            )
        ],
    )


def world_df_to_pixels(df: pd.DataFrame, map_id: str) -> pd.DataFrame:
    if df.empty:
        return df
    cfg = MAPS[map_id]
    px, py = cfg.world_to_pixel(df["x"].astype(float).to_numpy(), df["z"].astype(float).to_numpy())
    out = df.copy()
    out["px"] = px
    out["py"] = py
    return out


def make_match_figure(
    df: pd.DataFrame,
    map_id: str,
    minimap_image_url: str,
    t_ms_max: int,
    *,
    show_paths: bool,
    show_events: bool,
    show_bots: bool,
    show_humans: bool,
) -> go.Figure:
    fig = go.Figure()
    _add_minimap_background(fig, minimap_image_url, size_px=MAPS[map_id].image_size_px)

    if df.empty:
        return fig

    df = df[df["t_ms"] <= t_ms_max].copy()
    df = df.sort_values(["user_id", "t_ms"], kind="stable")
    df["is_bot"] = df["user_id"].astype(str).apply(is_bot_user_id)

    if not show_bots:
        df = df[~df["is_bot"]]
    if not show_humans:
        df = df[df["is_bot"]]

    # Paths (movement)
    if show_paths:
        move = df[df["event"].isin(["Position", "BotPosition"])].copy()
        for is_bot, sub in move.groupby("is_bot"):
            if sub.empty:
                continue
            color = "rgba(147,197,253,0.65)" if is_bot else "rgba(99,102,241,0.75)"
            # Show each player's polyline as a separate trace for hover clarity
            for user_id, p in sub.groupby("user_id"):
                fig.add_trace(
                    go.Scatter(
                        x=p["px"],
                        y=p["py"],
                        mode="lines",
                        line=dict(color=color, width=2),
                        name=("Bot path" if is_bot else "Human path"),
                        legendgroup=("bot" if is_bot else "human"),
                        showlegend=False,
                        hovertemplate="user=%{customdata[0]}<br>t=%{customdata[1]}s<extra></extra>",
                        customdata=np.stack([p["user_id"].astype(str), (p["t_ms"] / 1000).round(1)], axis=1),
                    )
                )

    # Event markers
    if show_events:
        events = df[df["event"].isin(EVENT_STYLE.keys())].copy()
        for ev, sub in events.groupby("event"):
            style = EVENT_STYLE.get(ev, dict(symbol="circle", color="#ffffff", size=9))
            fig.add_trace(
                go.Scatter(
                    x=sub["px"],
                    y=sub["py"],
                    mode="markers",
                    marker=dict(symbol=style["symbol"], color=style["color"], size=style["size"], line=dict(width=0)),
                    name=ev,
                    hovertemplate="event=%{customdata[0]}<br>user=%{customdata[1]}<br>t=%{customdata[2]}s<extra></extra>",
                    customdata=np.stack(
                        [sub["event"].astype(str), sub["user_id"].astype(str), (sub["t_ms"] / 1000).round(1)],
                        axis=1,
                    ),
                )
            )

    return fig


def add_heatmap_overlay(
    fig: go.Figure,
    df: pd.DataFrame,
    map_id: str,
    metric: str,
    cfg: HeatmapConfig = HeatmapConfig(),
) -> go.Figure:
    if df.empty:
        return fig

    if metric == "Traffic":
        subset = df[df["event"].isin(["Position", "BotPosition"])]
    elif metric == "Kills":
        subset = df[df["event"].isin(["Kill", "BotKill"])]
    elif metric == "Deaths":
        subset = df[df["event"].isin(["Killed", "BotKilled"])]
    elif metric == "Storm deaths":
        subset = df[df["event"].isin(["KilledByStorm"])]
    else:
        subset = df

    if subset.empty:
        return fig

    size = MAPS[map_id].image_size_px
    x = subset["px"].to_numpy()
    y = subset["py"].to_numpy()
    # clamp to minimap bounds (out-of-bounds events can happen due to telemetry noise)
    x = np.clip(x, 0, size)
    y = np.clip(y, 0, size)

    heat, xedges, yedges = np.histogram2d(x, y, bins=cfg.bins, range=[[0, size], [0, size]])
    # Plotly Heatmap expects z indexed by y then x; transpose
    z = heat.T

    fig.add_trace(
        go.Heatmap(
            z=z,
            x=np.linspace(0, size, cfg.bins),
            y=np.linspace(0, size, cfg.bins),
            colorscale=cfg.colorscale,
            opacity=cfg.opacity,
            showscale=False,
            hoverinfo="skip",
            name=f"{metric} heat",
        )
    )
    return fig


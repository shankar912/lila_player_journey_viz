from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

# Allow running as a script without installing the package
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lila_viz.loader import build_file_index, get_data_dir, load_match_events, normalize_match_time_ms
from lila_viz.mapping import MAPS, is_bot_user_id
from lila_viz.viz import world_df_to_pixels


def _quantile_cut(v: np.ndarray, q: float) -> float:
    if len(v) == 0:
        return float("nan")
    return float(np.quantile(v, q))


def compute_top_hotspots(df: pd.DataFrame, map_id: str, metric: str, bins: int = 70, top_k: int = 5):
    size = MAPS[map_id].image_size_px
    if metric == "Kills":
        sub = df[df["event"].isin(["Kill", "BotKill"])]
    elif metric == "Deaths":
        sub = df[df["event"].isin(["Killed", "BotKilled", "KilledByStorm"])]
    elif metric == "Storm deaths":
        sub = df[df["event"].isin(["KilledByStorm"])]
    else:
        sub = df[df["event"].isin(["Position", "BotPosition"])]
    if sub.empty:
        return []

    x = np.clip(sub["px"].to_numpy(), 0, size)
    y = np.clip(sub["py"].to_numpy(), 0, size)
    heat, xedges, yedges = np.histogram2d(x, y, bins=bins, range=[[0, size], [0, size]])
    flat_idx = np.argsort(heat.ravel())[::-1]

    hotspots = []
    for idx in flat_idx[: top_k * 3]:
        val = heat.ravel()[idx]
        if val <= 0:
            break
        yi, xi = np.unravel_index(idx, heat.shape)
        x0, x1 = xedges[xi], xedges[xi + 1]
        y0, y1 = yedges[yi], yedges[yi + 1]
        hotspots.append(dict(count=int(val), px=float((x0 + x1) / 2), py=float((y0 + y1) / 2)))
        if len(hotspots) >= top_k:
            break
    return hotspots


def main() -> None:
    data_dir = get_data_dir()
    idx = build_file_index(data_dir)
    if idx.empty:
        raise SystemExit(f"No files found under {data_dir}")

    # Basic distributional checks
    print("### Dataset overview")
    print(f"days: {sorted(idx['date_folder'].unique().tolist())}")
    print(f"maps: {sorted([m for m in idx['map_id'].dropna().unique().tolist() if m])}")
    print(f"matches: {idx['match_id'].nunique():,}")
    print(f"players (unique user_ids): {idx['user_id'].nunique():,}")
    print(f"bot files: {int(idx['is_bot'].sum()):,} / {len(idx):,}")
    print()

    # Pick a “representative” match per map: one with many files (more participants)
    print("### Representative matches (most participants) per map")
    rep_matches = []
    for map_id in sorted(idx["map_id"].dropna().unique()):
        sub = idx[idx["map_id"] == map_id]
        counts = sub.groupby("match_id")["file_path"].count().sort_values(ascending=False)
        if counts.empty:
            continue
        match_id = counts.index[0]
        rep_matches.append((map_id, match_id, int(counts.iloc[0])))
        print(f"- {map_id}: {match_id} ({int(counts.iloc[0])} participant files)")
    print()

    print("### Early-game engagement timing (seconds)")
    # For each match:
    # - define "match start" as earliest movement sample (Position/BotPosition) across all participants
    # - find earliest combat event (Kill/Killed/BotKill/BotKilled)
    # - report delta in seconds
    rows = []
    for match_id, sub in idx.groupby("match_id"):
        df = load_match_events(idx, match_id)
        if df.empty:
            continue
        df["event"] = df["event"].apply(lambda x: x.decode("utf-8") if isinstance(x, (bytes, bytearray)) else x)

        ts_ns = pd.to_datetime(df["ts"]).astype("int64")
        ts_ms = (ts_ns // 1_000_000).astype("int64")
        df = df.assign(_ts_ms=ts_ms)

        movement = df[df["event"].isin(["Position", "BotPosition"])]
        combat = df[df["event"].isin(["Kill", "Killed", "BotKill", "BotKilled"])]
        if movement.empty or combat.empty:
            continue

        start_ms = int(movement["_ts_ms"].min())
        first_combat_ms = int(combat["_ts_ms"].min())
        rows.append(max(0.0, (first_combat_ms - start_ms) / 1000.0))
    v = np.array(rows, dtype=float)
    print(f"matches_with_combat: {len(v):,}")
    if len(v):
        print(f"p25={_quantile_cut(v, 0.25):.1f}s  p50={_quantile_cut(v, 0.50):.1f}s  p75={_quantile_cut(v, 0.75):.1f}s")
    print()

    print("### Hotspots per map (pixel-space bins)")
    for map_id, match_id, _n in rep_matches:
        df = load_match_events(idx, match_id)
        df = normalize_match_time_ms(df)
        df = df[df["map_id"] == map_id]
        df = df.copy()
        df["event"] = df["event"].apply(lambda x: x.decode("utf-8") if isinstance(x, (bytes, bytearray)) else x)
        df = world_df_to_pixels(df, map_id)
        for metric in ["Traffic", "Kills", "Deaths", "Storm deaths"]:
            hs = compute_top_hotspots(df, map_id, metric, bins=80, top_k=3)
            if not hs:
                continue
            formatted = ", ".join([f"(count={h['count']}, px~{h['px']:.0f}, py~{h['py']:.0f})" for h in hs])
            print(f"- {map_id} / {metric}: {formatted}")
    print()

    print("### Bot vs human movement density (sampled)")
    # Sample a subset of matches to estimate bot/human Position sampling counts
    sample_matches = idx["match_id"].dropna().unique().tolist()[:120]
    bot_pos = 0
    human_pos = 0
    for m in sample_matches:
        df = load_match_events(idx, m)
        if df.empty:
            continue
        df["event"] = df["event"].apply(lambda x: x.decode("utf-8") if isinstance(x, (bytes, bytearray)) else x)
        human_pos += int((df["event"] == "Position").sum())
        bot_pos += int((df["event"] == "BotPosition").sum())
    print(f"sample_matches: {len(sample_matches)}  human_position_rows: {human_pos:,}  bot_position_rows: {bot_pos:,}")

    print()
    print("### Global bot vs human movement (all files)")
    hpos = 0
    bpos = 0
    for fp in idx["file_path"].tolist():
        t = pq.read_table(fp, columns=["event"])
        ev = pd.Series(t.column("event").to_pylist()).apply(
            lambda x: x.decode("utf-8") if isinstance(x, (bytes, bytearray)) else x
        )
        hpos += int((ev == "Position").sum())
        bpos += int((ev == "BotPosition").sum())
    total = hpos + bpos
    if total:
        print(f"human_position_rows: {hpos:,}  bot_position_rows: {bpos:,}  bot_share: {bpos/total:.1%}")
    else:
        print("No Position rows found.")

    print()
    print("### Map utilization (traffic concentration)")
    for map_id in sorted(idx["map_id"].dropna().unique()):
        cfg = MAPS[map_id]
        xs = []
        ys = []
        for fp in idx.loc[idx["map_id"] == map_id, "file_path"].tolist():
            t = pq.read_table(fp, columns=["event", "x", "z"])
            df = t.to_pandas()
            df["event"] = df["event"].apply(lambda x: x.decode("utf-8") if isinstance(x, (bytes, bytearray)) else x)
            df = df[df["event"].isin(["Position", "BotPosition"])]
            if df.empty:
                continue
            px, py = cfg.world_to_pixel(df["x"].astype(float).to_numpy(), df["z"].astype(float).to_numpy())
            xs.append(px)
            ys.append(py)
        if not xs:
            continue
        x = np.clip(np.concatenate(xs), 0, cfg.image_size_px)
        y = np.clip(np.concatenate(ys), 0, cfg.image_size_px)
        bins = 100
        heat, *_ = np.histogram2d(x, y, bins=bins, range=[[0, cfg.image_size_px], [0, cfg.image_size_px]])
        touched = int((heat > 0).sum())
        total_bins = bins * bins
        traffic = heat.ravel()
        traffic_sum = float(traffic.sum())
        top_n = max(1, int(math.ceil(0.05 * len(traffic))))
        top_share = float(np.sort(traffic)[::-1][:top_n].sum()) / traffic_sum if traffic_sum else 0.0
        print(f"- {map_id}: bins_touched={touched/total_bins:.1%}  top5%_traffic_share={top_share:.1%}")

    print()
    print("### Storm deaths vs other deaths (all maps)")
    storm = 0
    all_deaths = 0
    for fp in idx["file_path"].tolist():
        t = pq.read_table(fp, columns=["event"])
        ev = pd.Series(t.column("event").to_pylist()).apply(
            lambda x: x.decode("utf-8") if isinstance(x, (bytes, bytearray)) else x
        )
        storm += int((ev == "KilledByStorm").sum())
        all_deaths += int(ev.isin(["Killed", "BotKilled", "KilledByStorm"]).sum())
    if all_deaths:
        print(f"storm_deaths: {storm:,}  all_deaths: {all_deaths:,}  storm_share_of_deaths: {storm/all_deaths:.1%}")
    else:
        print("No death rows found.")


if __name__ == "__main__":
    main()


# Architecture (1 page)

## What I built
A **Streamlit** web app (`app.py`) that lets Level Designers explore LILA BLACK telemetry:
- Player paths (humans vs bots)
- Event markers (kills, deaths, loot, storm deaths)
- Timeline playback (watch match progression)
- Heatmap overlays (traffic / kills / deaths / storm deaths)

## Tech stack and why
| Component | Choice | Why |
|---|---|---|
| UI | Streamlit | Fast to ship a polished internal tool; great for filters + interactive plots. |
| Plotting | Plotly | Renders paths + markers + heatmap overlays cleanly; hover tooltips help designers. |
| Parquet reading | PyArrow | Reliable parquet reader even when files have no `.parquet` extension. |
| Data wrangling | Pandas / NumPy | Simple grouping (per user), time slicing, and 2D histograms for heatmaps. |

## Data flow (parquet → browser)
1. **Index step (cached)**: scan `February_*` folders and build an index table:
   - Parse `user_id` + `match_id` from filename (`{user_id}_{match_id}.nakama-0`)
   - Read `map_id` from the parquet file (single-column read for speed)
2. **User selects map/date/match** in sidebar.
3. **Load match**: read all parquet files for that `match_id`, concatenate rows, decode `event` bytes.
4. **Normalize time**: convert `ts` (datetime) to relative match time `t_ms` from match start.
5. **World → minimap mapping**: convert `(x,z)` to pixel `(px,py)` using the map config.
6. **Render**:
   - Path lines for `Position` / `BotPosition`
   - Markers for combat/loot/storm events
   - Optional heatmap overlay (2D histogram bins)
   - Playback slider filters rows where `t_ms <= slider_time`

## Coordinate mapping (the tricky part)
Telemetry provides positions in world coordinates (x,z), while the UI requires pixel positions on a 1024×1024 minimap.

Each map defines an origin and scale to convert world coordinates into pixel space. The Y-axis is flipped to match the top-left origin used by images.

Implementation lives in `lila_viz/mapping.py` (`MapConfig.world_to_pixel`).

Normalized using origin and scale, then map to pixel space and flip Y to match the image coordinate system.





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
For a world coordinate \((x,z)\), per map config:
- \(u = (x - origin_x) / scale\)
- \(v = (z - origin_z) / scale\)
- \(pixel_x = u \cdot 1024\)
- \(pixel_y = (1 - v) \cdot 1024\)  (flip because images are top-left origin)

Implementation lives in `lila_viz/mapping.py` (`MapConfig.world_to_pixel`).

**Assumptions / handling ambiguities**
- `y` is elevation, ignored for 2D minimap plotting (per README).
- Some events can land slightly out of bounds due to telemetry noise; heatmaps clamp to `[0,1024]`.
- Humans vs bots: `user_id.isdigit()` is bot; UUID-like strings are humans (per README).

## Major trade-offs
| Consideration | Option A | Option B | Decision |
|---|---|---|---|
| Multi-file querying | DuckDB SQL over whole dataset | Load only selected match/day | **Load selected match** for responsiveness; add day-level analysis in scripts. |
| Heatmaps | Datashader | NumPy 2D histogram | **NumPy histogram**: simpler + good enough at this scale. |
| Playback | Full animation | Time slider (progressive reveal) | **Time slider**: reliable in Streamlit and easy to reason about. |

## If I had more time
- Add “**scope**” selector for heatmaps (match vs day vs all days) using DuckDB to aggregate quickly.
- Add extraction-related events once available (to measure “successful extractions” and routes).
- Add designer annotations (pin + note) to mark problematic areas and share links.


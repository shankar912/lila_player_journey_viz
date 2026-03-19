# LILA BLACK — Player Journey Visualization (Streamlit)

## What this is
Interactive web tool for Level Designers to explore:
- Player movement paths on minimaps
- Kills / deaths / loot / storm deaths
- Humans vs bots
- Match playback over time
- Heatmap overlays (traffic / kills / deaths / storm deaths)

## Data location
This app expects the dataset folder that contains:
- `February_10/ ... February_14/` subfolders
- `minimaps/` subfolder

By default it looks for: `c:\Quiz\Questions\player_data`

You can override with an environment variable:
- `LILA_PLAYER_DATA_DIR` (absolute path)

## Setup (Windows / PowerShell)
From this repo folder:

```bash
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
streamlit run app.py
```

## Notes
- Files have **no `.parquet` extension** but they are parquet.
- `event` is stored as **bytes** and is decoded to UTF-8 strings in the loader.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import pyarrow.parquet as pq


DEFAULT_DATA_DIR = Path(r"c:\Quiz\Questions\player_data")


@dataclass(frozen=True)
class FileIndexRow:
    date_folder: str
    file_path: str
    user_id: str
    match_id: str
    is_bot: bool
    map_id: str


def get_data_dir() -> Path:
    raw = os.environ.get("LILA_PLAYER_DATA_DIR")
    return Path(raw) if raw else DEFAULT_DATA_DIR


def iter_day_folders(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        return []
    return sorted([p for p in data_dir.iterdir() if p.is_dir() and p.name.startswith("February_")])


def iter_parquetish_files(day_folder: Path) -> Iterable[Path]:
    # Data files have no .parquet extension; they look like *.nakama-0
    for p in day_folder.iterdir():
        if p.is_file() and p.name.endswith(".nakama-0"):
            yield p


def parse_filename(filename: str) -> tuple[str, str]:
    # {user_id}_{match_id}.nakama-0
    base = filename
    if base.endswith(".nakama-0"):
        base = base[: -len(".nakama-0")]
    user_id, match_id = base.split("_", 1)
    return user_id, match_id + ".nakama-0"


def _decode_event_series(s: pd.Series) -> pd.Series:
    # event column can be bytes or already string depending on reader/version
    return s.apply(lambda x: x.decode("utf-8") if isinstance(x, (bytes, bytearray)) else x)


def read_single_file(file_path: Path) -> pd.DataFrame:
    t = pq.read_table(str(file_path))
    df = t.to_pandas()
    if "event" in df.columns:
        df["event"] = _decode_event_series(df["event"])
    return df


def read_file_map_id(file_path: Path) -> str:
    # Fast-ish: read only map_id column; then take first value.
    t = pq.read_table(str(file_path), columns=["map_id"])
    col = t.column("map_id").to_pylist()
    return str(col[0]) if col else ""


def build_file_index(data_dir: Path) -> pd.DataFrame:
    rows: list[dict] = []
    for day in iter_day_folders(data_dir):
        for f in iter_parquetish_files(day):
            user_id, match_id = parse_filename(f.name)
            is_bot = user_id.isdigit()
            try:
                map_id = read_file_map_id(f)
            except Exception:
                map_id = ""
            rows.append(
                {
                    "date_folder": day.name,
                    "file_path": str(f),
                    "user_id": user_id,
                    "match_id": match_id,
                    "is_bot": is_bot,
                    "map_id": map_id,
                }
            )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["date_folder", "map_id", "match_id", "is_bot", "user_id"], kind="stable")
    return df


def load_match_events(index_df: pd.DataFrame, match_id: str) -> pd.DataFrame:
    files = index_df.loc[index_df["match_id"] == match_id, "file_path"].tolist()
    frames: list[pd.DataFrame] = []
    for fp in files:
        frames.append(read_single_file(Path(fp)))
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    return df


def normalize_match_time_ms(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "ts" not in df.columns:
        return df
    # pandas datetime64[ns] → int64 ns
    ts_ns = pd.to_datetime(df["ts"]).astype("int64")
    ts_ms = (ts_ns // 1_000_000).astype("int64")
    start = int(ts_ms.min())
    df = df.copy()
    df["t_ms"] = ts_ms - start
    return df


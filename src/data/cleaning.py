from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from src.utils.log import get_logger

logger = get_logger(__name__)


REQUIRED_COLS_HINT = ["Date", "HomeTeam", "AwayTeam"]


def _safe_read_csv(path: Path) -> pd.DataFrame:
    """Read CSV robustly (Football-Data files can contain non-UTF8 chars)."""
    try:
        return pd.read_csv(path, encoding="utf-8", encoding_errors="ignore")
    except TypeError:
        # pandas < 2.0 fallback (shouldn't happen with the project's requirements)
        return pd.read_csv(path, encoding="latin-1")


def _get_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    # Football-Data: Date often dd/mm/yy (dayfirst=True)
    date_col = _get_col(df, ["Date", "date"])
    if not date_col:
        raise ValueError("No Date column found in dataframe")

    # Some files have separate 'Time'
    time_col = _get_col(df, ["Time", "time"])

    df = df.copy()
    df["match_date"] = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")

    if time_col and time_col in df.columns:
        # merge date + time if time looks present
        dt_raw = df[date_col].astype(str).str.strip() + " " + df[time_col].astype(str).str.strip()
        df["match_datetime"] = pd.to_datetime(dt_raw, dayfirst=True, errors="coerce")
    else:
        df["match_datetime"] = pd.NaT

    return df


def clean_matches(raw_csv_paths: Iterable[Path], seasons: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """Load and clean match data from Football-Data.co.uk CSVs.

    Parameters
    ----------
    raw_csv_paths:
        Paths to CSV files (one per season).
    seasons:
        Optional seasons list aligned with raw_csv_paths. If not provided, inferred from filename.

    Returns
    -------
    pd.DataFrame
        Cleaned matches with stable column names.
    """
    paths = list(raw_csv_paths)
    seasons_list = list(seasons) if seasons is not None else [None] * len(paths)

    frames: List[pd.DataFrame] = []
    for path, season in zip(paths, seasons_list):
        logger.info("Reading raw CSV: %s", path)
        df = _safe_read_csv(path)

        # Season inference from filename if missing
        if season is None:
            # expects like "F1_2526.csv"
            stem = path.stem
            season = stem.split("_")[-1] if "_" in stem else "unknown"
        df["season"] = str(season)

        # Basic sanity
        missing_hint = [c for c in REQUIRED_COLS_HINT if c not in df.columns]
        if missing_hint:
            logger.warning("CSV %s is missing columns %s (will try best-effort parsing)", path, missing_hint)

        df = _parse_dates(df)

        # Standardize team names
        home_col = _get_col(df, ["HomeTeam", "Home", "Home Team"])
        away_col = _get_col(df, ["AwayTeam", "Away", "Away Team"])
        if not home_col or not away_col:
            raise ValueError(f"Missing Home/Away team columns in {path}")

        # Goals / results columns vary slightly across files
        hg_col = _get_col(df, ["FTHG", "HG"])
        ag_col = _get_col(df, ["FTAG", "AG"])
        res_col = _get_col(df, ["FTR", "Res"])

        cleaned = pd.DataFrame(
            {
                "season": df["season"].astype(str),
                "match_date": df["match_date"],
                "match_datetime": df["match_datetime"],
                "home_team": df[home_col].astype(str).str.strip(),
                "away_team": df[away_col].astype(str).str.strip(),
                "home_goals": pd.to_numeric(df[hg_col], errors="coerce") if hg_col else pd.NA,
                "away_goals": pd.to_numeric(df[ag_col], errors="coerce") if ag_col else pd.NA,
                "result": df[res_col].astype(str).str.strip() if res_col else pd.NA,
            }
        )

        # Normalize result values
        cleaned["result"] = cleaned["result"].replace({"nan": pd.NA, "": pd.NA})
        cleaned["is_played"] = cleaned["home_goals"].notna() & cleaned["away_goals"].notna()

        # If result missing but goals present, compute it
        def compute_result(row) -> Optional[str]:
            if pd.notna(row["result"]) and row["result"] in {"H", "D", "A"}:
                return row["result"]
            if not row["is_played"]:
                return None
            hg = float(row["home_goals"])
            ag = float(row["away_goals"])
            if hg > ag:
                return "H"
            if hg < ag:
                return "A"
            return "D"

        cleaned["result"] = cleaned.apply(compute_result, axis=1)

        # Points
        cleaned["points_home"] = cleaned["result"].map({"H": 3, "D": 1, "A": 0}).astype("Int64")
        cleaned["points_away"] = cleaned["result"].map({"H": 0, "D": 1, "A": 3}).astype("Int64")

        cleaned["total_goals"] = (cleaned["home_goals"] + cleaned["away_goals"]).astype("Float64")

        # Stable match_id (hash of season + date + teams)
        def make_id(row) -> str:
            ts = row["match_datetime"] if pd.notna(row["match_datetime"]) else row["match_date"]
            ts_str = ts.isoformat() if pd.notna(ts) else ""
            key = f"{row['season']}|{ts_str}|{row['home_team']}|{row['away_team']}"
            return hashlib.md5(key.encode("utf-8")).hexdigest()[:16]

        cleaned["match_id"] = cleaned.apply(make_id, axis=1)

        frames.append(cleaned)

    all_matches = pd.concat(frames, ignore_index=True)

    # Basic cleanup
    all_matches = all_matches.drop_duplicates(subset=["match_id"], keep="last")
    all_matches = all_matches.sort_values(["season", "match_date", "match_datetime"], na_position="last")
    return all_matches.reset_index(drop=True)


def save_clean_matches(df: pd.DataFrame, processed_path: Path) -> None:
    """Save cleaned matches to CSV."""
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(processed_path, index=False)
    logger.info("Saved processed dataset: %s (%d rows)", processed_path, len(df))


def load_processed_matches(processed_path: Path) -> pd.DataFrame:
    """Load the processed matches CSV with consistent dtypes."""
    if not processed_path.exists():
        raise FileNotFoundError(
            f"Processed dataset not found: {processed_path}. Run scripts.download_data first."
        )

    df = pd.read_csv(processed_path, parse_dates=["match_date", "match_datetime"])

    # Dtype normalization (CSV roundtrip can change types)
    if "is_played" in df.columns:
        df["is_played"] = df["is_played"].astype(str).str.lower().isin(["true", "1", "yes"])

    for col in ["home_goals", "away_goals", "total_goals"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["points_home", "points_away"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    return df

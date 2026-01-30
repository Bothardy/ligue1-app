from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path (Streamlit runs scripts from /app)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from pathlib import Path
from typing import Iterable, Tuple

import pandas as pd
import streamlit as st

from src.config import get_settings
from src.data.cleaning import load_processed_matches
from src.models.poisson import PoissonTeamStrengthModel
from src.ui.team_logos import get_team_logo_image


@st.cache_resource
def settings_cached():
    return get_settings()


@st.cache_data
def load_matches_cached(processed_path: str) -> pd.DataFrame:
    return load_processed_matches(Path(processed_path))


def available_seasons(df: pd.DataFrame) -> list[str]:
    seasons = sorted(df["season"].astype(str).unique().tolist(), reverse=True)
    return seasons


def available_teams(df: pd.DataFrame, *, season: str | None = None) -> list[str]:
    x = df
    if season is not None:
        x = x[x["season"].astype(str) == str(season)]
    teams = sorted(set(x["home_team"].astype(str)).union(set(x["away_team"].astype(str))))
    return teams


def team_logo(team_name: str) -> bytes:
    """Return logo **bytes** for a team.

    We download logos with browser-like headers and return bytes to Streamlit,
    because some hosts block Streamlit's default image downloader.
    """
    return get_team_logo_image(team_name, size=128)


@st.cache_resource
def get_poisson_model_cached(
    processed_path: str,
    seasons: Tuple[str, ...],
    max_goals: int,
    smoothing_k: float,
) -> PoissonTeamStrengthModel:
    df = load_matches_cached(processed_path)
    if seasons:
        df = df[df["season"].astype(str).isin([str(s) for s in seasons])]
    model = PoissonTeamStrengthModel(max_goals=max_goals, smoothing_k=smoothing_k).fit(df)
    return model

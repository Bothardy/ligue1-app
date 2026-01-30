from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Tuple

import pandas as pd

from src.utils.log import get_logger

logger = get_logger(__name__)
Context = Literal["home", "away"]


@dataclass(frozen=True)
class TeamContextStats:
    team: str
    context: Context
    matches: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int
    points_per_match: float
    win_rate: float
    draw_rate: float
    loss_rate: float
    avg_goals_for: float
    avg_goals_against: float


def _team_long(matches: pd.DataFrame) -> pd.DataFrame:
    """Convert match-level data to team-level rows (two rows per played match)."""
    m = matches[matches["is_played"]].copy()
    m = m.sort_values(["match_date", "match_datetime"], na_position="last")

    home = pd.DataFrame(
        {
            "match_id": m["match_id"],
            "season": m["season"],
            "match_date": m["match_date"],
            "match_datetime": m["match_datetime"],
            "team": m["home_team"],
            "opponent": m["away_team"],
            "context": "home",
            "goals_for": m["home_goals"].astype(int),
            "goals_against": m["away_goals"].astype(int),
            "points": m["points_home"].astype(int),
            "result": m["result"],
        }
    )

    away = pd.DataFrame(
        {
            "match_id": m["match_id"],
            "season": m["season"],
            "match_date": m["match_date"],
            "match_datetime": m["match_datetime"],
            "team": m["away_team"],
            "opponent": m["home_team"],
            "context": "away",
            "goals_for": m["away_goals"].astype(int),
            "goals_against": m["home_goals"].astype(int),
            "points": m["points_away"].astype(int),
            "result": m["result"].map({"H": "A", "A": "H", "D": "D"}),  # perspective of away team
        }
    )

    return pd.concat([home, away], ignore_index=True)


def compute_home_away_stats(matches: pd.DataFrame, *, season: str | None = None) -> pd.DataFrame:
    """Compute home/away statistics per team.

    Parameters
    ----------
    matches:
        Cleaned matches dataframe.
    season:
        Optional season filter (e.g., "2526"). If None, uses all seasons.

    Returns
    -------
    pd.DataFrame
        One row per (team, context) with aggregated stats.
    """
    df = matches.copy()
    if season is not None:
        df = df[df["season"].astype(str) == str(season)]

    long_df = _team_long(df)

    def agg(g: pd.DataFrame) -> pd.Series:
        wins = int((g["result"] == "H").sum())
        draws = int((g["result"] == "D").sum())
        losses = int((g["result"] == "A").sum())
        matches_n = int(len(g))
        gf = int(g["goals_for"].sum())
        ga = int(g["goals_against"].sum())
        pts = int(g["points"].sum())
        return pd.Series(
            {
                "matches": matches_n,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "goals_for": gf,
                "goals_against": ga,
                "goal_diff": gf - ga,
                "points": pts,
                "points_per_match": pts / matches_n if matches_n else 0.0,
                "win_rate": wins / matches_n if matches_n else 0.0,
                "draw_rate": draws / matches_n if matches_n else 0.0,
                "loss_rate": losses / matches_n if matches_n else 0.0,
                "avg_goals_for": gf / matches_n if matches_n else 0.0,
                "avg_goals_against": ga / matches_n if matches_n else 0.0,
            }
        )

    out = long_df.groupby(["team", "context"], as_index=False).apply(agg).reset_index(drop=True)
    out = out.sort_values(["team", "context"])
    return out


def compute_recent_form(matches: pd.DataFrame, *, team: str, n: int = 5, season: str | None = None) -> Tuple[str, int]:
    """Return recent form string (e.g. "W-D-L-W-W") and points over last n matches."""
    df = matches[matches["is_played"]].copy()
    if season is not None:
        df = df[df["season"].astype(str) == str(season)]

    df = df.sort_values(["match_date", "match_datetime"], na_position="last")

    # create team-long and filter
    long_df = _team_long(df)
    t = long_df[long_df["team"] == team].tail(n)

    # result from team's perspective: H=win, D=draw, A=loss
    mapping = {"H": "W", "D": "D", "A": "L"}
    form = "-".join(mapping.get(r, "?") for r in t["result"].astype(str).tolist())
    points = int(t["points"].sum()) if len(t) else 0
    return form, points

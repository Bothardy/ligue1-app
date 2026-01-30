from __future__ import annotations

import pandas as pd


def compute_standings(matches: pd.DataFrame, *, season: str) -> pd.DataFrame:
    """Compute the league table for a given season.

    Notes
    -----
    - Uses only played matches.
    - Tie-breakers are simplified to: points, goal difference, goals for.

    Parameters
    ----------
    matches:
        Cleaned matches dataframe.
    season:
        Season code (e.g. "2526").

    Returns
    -------
    pd.DataFrame
        Table with columns: rank, team, played, wins, draws, losses, gf, ga, gd, points.
    """
    df = matches[matches["is_played"]].copy()
    df = df[df["season"].astype(str) == str(season)]

    if df.empty:
        return pd.DataFrame(
            columns=["rank", "team", "played", "wins", "draws", "losses", "gf", "ga", "gd", "points"]
        )

    # Home rows
    home = pd.DataFrame(
        {
            "team": df["home_team"].astype(str),
            "gf": df["home_goals"].astype(int),
            "ga": df["away_goals"].astype(int),
            "points": df["points_home"].astype(int),
            "result": df["result"].astype(str),
        }
    )

    # Away rows (result from away perspective)
    away_res = df["result"].map({"H": "L", "A": "W", "D": "D"}).astype(str)
    away = pd.DataFrame(
        {
            "team": df["away_team"].astype(str),
            "gf": df["away_goals"].astype(int),
            "ga": df["home_goals"].astype(int),
            "points": df["points_away"].astype(int),
            "result": away_res,
        }
    )

    long = pd.concat([home, away], ignore_index=True)

    def agg(g: pd.DataFrame) -> pd.Series:
        wins = int((g["result"] == "W").sum())
        draws = int((g["result"] == "D").sum())
        losses = int((g["result"] == "L").sum())
        played = int(len(g))
        gf = int(g["gf"].sum())
        ga = int(g["ga"].sum())
        points = int(g["points"].sum())
        return pd.Series(
            {
                "played": played,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "gf": gf,
                "ga": ga,
                "gd": gf - ga,
                "points": points,
            }
        )

    table = long.groupby("team", as_index=False).apply(agg).reset_index(drop=True)
    table = table.sort_values(["points", "gd", "gf"], ascending=[False, False, False]).reset_index(drop=True)
    table.insert(0, "rank", range(1, len(table) + 1))
    return table


def compute_cumulative_points(matches: pd.DataFrame, *, season: str, team: str) -> pd.DataFrame:
    """Compute cumulative points over time for one team within a season."""
    df = matches[matches["is_played"]].copy()
    df = df[df["season"].astype(str) == str(season)]
    df = df.sort_values(["match_date", "match_datetime"], na_position="last")

    # team-long view
    home = df[df["home_team"] == team].copy()
    home["points"] = home["points_home"].astype(int)
    home["opponent"] = home["away_team"].astype(str)
    home["context"] = "home"

    away = df[df["away_team"] == team].copy()
    away["points"] = away["points_away"].astype(int)
    away["opponent"] = away["home_team"].astype(str)
    away["context"] = "away"

    t = pd.concat([home, away], ignore_index=True)
    if t.empty:
        return pd.DataFrame(columns=["match_date", "opponent", "context", "points", "cum_points"])

    t = t.sort_values(["match_date", "match_datetime"], na_position="last")
    t["cum_points"] = t["points"].cumsum()
    return t[["match_date", "opponent", "context", "points", "cum_points"]]

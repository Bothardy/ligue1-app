from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.cleaning import clean_matches


def test_clean_matches_basic(tmp_path: Path) -> None:
    csv_content = """Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR
F1,01/01/25,TeamA,TeamB,2,1,H
F1,02/01/25,TeamC,TeamA,0,0,D
"""
    p = tmp_path / "F1_2425.csv"
    p.write_text(csv_content, encoding="utf-8")

    df = clean_matches([p], seasons=["2425"])

    assert len(df) == 2
    expected_cols = {
        "match_id",
        "season",
        "match_date",
        "match_datetime",
        "home_team",
        "away_team",
        "home_goals",
        "away_goals",
        "result",
        "points_home",
        "points_away",
        "is_played",
    }
    assert expected_cols.issubset(set(df.columns))

    # First match TeamA home win -> 3 points for home
    r0 = df.iloc[0]
    assert r0["result"] in {"H", "D", "A"}
    assert int(df.loc[df["home_team"] == "TeamA", "points_home"].iloc[0]) == 3

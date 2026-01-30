from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

import pandas as pd

from src.utils.log import get_logger

logger = get_logger(__name__)


def _poisson_pmf(k: int, lam: float) -> float:
    """Poisson probability mass function for small k (we limit k to MAX_GOALS)."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam**k) / math.factorial(k)


@dataclass
class TeamStrengths:
    league_avg_home_goals: float
    league_avg_away_goals: float
    attack_home: Dict[str, float]
    defense_home: Dict[str, float]
    attack_away: Dict[str, float]
    defense_away: Dict[str, float]


class PoissonTeamStrengthModel:
    """Simple Poisson model based on team attack/defense strengths (home vs away)."""

    def __init__(self, *, max_goals: int = 7, smoothing_k: float = 3.0) -> None:
        self.max_goals = int(max_goals)
        self.smoothing_k = float(smoothing_k)
        self.strengths: TeamStrengths | None = None

    def fit(self, matches: pd.DataFrame) -> "PoissonTeamStrengthModel":
        """Fit strengths from historical played matches."""
        m = matches[matches["is_played"]].copy()
        if m.empty:
            raise ValueError("No played matches found to fit the model.")

        total_matches = len(m)
        total_home_goals = float(m["home_goals"].sum())
        total_away_goals = float(m["away_goals"].sum())

        avg_home = total_home_goals / total_matches
        avg_away = total_away_goals / total_matches

        # Aggregate by team for home context
        home_group = m.groupby("home_team")
        home_matches = home_group.size()
        home_scored = home_group["home_goals"].sum()
        home_conceded = home_group["away_goals"].sum()

        # Aggregate by team for away context
        away_group = m.groupby("away_team")
        away_matches = away_group.size()
        away_scored = away_group["away_goals"].sum()
        away_conceded = away_group["home_goals"].sum()

        # Smoothed means then ratios to league average
        def smoothed_ratio(goals: pd.Series, games: pd.Series, league_avg: float) -> Dict[str, float]:
            out: Dict[str, float] = {}
            for team in games.index:
                g = float(goals.get(team, 0.0))
                n = float(games.get(team, 0.0))
                mean = (g + self.smoothing_k * league_avg) / (n + self.smoothing_k) if (n + self.smoothing_k) > 0 else league_avg
                out[str(team)] = mean / league_avg if league_avg > 0 else 1.0
            return out

        attack_home = smoothed_ratio(home_scored, home_matches, avg_home)
        defense_home = smoothed_ratio(home_conceded, home_matches, avg_away)
        attack_away = smoothed_ratio(away_scored, away_matches, avg_away)
        defense_away = smoothed_ratio(away_conceded, away_matches, avg_home)

        self.strengths = TeamStrengths(
            league_avg_home_goals=avg_home,
            league_avg_away_goals=avg_away,
            attack_home=attack_home,
            defense_home=defense_home,
            attack_away=attack_away,
            defense_away=defense_away,
        )

        logger.info(
            "Fitted Poisson strengths on %d matches. League avg (home=%.3f, away=%.3f)",
            total_matches,
            avg_home,
            avg_away,
        )
        return self

    def expected_goals(self, home_team: str, away_team: str) -> Tuple[float, float]:
        """Compute expected goals (λ_home, λ_away) for a given matchup."""
        if self.strengths is None:
            raise RuntimeError("Model is not fitted. Call fit() first.")

        s = self.strengths
        a_h = s.attack_home.get(home_team, 1.0)
        d_h = s.defense_home.get(home_team, 1.0)
        a_a = s.attack_away.get(away_team, 1.0)
        d_a = s.defense_away.get(away_team, 1.0)

        lam_home = s.league_avg_home_goals * a_h * d_a
        lam_away = s.league_avg_away_goals * a_a * d_h
        return float(lam_home), float(lam_away)

    def score_matrix(self, lam_home: float, lam_away: float) -> pd.DataFrame:
        """Probability matrix P(HomeGoals=i, AwayGoals=j) for i,j in [0..max_goals]."""
        max_g = self.max_goals
        probs = []
        for i in range(max_g + 1):
            row = []
            p_i = _poisson_pmf(i, lam_home)
            for j in range(max_g + 1):
                row.append(p_i * _poisson_pmf(j, lam_away))
            probs.append(row)
        mat = pd.DataFrame(probs, index=list(range(max_g + 1)), columns=list(range(max_g + 1)))
        mat.index.name = "HomeGoals"
        mat.columns.name = "AwayGoals"
        return mat

    def predict_proba(self, home_team: str, away_team: str) -> Dict[str, float]:
        """Predict 1X2 probabilities + expected goals."""
        lam_home, lam_away = self.expected_goals(home_team, away_team)
        mat = self.score_matrix(lam_home, lam_away)

        p_home = float(mat.where(mat.index.to_series().values[:, None] > mat.columns.values).sum().sum())
        p_draw = float(mat.where(mat.index.to_series().values[:, None] == mat.columns.values).sum().sum())
        p_away = float(mat.where(mat.index.to_series().values[:, None] < mat.columns.values).sum().sum())

        # Normalize (matrix is truncated at max_goals, so total may be < 1)
        total = p_home + p_draw + p_away
        if total > 0:
            p_home, p_draw, p_away = p_home / total, p_draw / total, p_away / total

        # Most likely score
        max_loc = mat.stack().idxmax()
        most_likely_home, most_likely_away = int(max_loc[0]), int(max_loc[1])

        return {
            "p_home_win": p_home,
            "p_draw": p_draw,
            "p_away_win": p_away,
            "lambda_home": lam_home,
            "lambda_away": lam_away,
            "expected_total_goals": lam_home + lam_away,
            "most_likely_home_goals": most_likely_home,
            "most_likely_away_goals": most_likely_away,
        }

    def evaluate(self, matches: pd.DataFrame, *, test_season: str | None = None) -> Dict[str, float]:
        """Evaluate the model with a simple temporal split.

        If test_season is provided, train on all other seasons and test on that one.
        Otherwise, train on the oldest 80% matches and test on the newest 20%.
        """
        df = matches[matches["is_played"]].copy()
        df = df.sort_values(["match_date", "match_datetime"], na_position="last")
        if df.empty:
            raise ValueError("No played matches to evaluate.")

        if test_season is not None:
            train = df[df["season"].astype(str) != str(test_season)]
            test = df[df["season"].astype(str) == str(test_season)]
            if test.empty or train.empty:
                raise ValueError("Not enough data for the requested test_season split.")
        else:
            split = int(0.8 * len(df))
            train, test = df.iloc[:split], df.iloc[split:]

        model = PoissonTeamStrengthModel(max_goals=self.max_goals, smoothing_k=self.smoothing_k).fit(train)

        correct = 0
        n = 0
        log_losses = []

        for _, row in test.iterrows():
            proba = model.predict_proba(str(row["home_team"]), str(row["away_team"]))
            p_home, p_draw, p_away = proba["p_home_win"], proba["p_draw"], proba["p_away_win"]

            pred = "H" if p_home >= max(p_draw, p_away) else ("D" if p_draw >= p_away else "A")
            actual = str(row["result"])
            if pred == actual:
                correct += 1
            n += 1

            p_true = {"H": p_home, "D": p_draw, "A": p_away}.get(actual, 1.0 / 3.0)
            p_true = min(max(float(p_true), 1e-12), 1.0)
            log_losses.append(-math.log(p_true))

        accuracy = correct / n if n else 0.0
        log_loss = float(sum(log_losses) / len(log_losses)) if log_losses else float("nan")

        return {
            "n_test": float(n),
            "accuracy": float(accuracy),
            "log_loss": float(log_loss),
            "split": f"test_season={test_season}" if test_season else "temporal_80_20",
        }

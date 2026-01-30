from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _parse_csv_list(value: str | None, default: str) -> List[str]:
    raw = (value or default).strip()
    if not raw:
        return [s for s in default.split(",") if s.strip()]
    return [s.strip() for s in raw.split(",") if s.strip()]


@dataclass(frozen=True)
class Settings:
    """Global application settings loaded from environment variables."""

    # Data
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
    raw_dir: Path = Path(os.getenv("RAW_DIR", "data/raw"))
    processed_dir: Path = Path(os.getenv("PROCESSED_DIR", "data/processed"))

    # Football-Data.co.uk settings
    division: str = os.getenv("DIVISION", "F1")
    seasons: List[str] = None  # initialized in __post_init__

    # Model
    max_goals: int = int(os.getenv("MAX_GOALS", "7"))
    form_n: int = int(os.getenv("FORM_N", "5"))
    smoothing_k: float = float(os.getenv("SMOOTHING_K", "3.0"))

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "seasons",
            _parse_csv_list(os.getenv("SEASONS"), default="2526,2425,2324"),
        )


def get_settings() -> Settings:
    """Return settings (create folders if needed)."""
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    s.raw_dir.mkdir(parents=True, exist_ok=True)
    s.processed_dir.mkdir(parents=True, exist_ok=True)
    return s

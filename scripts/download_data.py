from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from src.config import get_settings
from src.data.cleaning import clean_matches, save_clean_matches
from src.data.fetch import download_many
from src.utils.log import get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and preprocess Ligue 1 match data.")
    parser.add_argument(
        "--seasons",
        type=str,
        default=None,
        help="Comma-separated season codes (e.g., 2324,2425,2526). Defaults to SEASONS env or built-in default.",
    )
    parser.add_argument(
        "--division",
        type=str,
        default=None,
        help="Division code (default from env, for Ligue 1 it's F1).",
    )
    parser.add_argument("--force", action="store_true", help="Force re-download even if cached.")
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output CSV path for processed data (default: data/processed/matches_clean.csv).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()

    seasons: List[str] = settings.seasons
    if args.seasons:
        seasons = [s.strip() for s in args.seasons.split(",") if s.strip()]

    division = args.division or settings.division

    logger.info("Downloading seasons=%s division=%s", seasons, division)
    raw_paths = download_many(seasons=seasons, division=division, raw_dir=settings.raw_dir, force=args.force)

    df = clean_matches(raw_paths, seasons=seasons)

    out_path = Path(args.out) if args.out else settings.processed_dir / "matches_clean.csv"
    save_clean_matches(df, out_path)

    logger.info("Done. You can now run: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()

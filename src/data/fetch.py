from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable, List, Tuple

import requests

from src.utils.log import get_logger

logger = get_logger(__name__)

BASE_URL_TEMPLATE = "https://www.football-data.co.uk/mmz4281/{season}/{division}.csv"


class DownloadError(RuntimeError):
    """Raised when a CSV download fails."""


def build_season_url(season: str, division: str) -> str:
    """Build the Football-Data.co.uk URL for a given season and division."""
    return BASE_URL_TEMPLATE.format(season=season, division=division)


def _download_with_retries(
    url: str,
    dest_path: Path,
    *,
    timeout_s: int = 20,
    max_retries: int = 4,
    backoff_s: float = 1.5,
) -> None:
    """Download a URL to a local file with retries and basic rate-limit handling."""
    session = requests.Session()
    last_err: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Downloading %s (attempt %s/%s)", url, attempt, max_retries)
            resp = session.get(url, timeout=timeout_s)
            # Basic rate-limit handling
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else backoff_s * attempt
                logger.warning("Rate limited (429). Sleeping %.1fs then retrying...", wait)
                time.sleep(wait)
                continue

            resp.raise_for_status()
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(resp.content)
            logger.info("Saved to %s (%d bytes)", dest_path, dest_path.stat().st_size)
            return
        except Exception as e:  # noqa: BLE001
            last_err = e
            wait = backoff_s * attempt
            logger.warning("Download failed: %s. Retrying in %.1fs", e, wait)
            time.sleep(wait)

    raise DownloadError(f"Failed to download {url} after {max_retries} attempts") from last_err


def download_season_csv(
    season: str,
    division: str,
    raw_dir: Path,
    *,
    force: bool = False,
) -> Path:
    """Ensure the CSV for (season, division) exists locally; download if needed."""
    filename = f"{division}_{season}.csv"
    dest = raw_dir / filename
    if dest.exists() and not force:
        logger.info("Using cached file: %s", dest)
        return dest

    url = build_season_url(season=season, division=division)
    _download_with_retries(url, dest)
    return dest


def download_many(
    seasons: Iterable[str],
    division: str,
    raw_dir: Path,
    *,
    force: bool = False,
) -> List[Path]:
    """Download multiple seasons and return local file paths."""
    paths: List[Path] = []
    for s in seasons:
        paths.append(download_season_csv(s, division, raw_dir, force=force))
    return paths


def quick_head_check(url: str) -> Tuple[bool, int]:
    """Small helper for debugging: check if URL is reachable."""
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
        return resp.ok, resp.status_code
    except Exception:  # noqa: BLE001
        return False, -1

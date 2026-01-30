"""Team logo utilities.

Goal
----
Display *real* club crests (not placeholders) as reliably as possible.

What we use
-----------
We rely on the official **monochrome** club crests hosted on ligue1.com
(LFP Media). These URLs are stable and don't require any API key.

Why monochrome?
--------------
Some color-logo sources block Python/Streamlit downloaders (anti-bot /
hotlink protection). The official monochrome assets are much more
reliable for a school project demo.

If downloading still fails (offline / corporate firewall), we generate a
small placeholder PNG with the team initials so the UI never breaks.

Note: logos are the property of their respective owners.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Optional

import requests


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0 Safari/537.36"
)

IMAGE_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Referer": "https://ligue1.com/",
}


def _download_image_bytes(url: str) -> Optional[bytes]:
    """Download an image and return bytes (or None)."""

    if not url:
        return None

    try:
        r = requests.get(url, timeout=10, headers=IMAGE_HEADERS)
    except Exception:
        return None

    if r.status_code != 200:
        return None

    ctype = (r.headers.get("content-type") or "").lower()
    if "image" not in ctype:
        return None

    if not r.content or len(r.content) < 256:
        return None

    return r.content


# ---------------------------------------------------------------------------
# Team name normalization + mapping to LFP filenames
# ---------------------------------------------------------------------------


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("'", " ").replace(".", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# Football-Data (and our cleaned dataset) can use slightly different names.
# This mapping points to the **exact** file basenames used by ligue1.com.
TEAM_TO_LFP_FILE: dict[str, str] = {
    # Core Ligue 1 (common)
    "angers": "Angers",
    "angers sco": "Angers",
    "auxerre": "Auxerre",
    "aj auxerre": "Auxerre",
    "brest": "Brest",
    "stade brestois": "Brest",
    "le havre": "Le-Havre",
    "havre": "Le-Havre",
    "lehavre": "Le-Havre",
    "lorient": "Lorient",
    "lens": "Lens",
    "rc lens": "Lens",
    "lille": "Lille",
    "losc": "Lille",
    "lyon": "Lyon",
    "ol": "Lyon",
    "marseille": "Marseille",
    "om": "Marseille",
    "metz": "Metz",
    "fc metz": "Metz",
    "monaco": "Monaco",
    "as monaco": "Monaco",
    "nantes": "Nantes",
    "fc nantes": "Nantes",
    "nice": "Nice",
    "ogc nice": "Nice",
    "paris sg": "Paris",
    "psg": "Paris",
    "paris saint germain": "Paris",
    "paris saint-germain": "Paris",
    "paris": "Paris",
    "paris fc": "Paris_FC",
    "rennes": "Rennes",
    "stade rennais": "Rennes",
    "reims": "Reims",
    "strasbourg": "Strasbourg",
    "rc strasbourg": "Strasbourg",
    "toulouse": "Toulouse",
    "toulouse fc": "Toulouse",
    # Teams often present historically (may now be in L2)
    "clermont": "Clermont",
    "clermont foot": "Clermont",
    "montpellier": "Montpellier",
    "st etienne": "Saint-Etienne",
    "saint etienne": "Saint-Etienne",
    "saint-etienne": "Saint-Etienne",
    "stade lavallois": "Laval",
    "bordeaux": "Bordeaux",
    "ajaccio": "Ajaccio",
}


def _guess_lfp_filename(team_name: str) -> str:
    """Heuristic fallback (works for many clubs).

    Converts "le havre" -> "Le-Havre", "paris fc" -> "Paris-Fc" (not perfect),
    etc. We still keep explicit mapping for tricky teams.
    """

    key = _norm(team_name)
    parts = [p for p in key.split() if p]
    parts = [p.capitalize() for p in parts]
    return "-".join(parts) if parts else "Ligue1"


# ---------------------------------------------------------------------------
# LFP URLs
# ---------------------------------------------------------------------------

LFP_MONO_BASE = "https://ligue1.com/images/clubs/monochrome"


@lru_cache(maxsize=512)
def get_team_logo_urls(team_name: str) -> tuple[str, ...]:
    """Return candidate logo URLs for a team.

    We try both L1 and L2 folders because ligue1.com stores crests under the
    *current* championship universe.
    """

    key = _norm(team_name)
    file_base = TEAM_TO_LFP_FILE.get(key) or _guess_lfp_filename(team_name)

    return (
        f"{LFP_MONO_BASE}/L1/{file_base}.webp",
        f"{LFP_MONO_BASE}/L2/{file_base}.webp",
    )


def _placeholder_png(team_name: str, *, size: int = 128) -> bytes:
    """Generate a small fallback PNG with team initials."""

    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return b""

    s = max(64, int(size))
    img = Image.new("RGBA", (s, s), (245, 247, 250, 255))
    draw = ImageDraw.Draw(img)

    # Deterministic accent color from the team name.
    h = abs(hash(_norm(team_name))) % 360
    import colorsys

    r, g, b = colorsys.hls_to_rgb(h / 360.0, 0.55, 0.55)
    color = (int(r * 255), int(g * 255), int(b * 255), 255)

    pad = int(s * 0.08)
    draw.ellipse([pad, pad, s - pad, s - pad], fill=color)

    parts = [p for p in _norm(team_name).split() if p]
    initials = "".join(p[0].upper() for p in parts[:2]) or "?"

    try:
        font = ImageFont.truetype("arial.ttf", int(s * 0.38))
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), initials, font=font)
    w = bbox[2] - bbox[0]
    htxt = bbox[3] - bbox[1]
    x = (s - w) / 2
    y = (s - htxt) / 2 - 2
    draw.text((x, y), initials, fill=(255, 255, 255, 255), font=font)

    from io import BytesIO

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@lru_cache(maxsize=512)
def get_team_logo_image(team_name: str, *, size: int = 128) -> bytes:
    """Return logo **bytes** for Streamlit.

    This is the function you should use in the UI (`st.image(bytes)`).
    """

    for url in get_team_logo_urls(team_name):
        b = _download_image_bytes(url)
        if b:
            return b

    return _placeholder_png(team_name, size=size)

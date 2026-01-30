from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pandas as pd
import streamlit as st

# Ensure project root is in sys.path (Streamlit runs scripts from /app)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ui.branding import APP_SUBTITLE, APP_TITLE, DATA_SOURCES_MD, DISCLAIMER_MD, LEAGUE_LOGO_URL
from src.ui.style import build_css


def init_page(*, page_title: str, page_icon: str = "⚽", layout: str = "wide") -> None:
    """Initialize Streamlit page with common style + sidebar.

    Must be called at the top of every page (before any other Streamlit command).
    """

    st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)
    st.markdown(build_css(), unsafe_allow_html=True)


def render_sidebar(*, processed_path: str | None = None, seasons: list[str] | None = None) -> None:
    """Render a branded sidebar with dataset status."""

    with st.sidebar:
        # Brand badge: gradient background so the (often white) official logo is visible.
        st.markdown(
            f'<div class="brand-badge"><img src="{LEAGUE_LOGO_URL}" alt="Ligue 1 logo" /></div>',
            unsafe_allow_html=True,
        )

        st.markdown(f"### {APP_TITLE}")
        st.caption(APP_SUBTITLE)

        if processed_path is not None:
            p = Path(processed_path)
            if p.exists():
                updated_at = datetime.fromtimestamp(p.stat().st_mtime)
                st.success("Dataset prêt ✅")
                st.write(f"Dernière mise à jour : **{updated_at:%Y-%m-%d %H:%M}**")
            else:
                st.warning("Dataset manquant")
                st.code("python -m scripts.download_data", language="bash")

        if seasons:
            st.markdown("---")
            st.markdown("**Saisons disponibles**")
            st.write(", ".join(seasons))

        st.markdown("---")
        st.caption(DISCLAIMER_MD)
        st.caption(DATA_SOURCES_MD)


def card(title: str, body_html: str, *, icon: str = "") -> None:
    """Render a simple HTML card.

    Why this function exists:
    Streamlit's markdown parser can interpret indented HTML blocks as *code blocks*,
    which is exactly what you saw on the Home page (HTML showing as text).

    Fix:
    We build the HTML with **no indentation** and no blank lines so it's always
    parsed as HTML and rendered correctly.
    """

    body_html = dedent(body_html).strip()

    icon_html = f"<span class='card-icon'>{icon}</span>" if icon else ""
    html = (
        "<div class='card'>"
        f"<div class='card-header'>{icon_html}<h3>{title}</h3></div>"
        f"<div class='card-body'>{body_html}</div>"
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def kpi_row(kpis: list[tuple[str, str]]) -> None:
    """Render KPIs (label, value) as a grid."""

    items_html = "".join(
        f"<div class='kpi-item'><div class='kpi-label'>{label}</div><div class='kpi-value'>{value}</div></div>"
        for label, value in kpis
    )
    st.markdown(f"<div class='kpi'>{items_html}</div>", unsafe_allow_html=True)


def format_pct(x: float) -> str:
    return f"{100*x:.1f}%" if pd.notna(x) else "—"

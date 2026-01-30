from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path (Streamlit runs scripts from /app)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


import streamlit as st

from common import load_matches_cached, settings_cached
from layout import card, init_page, kpi_row, render_sidebar
from src.features.standings import compute_standings
from src.ui.branding import APP_TITLE, APP_SUBTITLE, LEAGUE_LOGO_URL


init_page(page_title=APP_TITLE, page_icon="⚽")

settings = settings_cached()
processed_path = str(settings.processed_dir / "matches_clean.csv")

# Sidebar (branded)
try:
    # We render the sidebar even if dataset missing
    render_sidebar(processed_path=processed_path)
except Exception:  # noqa: BLE001
    pass

# --- Header / Hero ---
col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.image(LEAGUE_LOGO_URL, use_container_width=True)
with col_title:
    st.markdown(f"# {APP_TITLE}")
    st.markdown(f"<span class='badge'>{APP_SUBTITLE}</span>", unsafe_allow_html=True)

st.write("")

card(
    "🎯 Objectif",
    """
    <ul style="margin:0; padding-left: 1.1rem;">
      <li><b>Consulter</b> les scores et le calendrier (filtres équipe / saison / dates)</li>
      <li><b>Analyser</b> les performances <b>domicile vs extérieur</b> + la forme récente</li>
      <li><b>Prédire</b> un match (probabilités 1/X/2 + buts attendus) via un modèle de Poisson</li>
    </ul>
    <div style="margin-top: 10px;">
      <span class="badge">Tip</span>
      &nbsp;Si tu viens de cloner le projet, lance d'abord :
      <code style="padding: 2px 6px; border-radius: 8px; background: rgba(11,27,43,0.06); border: 1px solid rgba(11,27,43,0.10);">python -m scripts.download_data</code>
    </div>
    """,
)

st.write("")

# --- Dataset summary + mini standings ---
try:
    df = load_matches_cached(processed_path)
    seasons = sorted(df["season"].astype(str).unique().tolist(), reverse=True)
    latest_season = seasons[0] if seasons else None

    played = df[df["is_played"]].copy()
    last_date = played["match_date"].max() if not played.empty else None

    kpi_row(
        [
            ("Saisons", str(len(seasons))),
            ("Matchs (joués)", str(len(played))),
            ("Dernier match", str(last_date.date()) if last_date is not None else "—"),
        ]
    )

    st.write("")

    if latest_season:
        st.markdown("### 🏆 Aperçu classement (Top 10)")
        table = compute_standings(df, season=str(latest_season)).head(10)
        if not table.empty:
            st.dataframe(table, hide_index=True, use_container_width=True)
        else:
            st.info("Pas assez de matchs joués pour afficher un classement.")

    st.caption("Navigation : utilise les pages dans la barre latérale (Scores • Analyse • Classement • Prédiction).")

except Exception as e:  # noqa: BLE001
    st.warning("Dataset non chargé. Lance d'abord la préparation des données.")
    st.code("python -m scripts.download_data", language="bash")
    st.exception(e)

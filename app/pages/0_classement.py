from __future__ import annotations

import plotly.express as px
import streamlit as st

from common import available_seasons, load_matches_cached, settings_cached, team_logo
from layout import init_page, render_sidebar
from src.features.standings import compute_cumulative_points, compute_standings


init_page(page_title="Classement — Ligue 1 McDonald's", page_icon="🏆")

settings = settings_cached()
processed_path = str(settings.processed_dir / "matches_clean.csv")

# Load dataset
try:
    df = load_matches_cached(processed_path)
except Exception as e:  # noqa: BLE001
    render_sidebar(processed_path=processed_path)
    st.error("Dataset introuvable. Lance d'abord : `python -m scripts.download_data`")
    st.exception(e)
    st.stop()

seasons = available_seasons(df)
render_sidebar(processed_path=processed_path, seasons=seasons)

st.markdown("# 🏆 Classement")

season = st.selectbox("Saison", options=seasons, index=0)

stand = compute_standings(df, season=season)

if stand.empty:
    st.info("Pas de matchs joués pour cette saison (ou dataset incomplet).")
    st.stop()

# Add logos
stand = stand.copy()
stand.insert(1, "logo", stand["team"].apply(team_logo))

st.dataframe(
    stand,
    hide_index=True,
    use_container_width=True,
    column_config={
        "logo": st.column_config.ImageColumn("", width="small"),
        "rank": st.column_config.NumberColumn("#", width="small"),
        "team": st.column_config.TextColumn("Équipe"),
        "played": st.column_config.NumberColumn("MJ", width="small"),
        "wins": st.column_config.NumberColumn("G", width="small"),
        "draws": st.column_config.NumberColumn("N", width="small"),
        "losses": st.column_config.NumberColumn("P", width="small"),
        "gf": st.column_config.NumberColumn("BP", width="small"),
        "ga": st.column_config.NumberColumn("BC", width="small"),
        "gd": st.column_config.NumberColumn("Diff", width="small"),
        "points": st.column_config.NumberColumn("Pts", width="small"),
    },
)

st.markdown("---")
st.subheader("📈 Suivi points cumulés")

team = st.selectbox("Équipe", options=stand["team"].tolist(), index=0)
trend = compute_cumulative_points(df, season=season, team=team)

if trend.empty:
    st.info("Pas de données pour cette équipe.")
    st.stop()

fig = px.line(trend, x="match_date", y="cum_points", markers=True)
fig.update_layout(
    height=380,
    margin=dict(l=10, r=10, t=20, b=10),
    xaxis_title="Date",
    yaxis_title="Points cumulés",
)

st.plotly_chart(fig, use_container_width=True)

st.caption("Classement calculé à partir des matchs joués (tiebreak simplifié : points → diff → buts pour).")

from __future__ import annotations

import pandas as pd
import streamlit as st

from common import available_seasons, available_teams, load_matches_cached, settings_cached, team_logo
from layout import init_page, render_sidebar


init_page(page_title="Match Center — Ligue 1 McDonald's", page_icon="🗓️")

settings = settings_cached()
processed_path = str(settings.processed_dir / "matches_clean.csv")

try:
    df = load_matches_cached(processed_path)
except Exception as e:  # noqa: BLE001
    render_sidebar(processed_path=processed_path)
    st.error("Dataset introuvable. Lance d'abord : `python -m scripts.download_data`")
    st.exception(e)
    st.stop()

seasons = available_seasons(df)
render_sidebar(processed_path=processed_path, seasons=seasons)

st.markdown("# 🗓️ Match Center")

# --- Filters ---
col1, col2, col3 = st.columns([1.1, 1.3, 1.0])
with col1:
    season = st.selectbox("Saison", options=["Toutes"] + seasons, index=1 if seasons else 0)
with col2:
    team_scope_df = df if season == "Toutes" else df[df["season"].astype(str) == str(season)]
    teams = available_teams(df, season=None if season == "Toutes" else season)
    team = st.selectbox("Équipe", options=["Toutes"] + teams, index=0)
with col3:
    sort_order = st.selectbox("Tri", options=["Plus récents", "Plus anciens"], index=0)

view = df if season == "Toutes" else df[df["season"].astype(str) == str(season)].copy()
if team != "Toutes":
    view = view[(view["home_team"] == team) | (view["away_team"] == team)].copy()

min_date = view["match_date"].min()
max_date = view["match_date"].max()

st.markdown("### Filtre dates")
start_end = st.date_input(
    "Période",
    value=(
        (min_date.date() if pd.notna(min_date) else None),
        (max_date.date() if pd.notna(max_date) else None),
    ),
)

if isinstance(start_end, tuple) and len(start_end) == 2 and start_end[0] and start_end[1]:
    start, end = start_end
    view = view[(view["match_date"].dt.date >= start) & (view["match_date"].dt.date <= end)].copy()

cA, cB, cC, cD = st.columns([1, 1, 1, 2])
with cA:
    show_played = st.toggle("Joués", value=True)
with cB:
    show_upcoming = st.toggle("À venir", value=True)
with cC:
    show_logos = st.toggle("Logos", value=True)
with cD:
    max_rows = st.slider("Lignes", min_value=25, max_value=400, value=100, step=25)

if not show_played:
    view = view[~view["is_played"]].copy()
if not show_upcoming:
    view = view[view["is_played"]].copy()

# --- Prepare table ---
view = view.sort_values(["match_date", "match_datetime"], ascending=(sort_order == "Plus anciens"), na_position="last")

out = view.copy()
out["date"] = out["match_date"].dt.date
out["time"] = out["match_datetime"].dt.time.astype(str).replace("NaT", "")
out["score"] = out.apply(
    lambda r: f"{int(r['home_goals'])}-{int(r['away_goals'])}" if r["is_played"] else "—",
    axis=1,
)

if show_logos:
    out["home_logo"] = out["home_team"].apply(team_logo)
    out["away_logo"] = out["away_team"].apply(team_logo)
    cols = ["season", "date", "time", "home_logo", "home_team", "score", "away_team", "away_logo", "result"]
else:
    cols = ["season", "date", "time", "home_team", "score", "away_team", "result"]

out = out[cols]

# --- Quick summary ---
played_n = int(out["score"].ne("—").sum())
upcoming_n = int(out["score"].eq("—").sum())

c1, c2, c3 = st.columns(3)
c1.metric("Matchs affichés", str(len(out)))
c2.metric("Joués", str(played_n))
c3.metric("À venir", str(upcoming_n))

# --- Display ---
st.dataframe(
    out.head(max_rows),
    use_container_width=True,
    hide_index=True,
    column_config={
        "home_logo": st.column_config.ImageColumn("", width="small"),
        "away_logo": st.column_config.ImageColumn("", width="small"),
        "season": st.column_config.TextColumn("Saison", width="small"),
        "result": st.column_config.TextColumn("Résultat", width="small"),
    },
)

st.caption(
    "Logos et identité de marque : ligue1.com (LFP Media). "
    "Certaines saisons peuvent contenir peu de matchs (dataset local)."
)

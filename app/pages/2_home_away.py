from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from common import available_seasons, available_teams, load_matches_cached, settings_cached, team_logo
from layout import init_page, render_sidebar
from src.features.build import compute_home_away_stats, compute_recent_form


init_page(page_title="Team Analytics — Ligue 1 McDonald's", page_icon="📊")

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

st.markdown("# 📊 Team Analytics")

colA, colB = st.columns([1.1, 1.4])
with colA:
    season = st.selectbox("Saison", options=seasons, index=0 if seasons else 0)
with colB:
    teams = available_teams(df, season=season)
    team = st.selectbox("Équipe", options=teams)

# --- Header card ---
logo = team_logo(team)
col1, col2 = st.columns([1, 4])
with col1:
    st.image(logo, width=96)
with col2:
    st.markdown(f"## {team}")
    form_str, form_pts = compute_recent_form(df, team=team, n=settings.form_n, season=season)
    st.markdown(
        f"<span class='badge'>Saison {season}</span> &nbsp; "
        f"<span class='badge'>Forme ({settings.form_n}) : {form_str or '—'}</span> &nbsp; "
        f"<span class='badge'>Points ({settings.form_n}) : {form_pts}</span>",
        unsafe_allow_html=True,
    )

# --- Compute stats ---
stats = compute_home_away_stats(df, season=season)
team_stats = stats[stats["team"] == team].copy()

if team_stats.empty:
    st.warning("Pas de stats disponibles pour cette équipe/saison.")
    st.stop()

home = team_stats[team_stats["context"] == "home"].iloc[0]
away = team_stats[team_stats["context"] == "away"].iloc[0]

# --- KPI row ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Points / match (Home)", f"{home['points_per_match']:.2f}")
c2.metric("Points / match (Away)", f"{away['points_per_match']:.2f}")
c3.metric("Buts marqués / match (Home)", f"{home['avg_goals_for']:.2f}")
c4.metric("Buts marqués / match (Away)", f"{away['avg_goals_for']:.2f}")

st.markdown("---")

tabs = st.tabs(["🏠 vs ✈️ Home/Away", "📈 Comparaisons", "🧾 Derniers matchs", "🏅 Classements"])

# Tab 1: Home/Away comparison
with tabs[0]:
    comp = pd.DataFrame(
        {
            "Metric": [
                "Points / match",
                "Buts marqués / match",
                "Buts encaissés / match",
                "Diff buts / match",
                "Win rate",
            ],
            "Home": [
                float(home["points_per_match"]),
                float(home["avg_goals_for"]),
                float(home["avg_goals_against"]),
                float((home["goal_diff"] / home["matches"]) if home["matches"] else 0.0),
                float(home["win_rate"]),
            ],
            "Away": [
                float(away["points_per_match"]),
                float(away["avg_goals_for"]),
                float(away["avg_goals_against"]),
                float((away["goal_diff"] / away["matches"]) if away["matches"] else 0.0),
                float(away["win_rate"]),
            ],
        }
    )

    st.dataframe(comp, hide_index=True, use_container_width=True)

    melted = comp.melt(id_vars=["Metric"], var_name="Context", value_name="Value")
    fig = px.bar(melted, x="Metric", y="Value", color="Context", barmode="group")
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

# Tab 2: side-by-side distributions
with tabs[1]:
    st.markdown("### Distribution des résultats")
    dist = pd.DataFrame(
        {
            "Contexte": ["Home", "Away"],
            "Wins": [int(home["wins"]), int(away["wins"])],
            "Draws": [int(home["draws"]), int(away["draws"])],
            "Losses": [int(home["losses"]), int(away["losses"])],
        }
    )
    dist_m = dist.melt(id_vars=["Contexte"], var_name="Résultat", value_name="Matchs")
    fig2 = px.bar(dist_m, x="Résultat", y="Matchs", color="Contexte", barmode="group")
    fig2.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig2, use_container_width=True)

# Tab 3: last matches
with tabs[2]:
    st.markdown(f"### Derniers matchs — {team}")

    played = df[df["is_played"]].copy()
    played = played[played["season"].astype(str) == str(season)]
    played = played.sort_values(["match_date", "match_datetime"], ascending=False, na_position="last")

    last = played[(played["home_team"] == team) | (played["away_team"] == team)].head(10).copy()
    if last.empty:
        st.info("Pas de matchs joués trouvés.")
    else:
        last["date"] = last["match_date"].dt.date
        last["home_logo"] = last["home_team"].apply(team_logo)
        last["away_logo"] = last["away_team"].apply(team_logo)
        last["score"] = last.apply(lambda r: f"{int(r['home_goals'])}-{int(r['away_goals'])}", axis=1)
        out = last[["date", "home_logo", "home_team", "score", "away_team", "away_logo"]]
        st.dataframe(
            out,
            hide_index=True,
            use_container_width=True,
            column_config={
                "home_logo": st.column_config.ImageColumn("", width="small"),
                "away_logo": st.column_config.ImageColumn("", width="small"),
            },
        )

# Tab 4: rankings
with tabs[3]:
    st.markdown("### Top 10 — Points / match")
    home_top = stats[stats["context"] == "home"].sort_values("points_per_match", ascending=False).head(10).copy()
    away_top = stats[stats["context"] == "away"].sort_values("points_per_match", ascending=False).head(10).copy()

    home_top.insert(0, "logo", home_top["team"].apply(team_logo))
    away_top.insert(0, "logo", away_top["team"].apply(team_logo))

    c1, c2 = st.columns(2)
    with c1:
        st.caption("🏠 À domicile")
        st.dataframe(
            home_top[["logo", "team", "matches", "points_per_match", "avg_goals_for", "avg_goals_against"]],
            hide_index=True,
            use_container_width=True,
            column_config={"logo": st.column_config.ImageColumn("", width="small")},
        )
    with c2:
        st.caption("✈️ À l'extérieur")
        st.dataframe(
            away_top[["logo", "team", "matches", "points_per_match", "avg_goals_for", "avg_goals_against"]],
            hide_index=True,
            use_container_width=True,
            column_config={"logo": st.column_config.ImageColumn("", width="small")},
        )

st.caption("Astuce : la page Classement propose aussi un suivi des points cumulés par équipe.")

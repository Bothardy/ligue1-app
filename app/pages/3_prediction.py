from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from common import available_seasons, available_teams, get_poisson_model_cached, load_matches_cached, settings_cached, team_logo
from layout import init_page, render_sidebar
from src.models.poisson import PoissonTeamStrengthModel


init_page(page_title="Prediction Lab — Ligue 1 McDonald's", page_icon="🎯")

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

# Sidebar controls
render_sidebar(processed_path=processed_path, seasons=seasons)
with st.sidebar:
    st.markdown("---")
    st.subheader("Paramètres du modèle")
    train_seasons = st.multiselect(
        "Saisons pour l'entraînement",
        options=seasons,
        default=seasons,
    )
    max_goals = st.slider("Max buts (0..N)", min_value=5, max_value=10, value=settings.max_goals)
    smoothing_k = st.slider(
        "Smoothing k (stabilise les équipes avec peu de matchs)",
        min_value=0.0,
        max_value=10.0,
        value=float(settings.smoothing_k),
        step=0.5,
    )

if not train_seasons:
    st.warning("Sélectionne au moins une saison.")
    st.stop()

model = get_poisson_model_cached(processed_path, tuple(train_seasons), max_goals=max_goals, smoothing_k=smoothing_k)

st.markdown("# 🎯 Prediction Lab")
st.caption("Modèle Poisson interprétable : forces attaque/défense + avantage domicile.")

# Team selection
teams = available_teams(df, season=train_seasons[0] if len(train_seasons) == 1 else None)

colA, colB = st.columns(2)
with colA:
    home_team = st.selectbox("Équipe à domicile", options=teams, index=0 if teams else 0)
with colB:
    away_options = [t for t in teams if t != home_team]
    away_team = st.selectbox("Équipe à l'extérieur", options=away_options, index=0 if away_options else 0)

# Visual header with logos
l1, l2, l3 = st.columns([1, 3, 1])
with l1:
    st.image(team_logo(home_team), width=96)
with l2:
    st.markdown(f"## {home_team} vs {away_team}")
    st.markdown(
        f"<span class='badge'>Train : {', '.join(train_seasons)}</span> &nbsp; "
        f"<span class='badge'>Max goals : {max_goals}</span> &nbsp; "
        f"<span class='badge'>Smoothing k : {smoothing_k:.1f}</span>",
        unsafe_allow_html=True,
    )
with l3:
    st.image(team_logo(away_team), width=96)

proba = model.predict_proba(home_team, away_team)

# KPIs
k1, k2, k3 = st.columns(3)
k1.metric("1 (Home)", f"{proba['p_home_win']*100:.1f}%")
k2.metric("X (Draw)", f"{proba['p_draw']*100:.1f}%")
k3.metric("2 (Away)", f"{proba['p_away_win']*100:.1f}%")

k4, k5, k6 = st.columns(3)
k4.metric("λ Home", f"{proba['lambda_home']:.2f}")
k5.metric("λ Away", f"{proba['lambda_away']:.2f}")
k6.metric("Total buts", f"{proba['expected_total_goals']:.2f}")

st.markdown(
    f"**Score le plus probable (grille 0..{max_goals}) :** "
    f"{proba['most_likely_home_goals']} - {proba['most_likely_away_goals']}"
)

# Probability bar
prob_df = pd.DataFrame(
    {
        "Issue": ["1 (Home)", "X (Draw)", "2 (Away)"],
        "Probabilité": [proba["p_home_win"], proba["p_draw"], proba["p_away_win"]],
    }
)
figp = px.bar(prob_df, x="Issue", y="Probabilité", text=prob_df["Probabilité"].map(lambda x: f"{x*100:.1f}%"))
figp.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10), yaxis_tickformat=".0%")
st.plotly_chart(figp, use_container_width=True)

# Top scorelines
lam_home, lam_away = proba["lambda_home"], proba["lambda_away"]
mat = model.score_matrix(lam_home, lam_away)
top = mat.stack().sort_values(ascending=False).head(12).reset_index()
top.columns = ["HomeGoals", "AwayGoals", "Probability"]
top["Score"] = top["HomeGoals"].astype(str) + "-" + top["AwayGoals"].astype(str)

top = top[["Score", "Probability"]]
top["Probability"] = top["Probability"].astype(float)

with st.expander("🔢 Top scores probables"):
    st.dataframe(top, hide_index=True, use_container_width=True)

# Head-to-head
with st.expander("🤝 Head-to-head (historique)"):
    played = df[df["is_played"]].copy()
    h2h = played[((played["home_team"] == home_team) & (played["away_team"] == away_team)) | ((played["home_team"] == away_team) & (played["away_team"] == home_team))].copy()
    h2h = h2h.sort_values(["match_date", "match_datetime"], ascending=False, na_position="last").head(10)
    if h2h.empty:
        st.info("Aucun match H2H trouvé dans le dataset sélectionné.")
    else:
        h2h["date"] = h2h["match_date"].dt.date
        h2h["score"] = h2h.apply(lambda r: f"{int(r['home_goals'])}-{int(r['away_goals'])}", axis=1)
        h2h["home_logo"] = h2h["home_team"].apply(team_logo)
        h2h["away_logo"] = h2h["away_team"].apply(team_logo)
        out = h2h[["season", "date", "home_logo", "home_team", "score", "away_team", "away_logo"]]
        st.dataframe(
            out,
            hide_index=True,
            use_container_width=True,
            column_config={
                "home_logo": st.column_config.ImageColumn("", width="small"),
                "away_logo": st.column_config.ImageColumn("", width="small"),
            },
        )

# Explanation + evaluation
with st.expander("🧠 Explication (attaque / défense)"):
    s = model.strengths
    assert s is not None
    explanation = pd.DataFrame(
        [
            {
                "Équipe": home_team,
                "Contexte": "Home",
                "Attack strength": float(s.attack_home.get(home_team, 1.0)),
                "Defense strength": float(s.defense_home.get(home_team, 1.0)),
            },
            {
                "Équipe": away_team,
                "Contexte": "Away",
                "Attack strength": float(s.attack_away.get(away_team, 1.0)),
                "Defense strength": float(s.defense_away.get(away_team, 1.0)),
            },
        ]
    )
    st.dataframe(explanation, hide_index=True, use_container_width=True)
    st.caption(
        "Interprétation : attack > 1 = meilleure attaque que la moyenne ; "
        "defense > 1 = défense plus faible (encaisse plus)."
    )

with st.expander("📏 Évaluation rapide"):
    test_season = st.selectbox("Saison test", options=["(split temporel 80/20)"] + seasons)
    evaluator = PoissonTeamStrengthModel(max_goals=max_goals, smoothing_k=smoothing_k)
    if test_season == "(split temporel 80/20)":
        metrics = evaluator.evaluate(df, test_season=None)
    else:
        metrics = evaluator.evaluate(df, test_season=str(test_season))

    st.json(metrics)
    st.caption("Log-loss plus bas = meilleur calibrage des probabilités. Accuracy = % de bons 1X2.")

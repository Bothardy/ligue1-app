## PROJET BY : SID AHMED LAMRI  ~~ EL MEHDI ALAOUI ~~ FAYCALE BOUTAHAR 

Application data-driven (Streamlit + Pandas + Docker) permettant :
- un **Match Center** (scores, calendrier, filtres) + logos,
- une page **Classement** (table + points cumulés),
- une page **Team Analytics** (Home/Away, forme récente, derniers matchs),
- une page **Prediction Lab** (Poisson : proba 1/X/2, buts attendus, top scores, head-to-head).

> ⚠️ Projet étudiant **non officiel** : aucune affiliation avec la LFP, les clubs, ou McDonald's.

---

## Membres du groupe
- Sid-ahmed LAMRI
- El Mehdi ALAOUI
- Fayçal BOUTAHAR

---

## Pré-requis
- Python 3.11+
- Docker (recommandé pour l’exécution “from scratch”)

---

## 1) Lancer en local (sans Docker)

### Installation
```bash
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
```
.\.venv\Scripts\python -m pip install python-dotenv

### Télécharger et préparer les données (Football-Data.co.uk)
```bash
python -m scripts.download_data
```

### Lancer l’application
```bash
python -m streamlit run app\streamlit_app.py
```

---

## 2) Lancer avec Docker

### Build
```bash
docker build -t ligue1-app .
```

### Run
> On monte `./data` dans le container pour conserver le cache de données.
```bash
docker run --rm -p 8501:8501 -v "$(pwd)/data:/app/data" ligue1-app
```

Ouvre ensuite : http://localhost:8501

---

## Configuration (.env)
Tu peux créer un fichier `.env` (non committé) pour régler les saisons, etc.

Exemple :
```bash
cp .env.example .env
```

Variables :
- `SEASONS` : ex `2526,2425,2324`
- `DIVISION` : `F1`
- `MAX_GOALS` : ex `7`
- `FORM_N` : ex `5`

---

## Structure du projet
```
ligue1-app/
├── Dockerfile
├── compose.yml
├── requirements.txt
├── README.md
├── .env.example
├── src/
│   ├── config.py
│   ├── data/
│   │   ├── fetch.py
│   │   └── cleaning.py
│   ├── features/
│   │   ├── build.py
│   │   └── standings.py
│   ├── models/
│   │   └── poisson.py
│   ├── ui/
│   │   ├── branding.py
│   │   ├── style.py
│   │   └── team_logos.py
│   └── utils/
│       └── log.py
├── app/
│   ├── streamlit_app.py
│   ├── layout.py
│   └── pages/
│       ├── 0_classement.py
│       ├── 1_scores.py
│       ├── 2_home_away.py
│       └── 3_prediction.py
├── scripts/
│   └── download_data.py
├── data/
│   ├── raw/        (gitignored)
│   └── processed/  (gitignored)
└── tests/
    └── test_cleaning.py
```

---

## Notes sur le modèle (Poisson)
- On estime des forces d’attaque/défense séparées **domicile** et **extérieur**.
- On en déduit les buts attendus (λ_home, λ_away).
- Puis on calcule une matrice de probabilité des scores (0..MAX_GOALS) et les proba 1X2.

Ce modèle est volontairement simple, interprétable, et sert de baseline robuste.

---

## Tests
```bash
pytest -q
```

---

## Lint (optionnel)
```bash
ruff check .
```

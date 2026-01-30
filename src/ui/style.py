from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Small theme object to keep UI settings in one place."""

    # Accent inspired by McDonald's golden arches.
    accent: str = "#ffbc0d"

    # Light theme (requested): soft background gradient + dark text.
    bg_top: str = "#f7f9fc"
    bg_bottom: str = "#eef2f7"
    card_bg: str = "rgba(255,255,255,0.86)"
    card_border: str = "rgba(11,27,43,0.12)"
    text: str = "#0b1b2b"
    muted: str = "rgba(11,27,43,0.65)"


def build_css(theme: Theme | None = None) -> str:
    """Return CSS injected into Streamlit for a more professional look."""
    t = theme or Theme()

    # A subtle pattern using CSS gradients (no external images).
    pitch_pattern = (
        "repeating-linear-gradient(90deg, rgba(11,27,43,0.04) 0px, rgba(11,27,43,0.04) 1px, transparent 1px, transparent 140px)",
        "repeating-linear-gradient(0deg, rgba(11,27,43,0.03) 0px, rgba(11,27,43,0.03) 1px, transparent 1px, transparent 110px)",
    )

    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

html, body, [class*="css"]  {{
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
}}

/* App background */
.stApp {{
  background:
    radial-gradient(1100px 520px at 18% 8%, rgba(255,188,13,0.18) 0%, rgba(255,188,13,0.00) 55%),
    radial-gradient(900px 500px at 85% 18%, rgba(0,85,164,0.10) 0%, rgba(0,85,164,0.00) 55%),
    linear-gradient(180deg, {t.bg_top} 0%, {t.bg_bottom} 100%),
    {pitch_pattern[0]},
    {pitch_pattern[1]};
  color: {t.text};
}}

/* Page padding */
.block-container {{
  /* Keep enough top padding so nothing is clipped, even if Streamlit header is visible */
  padding-top: 2.2rem;
  padding-bottom: 2.0rem;
}}

/* Hide Streamlit chrome for a cleaner "product" look */
header,
div[data-testid="stToolbar"],
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
div[data-testid="stDeployButton"],
div[data-testid="stAppDeployButton"],
div[data-testid="stMainMenu"],
div[data-testid="stHeaderActionElements"] {{
  display: none !important;
}}

/* Sidebar */
section[data-testid="stSidebar"] {{
  background: rgba(255,255,255,0.90);
  backdrop-filter: blur(8px);
  border-right: 1px solid {t.card_border};
}}

/* Ensure sidebar navigation is readable */
[data-testid="stSidebarNav"] * {{
  color: {t.text} !important;
}}

/* Brand badge: blue/green background so the white Ligue 1 logo is visible */
.brand-badge {{
  padding: 12px 12px;
  border-radius: 18px;
  border: 1px solid {t.card_border};
  background: linear-gradient(135deg, rgba(0,120,255,0.95) 0%, rgba(0,214,143,0.95) 100%);
  box-shadow: 0 14px 32px rgba(11,27,43,0.12);
}}
.brand-badge img {{
  width: 100%;
  height: auto;
  display: block;
  filter: drop-shadow(0 6px 10px rgba(0,0,0,0.18));
}}

/* Slight shadow for images so white crests remain visible */
img {{
  filter: drop-shadow(0 6px 10px rgba(0,0,0,0.18));
}}

/* Cards */
.card {{
  background: {t.card_bg};
  border: 1px solid {t.card_border};
  border-radius: 16px;
  padding: 16px 16px;
  box-shadow: 0 12px 30px rgba(11,27,43,0.10);
}}

.card-header {{
  display: flex;
  align-items: center;
  gap: 10px;
}}

.card-header h3 {{
  margin: 0;
}}

.card-icon {{
  font-size: 1.2rem;
}}

.card-body {{
  margin-top: 10px;
}}

.badge {{
  display: inline-block;
  padding: 4px 10px;
  border: 1px solid {t.card_border};
  border-radius: 999px;
  background: rgba(11,27,43,0.05);
  color: {t.muted};
  font-size: 0.85rem;
}}

.kpi {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}}

.kpi .kpi-item {{
  background: rgba(255,255,255,0.92);
  border: 1px solid {t.card_border};
  border-radius: 14px;
  padding: 12px;
}}

.kpi .kpi-label {{
  color: {t.muted};
  font-size: 0.85rem;
}}

.kpi .kpi-value {{
  font-size: 1.55rem;
  font-weight: 800;
  line-height: 1.2;
}}

/* Streamlit metrics readability */
div[data-testid="stMetricValue"] {{
  color: {t.text};
  font-weight: 800;
}}
div[data-testid="stMetricLabel"] {{
  color: {t.muted};
}}

/* Accent links */
a {{
  color: {t.accent};
}}

/* Hide default footer/menu (optional) */
footer {{visibility: hidden;}}
#MainMenu {{visibility: hidden;}}

</style>
"""

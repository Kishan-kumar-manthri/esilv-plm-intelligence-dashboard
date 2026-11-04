"""Visual system for the PLM Intelligence dashboard."""

import streamlit as st


def load_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
        :root {
          --navy:#f5f8fc; --panel:#ffffff; --panel2:#f7faff; --line:#dce5ef;
          --text:#16324a; --muted:#6b8194; --cyan:#0877b8; --blue:#1469a8;
          --green:#159b70; --amber:#e89500; --red:#e84c55;
        }
        html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
        .stApp { background:#f5f8fc; color:var(--text); }
        section[data-testid="stSidebar"] { width:235px !important; min-width:235px !important; max-width:235px !important; background:#ffffff; border-right:1px solid var(--line); }
        section[data-testid="stSidebar"] > div { width:235px !important; }
        [data-testid="stSidebar"] { background:#ffffff; border-right:1px solid var(--line); }
        [data-testid="stSidebar"] > div:first-child { padding-top:1.5rem; }
        h1,h2,h3 { font-family:'Space Grotesk', sans-serif !important; letter-spacing:-.03em; }
        h1 { font-size:2.25rem !important; } h2 { font-size:1.35rem !important; }
        .brand { padding: .5rem .3rem 1.6rem; border-bottom:1px solid var(--line); margin-bottom:1rem; }
        .brand-mark { display:inline-flex; width:34px; height:34px; border:2px solid var(--cyan); border-radius:10px; align-items:center; justify-content:center; color:var(--cyan); font-weight:700; margin-right:9px; background:#e9f5fc; }
        .brand-name { font-family:'Space Grotesk'; font-weight:700; font-size:1.05rem; letter-spacing:.08em; }
        .brand-sub { color:var(--muted); font-size:.72rem; margin-top:.45rem; }
        .topbar { display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--line); padding-bottom:1rem; margin-bottom:1.6rem; }
        .github-link { display:inline-block; padding:.45rem .8rem; border:1px solid #b9cddd; border-radius:7px; color:#17628f !important; background:#ffffff; font-size:.78rem; font-weight:600; text-decoration:none !important; }
        .github-link:hover { border-color:#0877b8; color:#0877b8 !important; background:#eef8fd; }
        .github-profile { display:inline-block; margin-left:.45rem; color:#6b8194 !important; font-size:.76rem; text-decoration:none !important; }
        .github-profile:hover { color:#0877b8 !important; }
        .eyebrow { color:var(--cyan); text-transform:uppercase; font-weight:700; letter-spacing:.14em; font-size:.7rem; }
        .status { color:var(--green); font-size:.78rem; }
        .kpi { background:#ffffff; border:1px solid var(--line); border-radius:10px; padding:.85rem .9rem; min-height:105px; box-shadow:0 3px 12px rgba(22,50,74,.07); }
        .kpi-label { color:var(--muted); font-size:.68rem; text-transform:uppercase; letter-spacing:.07em; white-space:nowrap; }
        .kpi-value { font-family:'Space Grotesk'; font-size:1.5rem; font-weight:700; margin-top:.35rem; white-space:nowrap; }
        .kpi-help { color:var(--muted); font-size:.72rem; margin-top:.3rem; }
        .panel { background:#ffffff; border:1px solid var(--line); border-radius:10px; padding:1.05rem; margin: .5rem 0 1rem; box-shadow:0 3px 12px rgba(22,50,74,.06); }
        .panel-title { font-family:'Space Grotesk'; font-size:1rem; font-weight:600; margin-bottom:.2rem; }
        .panel-caption { color:var(--muted); font-size:.78rem; margin-bottom:.8rem; }
        .evidence { color:var(--muted); border-left:2px solid var(--cyan); padding-left:.65rem; font-size:.76rem; }
        .tag { display:inline-block; padding:.25rem .55rem; border-radius:99px; font-size:.7rem; font-weight:600; margin-right:.25rem; background:#e7f2fa; color:#17628f; }
        .tag-green { background:#e2f6ee; color:#087a55; } .tag-amber { background:#fff3d8; color:#9a6400; } .tag-red { background:#fde5e8; color:#b8323d; }
        .visual-note { color:var(--muted); font-size:.7rem; text-align:center; margin-top:.25rem; }
        div[data-testid="stMetric"] { background:transparent; }
        [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:10px; overflow:hidden; }
        button[kind="primary"] { background:var(--cyan); color:#ffffff; border:0; }
        [data-testid="stRadio"] label, [data-testid="stSelectbox"] label { color:var(--text) !important; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label { font-weight:600; font-size:.82rem; padding:.25rem .1rem; }
        [data-testid="stSidebar"] [data-testid="stRadio"] > div { gap:.15rem; }
        [data-testid="stSidebar"] [data-testid="stRadio"] [data-baseweb="radio"] { transform:scale(.82); }
        [data-testid="stSidebar"] .brand-name { font-size:.9rem; }
        [data-testid="stSidebar"] .brand-sub { font-size:.65rem; }
        [data-testid="stDataFrame"] { background:#ffffff; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi(label: str, value: str, help_text: str, tone: str = "normal") -> None:
    color = {"good": "var(--green)", "warn": "var(--amber)", "risk": "var(--red)"}.get(tone, "var(--cyan)")
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value" style="color:{color}">{value}</div>'
        f'<div class="kpi-help">{help_text}</div></div>',
        unsafe_allow_html=True,
    )


def panel_start(title: str, caption: str = "") -> None:
    st.markdown(
        f'<div class="panel"><div class="panel-title">{title}</div>'
        f'<div class="panel-caption">{caption}</div>',
        unsafe_allow_html=True,
    )


def panel_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)

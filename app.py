"""
Visitors - interfaccia Streamlit, personalizzata (bianco + blu elettrico).
Legge i digest Markdown dal repo e li mostra categorizzati, con archivio,
ricerca e i grafici di affluenza (stagionalita) delle attrazioni.
"""
from __future__ import annotations

import datetime as dt
import pathlib
import re

import altair as alt
import pandas as pd
import streamlit as st
import yaml

ROOT = pathlib.Path(__file__).parent
DIGESTS = ROOT / "digests"
CONFIG = ROOT / "config"

BLUE = "#0b4cff"
INK = "#0b1220"
MESI = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
        "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
MESI_FULL = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
             "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]

st.set_page_config(page_title="Visitors", page_icon=":ticket:",
                   layout="centered", initial_sidebar_state="collapsed")

# --- Identita visiva: CSS custom -------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap');

:root { --blue:#0b4cff; --ink:#0b1220; --muted:#5b6472; --line:#e4e8f0; --tint:#f4f7ff; }

html, body, [class*="css"] { font-family:'IBM Plex Sans', system-ui, sans-serif; }
.block-container { padding-top: 1.4rem; padding-bottom: 4rem; max-width: 840px; }

/* nasconde decorazioni default di Streamlit per un look piu pulito */
#MainMenu, footer, header [data-testid="stToolbar"] { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stHeader"] { background: transparent; }

/* Brand header */
.vz-head { display:flex; align-items:center; gap:12px; margin-bottom:2px; }
.vz-mark { width:34px; height:34px; border-radius:10px; background:var(--blue); color:#fff;
           display:grid; place-items:center; font-weight:700; font-size:20px; }
.vz-name { font-weight:700; font-size:26px; letter-spacing:-.03em; color:var(--ink); }
.vz-tag  { margin-left:auto; font-family:'IBM Plex Mono',monospace; font-size:11px;
           text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }
.vz-sub  { color:var(--muted); font-size:14px; margin:0 0 8px; }

/* Tabs come pill */
.stTabs [data-baseweb="tab-list"] { gap:6px; border-bottom:none; }
.stTabs [data-baseweb="tab"] {
  border:1px solid var(--line); border-radius:999px; padding:6px 16px;
  background:#fff; color:var(--muted); font-weight:600; font-size:14px; }
.stTabs [data-baseweb="tab"][aria-selected="true"] {
  background:var(--blue); border-color:var(--blue); color:#fff; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }

/* Meta label */
.vz-meta { font-family:'IBM Plex Mono',monospace; font-size:11px; text-transform:uppercase;
           letter-spacing:.09em; color:var(--blue); margin:14px 0 2px; }

/* Titoli dei digest */
.vz-body h1 { font-size:24px; letter-spacing:-.02em; margin:.2rem 0 .6rem; }
.vz-body h2 { font-size:17px; padding-left:11px; border-left:3px solid var(--blue); margin:1.1rem 0 .4rem; }
.vz-body h3 { font-size:15px; margin:.8rem 0 .3rem; }
.vz-body a  { color:var(--blue); }
.vz-body li::marker { color:var(--blue); }
.vz-body blockquote { border-left:3px solid #c3d1ff; background:var(--tint);
                      border-radius:0 8px 8px 0; padding:8px 14px; color:var(--muted); }

/* Selectbox / input focus blu */
[data-baseweb="select"] > div:focus-within,
.stTextInput input:focus { border-color:var(--blue) !important; box-shadow:0 0 0 2px rgba(11,76,255,.15) !important; }
</style>
""", unsafe_allow_html=True)


# --- Utility ----------------------------------------------------------------

@st.cache_data(ttl=300)
def load_yaml(name: str) -> dict:
    with open(CONFIG / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_md(path: pathlib.Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    front, body = {}, raw
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                front[k.strip()] = v.strip()
        body = m.group(2)
    return {"front": front, "body": body.strip(), "path": path}


@st.cache_data(ttl=120)
def scan(subdir: str) -> list[dict]:
    d = DIGESTS / subdir
    if not d.exists():
        return []
    items = [parse_md(p) for p in d.rglob("*.md")]
    items.sort(key=lambda x: x["path"].stem, reverse=True)
    return items


def show_digest(item: dict) -> None:
    f = item["front"]
    meta = f.get("data") or f.get("settimana") or ""
    if meta:
        st.markdown(f"<div class='vz-meta'>{meta}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='vz-body'>\n\n{item['body']}\n\n</div>", unsafe_allow_html=True)


# --- Grafici (Altair, blu elettrico) ---------------------------------------

def line_chart(df_sel: pd.DataFrame):
    long = df_sel.reset_index().melt("mese", var_name="Attrazione", value_name="Indice")
    order = alt.Sort(MESI)
    blues = ["#0b4cff", "#1aa7ff", "#6b3cff", "#00b3a4", "#ff7a1a", "#e0397a", "#0b8a3e"]
    ch = (alt.Chart(long)
          .mark_line(strokeWidth=2.5, point=False)
          .encode(
              x=alt.X("mese:N", sort=MESI, title=None, axis=alt.Axis(labelColor="#9aa3b2")),
              y=alt.Y("Indice:Q", scale=alt.Scale(domain=[0, 100]), title=None,
                      axis=alt.Axis(labelColor="#9aa3b2", grid=True, gridColor="#eef1f7")),
              color=alt.Color("Attrazione:N",
                              scale=alt.Scale(range=blues),
                              legend=alt.Legend(orient="bottom", title=None)))
          .properties(height=280, width="container"))
    st.altair_chart(ch)


def bar_chart(series: pd.Series):
    df = series.rename_axis("Attrazione").reset_index(name="Indice")
    ch = (alt.Chart(df)
          .mark_bar(cornerRadius=6, color=BLUE)
          .encode(
              x=alt.X("Indice:Q", scale=alt.Scale(domain=[0, 100]), title=None),
              y=alt.Y("Attrazione:N", sort="-x", title=None,
                      axis=alt.Axis(labelColor=INK, labelLimit=220)))
          .properties(height=32 * len(df) + 10, width="container"))
    st.altair_chart(ch)


# --- Header -----------------------------------------------------------------

st.markdown("""
<div class="vz-head">
  <div class="vz-mark">V</div>
  <div class="vz-name">Visitors</div>
  <div class="vz-tag">OTA &amp; attrazioni</div>
</div>
<p class="vz-sub">Il tuo digest quotidiano su OTA e attrazioni turistiche.</p>
""", unsafe_allow_html=True)

tab_home, tab_ota, tab_attr, tab_arch = st.tabs(
    ["Oggi", "OTA", "Attrazioni", "Archivio"])


# --- OGGI -------------------------------------------------------------------

with tab_home:
    daily = scan("general")
    if not daily:
        st.info("Nessun digest ancora. Verranno generati automaticamente ogni giorno.")
    else:
        show_digest(daily[0])
        weekly_gen = scan("general-weekly")
        if weekly_gen:
            st.divider()
            with st.expander("Ultima panoramica settimanale"):
                show_digest(weekly_gen[0])


# --- OTA --------------------------------------------------------------------

with tab_ota:
    otas = load_yaml("otas.yaml")["otas"]
    names = {o["name"]: o["slug"] for o in otas}
    sel = st.selectbox("Seleziona OTA", list(names.keys()))
    items = scan(f"ota/{names[sel]}")
    if not items:
        st.info(f"Ancora nessun approfondimento per {sel}. Sono settimanali, a rotazione.")
    else:
        show_digest(items[0])
        if len(items) > 1:
            with st.expander(f"Storico {sel} ({len(items) - 1})"):
                for it in items[1:]:
                    st.markdown(f"**{it['front'].get('settimana', it['path'].stem)}**")
                    show_digest(it)
                    st.divider()


# --- ATTRAZIONI -------------------------------------------------------------

with tab_attr:
    attr_items = scan("attractions")
    if attr_items:
        show_digest(attr_items[0])
        st.divider()
    else:
        st.info("Ancora nessun approfondimento attrazioni (settimanale).")

    st.markdown("### Affluenza del periodo")
    st.caption("Curve di stima basate sulla stagionalita nota, non dati ufficiali.")

    attrs = load_yaml("attractions.yaml")["attractions"]
    df = pd.DataFrame({a["name"]: a["seasonality"] for a in attrs})
    df.insert(0, "mese", MESI)
    df = df.set_index("mese")

    scelte = st.multiselect("Attrazioni da mostrare",
                            list(df.columns), default=list(df.columns)[:3])
    if scelte:
        line_chart(df[scelte])

    mese_idx = dt.date.today().month - 1
    st.markdown(f"**Indice stimato — {MESI_FULL[mese_idx]}**")
    bar_chart(df.iloc[mese_idx].sort_values(ascending=False))

    with st.expander("Aggiungi i tuoi dati reali (vendite/osservazioni)"):
        st.caption("CSV con colonne: data, valore. Su hosting gratuito i dati "
                   "caricati valgono solo per questa sessione.")
        up = st.file_uploader("CSV dati reali", type="csv")
        if up:
            try:
                mydata = pd.read_csv(up)
                st.dataframe(mydata)
                if {"data", "valore"}.issubset(mydata.columns):
                    mydata["data"] = pd.to_datetime(mydata["data"])
                    st.line_chart(mydata.set_index("data")["valore"], color=BLUE)
            except Exception as e:  # noqa: BLE001
                st.error(f"CSV non valido: {e}")


# --- ARCHIVIO ---------------------------------------------------------------

with tab_arch:
    st.markdown("### Cerca in tutti i digest")
    q = st.text_input("Parola chiave", placeholder="es. commissioni, ranking, Colosseo")
    tutti = scan("general") + scan("general-weekly") + scan("attractions")
    for o in load_yaml("otas.yaml")["otas"]:
        tutti += scan(f"ota/{o['slug']}")

    if q:
        ql = q.lower()
        hits = [it for it in tutti if ql in it["body"].lower()
                or ql in it["front"].get("titolo", "").lower()]
        st.caption(f"{len(hits)} risultati")
        for it in hits[:40]:
            with st.expander(it["front"].get("titolo", it["path"].stem)):
                show_digest(it)
    else:
        st.caption(f"{len(tutti)} digest in archivio. Digita per cercare.")
        for it in tutti[:20]:
            with st.expander(it["front"].get("titolo", it["path"].stem)):
                show_digest(it)

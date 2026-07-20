"""
Visitors - interfaccia (Streamlit), ottimizzata per smartphone.
Legge i digest in Markdown dal repo e li mostra categorizzati, con archivio,
ricerca e i grafici di affluenza (stagionalita) delle attrazioni.
"""
from __future__ import annotations

import datetime as dt
import pathlib
import re

import pandas as pd
import streamlit as st
import yaml

ROOT = pathlib.Path(__file__).parent
DIGESTS = ROOT / "digests"
CONFIG = ROOT / "config"

MESI = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
        "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

st.set_page_config(page_title="Visitors", page_icon="🎫", layout="centered",
                   initial_sidebar_state="collapsed")

# CSS: leggibilita su mobile + look editoriale.
st.markdown("""
<style>
  .block-container {padding-top: 1.2rem; padding-bottom: 3rem; max-width: 820px;}
  h1, h2, h3 {letter-spacing: -0.01em;}
  .vz-brand {font-weight: 800; font-size: 2.1rem; margin-bottom: 0;}
  .vz-brand span {color: #e07a3f;}
  .vz-sub {color: #6b6459; margin-top: -.2rem; font-size: .95rem;}
  .vz-card {background: #f4f1ea; border-radius: 14px; padding: .9rem 1.1rem; margin:.4rem 0;}
  .vz-meta {color:#8a8073; font-size:.8rem;}
  @media (max-width: 640px){ .vz-brand{font-size:1.8rem;} .block-container{padding-left:.8rem;padding-right:.8rem;} }
</style>
""", unsafe_allow_html=True)


# --- Utility ----------------------------------------------------------------

@st.cache_data(ttl=300)
def load_yaml(name: str) -> dict:
    with open(CONFIG / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_md(path: pathlib.Path) -> dict:
    """Estrae frontmatter (--- ... ---) + corpo da un file digest."""
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
    items.sort(key=lambda x: x["path"].stat().st_mtime, reverse=True)
    return items


def show_digest(item: dict) -> None:
    f = item["front"]
    titolo = f.get("titolo") or item["path"].stem
    meta = f.get("data") or f.get("settimana") or ""
    st.markdown(f"<div class='vz-meta'>{meta}</div>", unsafe_allow_html=True)
    st.markdown(item["body"])


# --- Header -----------------------------------------------------------------

st.markdown("<div class='vz-brand'>Visit<span>ors</span></div>", unsafe_allow_html=True)
st.markdown("<div class='vz-sub'>Il tuo digest quotidiano su OTA e attrazioni</div>",
            unsafe_allow_html=True)
st.write("")

tab_home, tab_ota, tab_attr, tab_archivio = st.tabs(
    ["🏠 Oggi", "🛒 OTA", "🏛️ Attrazioni", "🗂️ Archivio"])


# --- HOME: ultimo digest generale + ultimi alert ----------------------------

with tab_home:
    daily = scan("general")
    if not daily:
        st.info("Nessun digest ancora. Verranno generati automaticamente ogni giorno "
                "(vedi README per l'attivazione).")
    else:
        latest = daily[0]
        show_digest(latest)
        st.divider()
        weekly_gen = scan("general-weekly")
        if weekly_gen:
            with st.expander("📊 Ultima panoramica settimanale"):
                show_digest(weekly_gen[0])


# --- OTA: selezione + ultimo approfondimento --------------------------------

with tab_ota:
    otas = load_yaml("otas.yaml")["otas"]
    names = {o["name"]: o["slug"] for o in otas}
    sel = st.selectbox("Scegli l'OTA", list(names.keys()))
    slug = names[sel]
    items = scan(f"ota/{slug}")
    if not items:
        st.info(f"Ancora nessun approfondimento per {sel}. "
                "Gli approfondimenti OTA sono settimanali (a rotazione).")
    else:
        show_digest(items[0])
        if len(items) > 1:
            with st.expander(f"Storico {sel} ({len(items)-1} precedenti)"):
                for it in items[1:]:
                    if st.button(it["front"].get("settimana", it["path"].stem),
                                 key=f"ota_{slug}_{it['path'].stem}"):
                        show_digest(it)


# --- ATTRAZIONI: digest + grafici affluenza ---------------------------------

with tab_attr:
    attr_items = scan("attractions")
    if attr_items:
        show_digest(attr_items[0])
    else:
        st.info("Ancora nessun approfondimento attrazioni (settimanale).")

    st.divider()
    st.subheader("Affluenza del periodo")
    st.caption("⚠️ Curve di STIMA basate sulla stagionalita nota, non dati ufficiali. "
               "Puoi caricare i tuoi dati reali qui sotto per confrontarli.")

    attrs = load_yaml("attractions.yaml")["attractions"]
    df = pd.DataFrame({a["name"]: a["seasonality"] for a in attrs}, index=MESI)

    scelte = st.multiselect("Attrazioni da mostrare",
                            list(df.columns), default=list(df.columns)[:3])
    if scelte:
        st.line_chart(df[scelte], height=280)

    mese_idx = dt.date.today().month - 1
    st.markdown(f"**Indice stimato per {MESI[mese_idx]} (mese corrente)**")
    oggi = df.iloc[mese_idx].sort_values(ascending=False)
    st.bar_chart(oggi, height=240)

    with st.expander("➕ Aggiungi i tuoi dati reali (vendite/osservazioni)"):
        st.caption("Carica un CSV con colonne: data, attrazione, valore. "
                   "Nota: su hosting gratuito i dati caricati valgono solo per questa sessione.")
        up = st.file_uploader("CSV dati reali", type="csv")
        if up:
            try:
                mydata = pd.read_csv(up)
                st.dataframe(mydata, use_container_width=True)
                if {"data", "valore"}.issubset(mydata.columns):
                    mydata["data"] = pd.to_datetime(mydata["data"])
                    st.line_chart(mydata.set_index("data")["valore"], height=240)
            except Exception as e:  # noqa: BLE001
                st.error(f"CSV non valido: {e}")


# --- ARCHIVIO: ricerca su tutti i digest ------------------------------------

with tab_archivio:
    st.subheader("Cerca in tutti i digest")
    q = st.text_input("Parola chiave", placeholder="es. commissioni, ranking, Colosseo")
    tutti = (scan("general") + scan("general-weekly")
             + scan("attractions"))
    for o in load_yaml("otas.yaml")["otas"]:
        tutti += scan(f"ota/{o['slug']}")

    if q:
        ql = q.lower()
        hits = [it for it in tutti if ql in it["body"].lower()
                or ql in it["front"].get("titolo", "").lower()]
        st.caption(f"{len(hits)} risultati")
        for it in hits[:40]:
            with st.expander(f"{it['front'].get('titolo', it['path'].stem)}"):
                show_digest(it)
    else:
        st.caption(f"{len(tutti)} digest in archivio. Digita per cercare.")
        for it in tutti[:20]:
            with st.expander(f"{it['front'].get('titolo', it['path'].stem)}"):
                show_digest(it)

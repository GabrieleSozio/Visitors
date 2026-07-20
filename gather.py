"""
Visitors - Raccolta dati via Claude (con Web Search).

Genera i digest e li salva come file Markdown nel repo.
La chiave API si legge dalla variabile d'ambiente ANTHROPIC_API_KEY
(su GitHub Actions e' un "secret", MAI scritta nel codice).

Uso:
    python gather.py --mode daily
    python gather.py --mode weekly-ota          # OTA a rotazione automatica
    python gather.py --mode weekly-ota --target getyourguide
    python gather.py --mode weekly-general
    python gather.py --mode weekly-attractions
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import sys

import yaml
from anthropic import Anthropic

# --- Configurazione ---------------------------------------------------------

MODEL = "claude-sonnet-5"  # scelta dell'utente: rapporto qualita/prezzo migliore
ROOT = pathlib.Path(__file__).parent
CONFIG = ROOT / "config"
DIGESTS = ROOT / "digests"

# Freni di costo: numero massimo di ricerche web per esecuzione.
MAX_SEARCHES = {
    "daily": 6,             # giornaliero leggero = solo novita/alert
    "weekly-general": 12,
    "weekly-ota": 14,
    "weekly-attractions": 12,
}

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def load_yaml(name: str) -> dict:
    with open(CONFIG / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def sources_block() -> str:
    data = load_yaml("sources.yaml")
    lines = ["FONTI DI SETTORE (privilegia quelle ad alta priorita):"]
    for s in data.get("sources", []):
        lines.append(f"- {s['name']} ({s['url']}) [{s.get('priority','?')}] - {s.get('focus','')}")
    lines.append("\nCANALI UFFICIALI OTA:")
    for s in data.get("ota_official", []):
        lines.append(f"- {s['name']} ({s['url']})")
    return "\n".join(lines)


def web_search_tool(max_uses: int) -> dict:
    return {
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": max_uses,
        "user_location": {"type": "approximate", "country": "IT", "timezone": "Europe/Rome"},
    }


def call_claude(system: str, user: str, max_uses: int, max_tokens: int = 16000) -> str:
    """Chiama Claude con il tool Web Search, gestendo il loop server-side (pause_turn)."""
    client = Anthropic()  # legge ANTHROPIC_API_KEY dall'ambiente
    tools = [web_search_tool(max_uses)]
    messages = [{"role": "user", "content": user}]

    while True:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            output_config={"effort": "medium"},  # equilibrio qualita/costo
            messages=messages,
        )
        if resp.stop_reason == "pause_turn":
            # Il tool server-side ha raggiunto il limite di iterazioni: si riprende.
            messages.append({"role": "assistant", "content": resp.content})
            continue
        if resp.stop_reason == "refusal":
            return "> Il modello ha rifiutato di rispondere per motivi di sicurezza."
        break

    text = "".join(b.text for b in resp.content if b.type == "text")
    return text.strip()


def save(path: pathlib.Path, front: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = "\n".join(f"{k}: {v}" for k, v in front.items())
    path.write_text(f"---\n{fm}\n---\n\n{body}\n", encoding="utf-8")
    print(f"[ok] scritto {path.relative_to(ROOT)}")


BASE_SYSTEM = f"""Sei un analista senior specializzato in distribuzione turistica e OTA,
al servizio di un product manager di un'agenzia di tour ed esperienze a Roma
(vende tour guidati e biglietti per attrazioni in tutta Italia).

Regole:
- Scrivi SEMPRE in italiano, chiaro e sintetico, in Markdown.
- Riporta solo novita REALI e verificabili tramite ricerca web; cita la fonte con link.
- NON inventare. Se in un certo periodo non ci sono novita rilevanti, dillo esplicitamente.
- Ordina per rilevanza pratica per un product manager (ranking, commissioni, policy,
  contenuti, algoritmi, connettivita, domanda di mercato).
- Ogni punto: cosa e' cambiato -> perche' conta per noi -> azione consigliata (se c'e').

{sources_block()}
"""


# --- Modalita ---------------------------------------------------------------

def run_daily() -> None:
    today = dt.date.today()
    user = f"""Fai una scansione GIORNALIERA LEGGERA delle novita del settore
in-destination / OTA nelle ultime 24-48 ore ({today.isoformat()}).

Obiettivo: solo ALERT e NOVITA da segnalare, niente approfondimenti lunghi.
Formato:
# Digest Generale - {today.strftime('%d/%m/%Y')}
## Alert del giorno
(3-8 bullet brevi. Ognuno: titolo in grassetto, 1-2 frasi, [fonte](url).)
Se non ci sono novita significative, scrivilo in una riga.
## Da tenere d'occhio
(eventuali temi che potrebbero evolvere nei prossimi giorni)
"""
    body = call_claude(BASE_SYSTEM, user, MAX_SEARCHES["daily"], max_tokens=8000)
    save(DIGESTS / "general" / f"{today.isoformat()}.md",
         {"tipo": "generale-giornaliero", "data": today.isoformat(),
          "titolo": f"Alert del {today.strftime('%d/%m/%Y')}"}, body)


def run_weekly_general() -> None:
    today = dt.date.today()
    y, w, _ = today.isocalendar()
    user = f"""Fai un APPROFONDIMENTO SETTIMANALE del settore in-destination / OTA
(settimana {w} del {y}). Analisi ragionata dei trend piu importanti della settimana:
distribuzione, tecnologia, movimenti di mercato, cambi strategici delle OTA.

Formato:
# Panoramica settimanale - Settimana {w}/{y}
## Temi principali (3-5, con analisi)
## Movimenti delle OTA
## Cosa significa per la nostra agenzia
(2-4 raccomandazioni concrete)
"""
    body = call_claude(BASE_SYSTEM, user, MAX_SEARCHES["weekly-general"])
    save(DIGESTS / "general-weekly" / f"{y}-W{w:02d}.md",
         {"tipo": "generale-settimanale", "settimana": f"{y}-W{w:02d}",
          "titolo": f"Panoramica settimana {w}/{y}"}, body)


def pick_ota(target: str | None) -> dict:
    otas = load_yaml("otas.yaml")["otas"]
    if target:
        for o in otas:
            if o["slug"] == target:
                return o
        sys.exit(f"OTA '{target}' non trovata in config/otas.yaml")
    # Rotazione automatica in base al numero di settimana ISO.
    w = dt.date.today().isocalendar()[1]
    return otas[w % len(otas)]


def run_weekly_ota(target: str | None) -> None:
    ota = pick_ota(target)
    today = dt.date.today()
    y, w, _ = today.isocalendar()
    user = f"""Fai un APPROFONDIMENTO SETTIMANALE dedicato a {ota['name']}
(settimana {w}/{y}). Aree da coprire: {ota.get('notes','')}.

Cerca le novita di prodotto, policy, commissioni, algoritmo di ranking,
requisiti per i partner/supplier e best practice recenti.

Formato:
# {ota['name']} - Approfondimento settimana {w}/{y}
## Novita di prodotto / policy
## Ranking & visibilita (come farsi trovare meglio)
## Commissioni & condizioni economiche
## Best practice operative per il product manager
## Azioni consigliate questa settimana
Se un'area non ha novita, indicalo brevemente ma dai comunque il contesto utile.
"""
    body = call_claude(BASE_SYSTEM, user, MAX_SEARCHES["weekly-ota"])
    save(DIGESTS / "ota" / ota["slug"] / f"{y}-W{w:02d}.md",
         {"tipo": "ota-settimanale", "ota": ota["name"], "slug": ota["slug"],
          "settimana": f"{y}-W{w:02d}", "titolo": f"{ota['name']} - sett. {w}/{y}"}, body)


def run_weekly_attractions() -> None:
    today = dt.date.today()
    y, w, _ = today.isocalendar()
    mese = MESI[today.month - 1]
    attrs = load_yaml("attractions.yaml")["attractions"]
    elenco = ", ".join(a["name"] for a in attrs)
    user = f"""Fai un APPROFONDIMENTO SETTIMANALE sulle ATTRAZIONI italiane che seguiamo
(settimana {w}/{y}, periodo: {mese}). Attrazioni: {elenco}.

Cerca cambiamenti REALI: nuove regole d'ingresso, aumenti prezzi, chiusure/aperture,
scioperi, cambi di biglietteria/rivenditori ufficiali, novita per i partner
(tour operator/rivenditori autorizzati), tetti di capienza, prenotazioni obbligatorie.

Formato:
# Attrazioni Italia - Settimana {w}/{y}
## Cambiamenti generali (per attrazione)
## Novita per i partner / rivenditori autorizzati
## Note sull'affluenza del periodo ({mese})
(commento qualitativo su code, sold-out, afflussi record trovati nelle fonti.
I grafici quantitativi nell'app sono STIME di stagionalita, non dati ufficiali.)
Se un'attrazione non ha novita, indicalo.
"""
    body = call_claude(BASE_SYSTEM, user, MAX_SEARCHES["weekly-attractions"])
    save(DIGESTS / "attractions" / f"{y}-W{w:02d}.md",
         {"tipo": "attrazioni-settimanale", "settimana": f"{y}-W{w:02d}",
          "titolo": f"Attrazioni Italia - sett. {w}/{y}"}, body)


def main() -> None:
    p = argparse.ArgumentParser(description="Visitors - raccolta dati via Claude")
    p.add_argument("--mode", required=True,
                   choices=["daily", "weekly-general", "weekly-ota", "weekly-attractions"])
    p.add_argument("--target", default=None, help="slug OTA specifica (solo weekly-ota)")
    args = p.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ERRORE: variabile ANTHROPIC_API_KEY non impostata.")

    if args.mode == "daily":
        run_daily()
    elif args.mode == "weekly-general":
        run_weekly_general()
    elif args.mode == "weekly-ota":
        run_weekly_ota(args.target)
    elif args.mode == "weekly-attractions":
        run_weekly_attractions()


if __name__ == "__main__":
    main()

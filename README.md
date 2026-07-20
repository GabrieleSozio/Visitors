# Visitors

Web app personale per il product management su OTA e attrazioni turistiche.
Raccoglie automaticamente le novità dalle fonti più affidabili del settore
(Arival, Skift, PhocusWire, canali ufficiali OTA…) e le organizza in digest
consultabili — generali giornalieri e approfondimenti settimanali per OTA e attrazioni.

Interfaccia **custom** (HTML/CSS/JS, bianco + blu elettrico), niente framework
esterni, veloce e mobile-first.

## Come funziona (architettura)

- **GitHub Actions** (scheduler gratuito) esegue `gather.py` a orari fissi.
- **`gather.py`** chiama **Claude Sonnet** con il tool **Web Search** e salva i
  digest in Markdown nella cartella `digests/` (versionati in git).
- **`build_index.py`** impacchetta digest + config in `data/index.json`
  (Markdown già convertito in HTML). È l'unico file letto dal sito.
- **`index.html` + `assets/`** è il sito statico che legge `data/index.json`.

Nessun costo tranne l'uso dell'API Claude (stima: ~15-30 €/mese con questa cadenza).

## Cadenza

- **Giornaliero (leggero):** solo alert/novità delle ultime 24-48h.
- **Settimanale (pesante):** panoramica generale + 1 OTA a rotazione + attrazioni.

---

## Struttura

```
index.html            sito (single page)
assets/style.css      grafica (bianco + blu elettrico)
assets/app.js         logica: tab, selettori, grafici SVG, ricerca
gather.py             raccolta dati via Claude + Web Search
build_index.py        genera data/index.json dai digest
data/index.json       dati letti dal sito (generato)
digests/              digest in Markdown
config/               fonti, OTA, attrazioni
.github/workflows/    automazioni giornaliera e settimanale
```

---

## Setup

### 1. Chiave API Anthropic
Account su **console.anthropic.com**, aggiungi credito, genera una API key.
Consiglio: imposta uno **spend limit mensile** (es. 40 €) come rete di sicurezza.
La chiave non va MAI nel codice.

### 2. Secret su GitHub
Repository → **Settings → Secrets and variables → Actions → New repository secret**
- Nome: `ANTHROPIC_API_KEY`
- Valore: la tua chiave

Poi tab **Actions** → "Digest giornaliero" → **Run workflow** per un primo test.

### 3. Pubblica il sito su Cloudflare Pages (gratis, anche con repo privato)
1. Crea un account su **dash.cloudflare.com** → sezione **Workers & Pages**.
2. **Create → Pages → Connect to Git** → autorizza GitHub → scegli `Visitors`.
3. Impostazioni build:
   - **Framework preset:** `None`
   - **Build command:** *(lascia vuoto)*
   - **Build output directory:** `/`
4. **Save and Deploy.** Otterrai un URL tipo `https://visitors.pages.dev`.

Ad ogni push (anche i commit automatici dei workflow) Cloudflare **ricostruisce
da solo** il sito, quindi i nuovi digest compaiono senza interventi.

> Alternativa GitHub Pages: funziona ma su repo **privati** richiede un piano a
> pagamento. Con Cloudflare Pages il repo resta privato e gratis.

### 4. Usala dallo smartphone
Apri l'URL → menu del browser → **Aggiungi a schermata Home**.

---

## Uso locale (test)

```bash
pip install -r requirements.txt

# genera un digest (serve la chiave in ambiente)
#   PowerShell:  $env:ANTHROPIC_API_KEY="sk-ant-..."
#   bash:        export ANTHROPIC_API_KEY=sk-ant-...
python gather.py --mode daily

# rigenera l'indice e avvia il sito in locale
python build_index.py
python -m http.server 8600
# apri http://127.0.0.1:8600
```

Altri comandi di raccolta:
```bash
python gather.py --mode weekly-general
python gather.py --mode weekly-ota                  # OTA a rotazione automatica
python gather.py --mode weekly-ota --target viator  # OTA specifica
python gather.py --mode weekly-attractions
```

---

## Personalizzazione

- **Fonti:** `config/sources.yaml`
- **OTA e rotazione:** `config/otas.yaml`
- **Attrazioni e stagionalità:** `config/attractions.yaml`
- **Colori/grafica:** `assets/style.css` (variabili `--blue`, `--ink`… in cima)
- **Orari automazioni:** `.github/workflows/*.yml` (campo `cron`, in UTC)
- **Freni di costo:** `MAX_SEARCHES` in `gather.py`

## Nota onesta sui grafici di affluenza
I numeri esatti di visitatori delle attrazioni non sono dati pubblici. I grafici
mostrano **stime di stagionalità** (pattern alta/bassa stagione), etichettate come
tali. I valori sono in `config/attractions.yaml` e puoi correggerli con i tuoi dati.

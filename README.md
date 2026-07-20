# Visitors

App personale per il product management su OTA e attrazioni turistiche.
Raccoglie automaticamente le novità dalle fonti più affidabili del settore
(Arival, Skift, PhocusWire, canali ufficiali OTA…) e le organizza in digest
consultabili — generali giornalieri e approfondimenti settimanali per OTA e attrazioni.

Interfaccia **Streamlit personalizzata** (bianco + blu elettrico, mobile-first).

## Come funziona (architettura)

- **GitHub Actions** (scheduler gratuito) esegue `gather.py` a orari fissi.
- **`gather.py`** chiama **Claude Sonnet** con il tool **Web Search** e salva i
  digest in Markdown nella cartella `digests/` (versionati in git).
- **`app.py`** (Streamlit) legge i digest e li mostra, con tema custom.

Nessun costo tranne l'uso dell'API Claude (stima: ~15-30 €/mese con questa cadenza).

## Cadenza

- **Giornaliero (leggero):** solo alert/novità delle ultime 24-48h.
- **Settimanale (pesante):** panoramica generale + 1 OTA a rotazione + attrazioni.

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

### 3. Pubblica l'app su Streamlit Community Cloud (gratis)
Il repo è pubblico, quindi il deploy è immediato:
1. Vai su **share.streamlit.io** → **Sign in with GitHub** → autorizza.
2. **Create app** → **Deploy a public app from GitHub**.
3. Impostazioni:
   - **Repository:** `GabrieleSozio/Visitors`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. **Deploy.** Ottieni un URL tipo `https://visitors.streamlit.app`.

L'app non usa la chiave API (legge solo i digest già nel repo), quindi non serve
inserire secret su Streamlit. Quando i workflow generano nuovi digest, l'app li
rilegge automaticamente (o usa "Reboot app" dal menu per forzare).

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

# avvia l'interfaccia
python -m streamlit run app.py
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
- **Colori/tema:** `.streamlit/config.toml` + blocco CSS in cima ad `app.py`
- **Orari automazioni:** `.github/workflows/*.yml` (campo `cron`, in UTC)
- **Freni di costo:** `MAX_SEARCHES` in `gather.py`

## Nota onesta sui grafici di affluenza
I numeri esatti di visitatori delle attrazioni non sono dati pubblici. I grafici
mostrano **stime di stagionalità** (pattern alta/bassa stagione), etichettate come
tali. I valori sono in `config/attractions.yaml` e puoi correggerli con i tuoi dati.

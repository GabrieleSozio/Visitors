# Visitors 🎫

App personale per il product management su OTA e attrazioni turistiche.
Raccoglie automaticamente le novità dalle fonti più affidabili del settore
(Arival, Skift, PhocusWire, canali ufficiali OTA…) e le organizza in digest
consultabili — generali giornalieri e approfondimenti settimanali per OTA e attrazioni.

## Come funziona (architettura)

- **GitHub Actions** (scheduler gratuito) esegue `gather.py` a orari fissi.
- **`gather.py`** chiama **Claude Sonnet** con il tool **Web Search** e genera i
  digest in Markdown, salvandoli nella cartella `digests/` (versionati in git).
- **Streamlit** (`app.py`) legge i digest e li mostra, ottimizzato per smartphone.

Nessun costo tranne l'uso dell'API Claude (stima: ~€15-30/mese con questa cadenza).

## Cadenza

- **Giornaliero (leggero):** solo alert/novità delle ultime 24-48h.
- **Settimanale (pesante):** panoramica generale + 1 OTA a rotazione + attrazioni.

---

## Setup passo-passo

### 1. Chiave API Anthropic
Crea un account su **console.anthropic.com**, aggiungi credito e genera una API key.
Consiglio: imposta anche uno **spend limit mensile** (es. €40) come rete di sicurezza.
⚠️ Non scrivere MAI la chiave nel codice.

### 2. Carica il progetto su GitHub
```bash
git init
git add .
git commit -m "Visitors - primo commit"
git branch -M main
git remote add origin https://github.com/<tuo-utente>/visitors.git
git push -u origin main
```

### 3. Configura il secret su GitHub
Repository → **Settings → Secrets and variables → Actions → New repository secret**
- Nome: `ANTHROPIC_API_KEY`
- Valore: la tua chiave

Poi vai nel tab **Actions**, apri "Digest giornaliero" e premi **Run workflow**
per un primo test manuale.

### 4. Pubblica l'app su Streamlit
Vai su **share.streamlit.io**, collega il repo GitHub, file principale `app.py`.
In **Advanced settings → Secrets** (facoltativo per l'app, che legge solo file)
non serve la chiave: l'app non chiama l'API, mostra solo i digest già generati.

### 5. Usarla dallo smartphone
Apri l'URL Streamlit sul telefono → menu del browser → **"Aggiungi a schermata Home"**.
Si aprirà come un'app.

---

## Uso locale (test)

```bash
pip install -r requirements.txt

# genera un digest (serve la chiave in ambiente)
export ANTHROPIC_API_KEY=sk-ant-...        # Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
python gather.py --mode daily

# avvia l'interfaccia
streamlit run app.py
```

Altri comandi:
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
- **Orari automazioni:** `.github/workflows/*.yml` (campo `cron`, in UTC)
- **Freni di costo:** `MAX_SEARCHES` in `gather.py`

## Nota onesta sui grafici di affluenza
I numeri esatti di visitatori delle attrazioni non sono dati pubblici. I grafici
mostrano **stime di stagionalità** (pattern alta/bassa stagione) e sono etichettati
come tali. Puoi caricare i tuoi dati reali di vendita nella scheda "Attrazioni"
per confrontarli.

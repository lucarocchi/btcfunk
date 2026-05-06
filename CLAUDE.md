# btcfunk — Claude Code Context

## Cos'è questo progetto

**btcfunk** è il sito web `btcfunk.com` — una piattaforma di **Bitcoin on-chain analytics**.

Mostra metriche Bitcoin (MVRV, on-chain data, AI analysis) e ospita la demo del widget FunkPay (`/#support`). Serve anche il file `funkpay.js` dal server `btcfunkpay`.

---

## Ecosistema FunkPay — 3 progetti

| Repo | Ruolo | Path locale |
|------|-------|-------------|
| `btcfunk` (questo) | Website btcfunk.com — analytics + demo FunkPay | `../btcfunk` |
| `btcfunkpay` | Merchant payment server (Python/FastAPI) | `../btcfunkpay` |
| `funkpayai` | Agent wallet + MCP server (Electron) | `../funkpayai` |

---

## Stack tecnico

- **Python 3.11+** + FastAPI
- **SQLite** — `btcfunk.sqlite` (metriche), `mvrv_cache.sqlite` (MVRV)
- **BigQuery** — fonte dati on-chain (via `test_bigquery.py`, scripts)
- **Jinja2** templates + static files
- **Cron** (`crontab.txt`) — aggiornamento dati giornaliero

## Struttura

```
btcfunk/
  app/
    main.py          — FastAPI app: endpoints metriche + analytics
    metrics_meta.py  — definizioni metriche (label, query, meta)
    static/          — CSS, JS, immagini
    templates/       — Jinja2 HTML templates
  scripts/
    daily_update.py         — aggiornamento dati giornaliero
    ai_analysis.py          — genera analisi AI (salva analysis.json)
    update_coinbase_premium.py
    update_csv.py
    import_exchange_addresses.py
    migrate_history.py
  btcfunk.sqlite     — DB principale metriche
  mvrv_cache.sqlite  — cache MVRV
  crontab.txt        — schedule cron jobs
  requirements.txt
```

## Comandi

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Relazione con btcfunkpay

Il sito `btcfunk.com` serve la demo di FunkPay all'endpoint `/#support`.
Il widget `funkpay.js` è hostato su `btcfunk.com/pay/funkpay.js` e viene servito da un'istanza di `btcfunkpay` in esecuzione sullo stesso server.

**Nginx config (produzione):**
```nginx
location /pay/ {
    proxy_pass http://127.0.0.1:8001/;  # btcfunkpay server
}
```

## Stato corrente (2026-05-06)

- ✅ Sito analytics funzionante su btcfunk.com
- ✅ Demo FunkPay live su btcfunk.com/#support
- ✅ `funkpay.js` servito tramite proxy → btcfunkpay
- 🔲 Pagina dedicata FunkPay/funkpayai per presentare l'ecosistema

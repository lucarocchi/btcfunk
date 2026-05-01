#!/usr/bin/env python3
"""
Aggiornamento giornaliero BigQuery → SQLite (solo ieri).
Da eseguire via cron ogni giorno alle 06:00 UTC (dopo che i blocchi del giorno precedente sono finalizzati).

Cron example:
    0 6 * * * cd /var/www/btcfunk && python3 scripts/daily_update.py >> logs/daily_update.log 2>&1

Requires: gcloud auth application-default login (o GOOGLE_APPLICATION_CREDENTIALS)
"""
import sys, os, sqlite3
from collections import defaultdict
from datetime import date as Date, datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, "../btcfunk.sqlite")

UTXO_REFRESH_DAYS = 7  # Riesegue UTXO snapshot (costoso) ogni 7 giorni

_bq = None
def bq():
    global _bq
    if _bq is None:
        from google.cloud import bigquery
        _bq = bigquery.Client()
    return _bq

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def run_query(sql, label):
    log(f"{label}: query BQ...")
    rows = list(bq().query(sql).result())
    log(f"{label}: {len(rows)} righe")
    return rows

def _bits_to_difficulty(bits_hex):
    exp      = int(bits_hex[:2], 16)
    mantissa = int(bits_hex[2:8], 16)
    target   = mantissa * (2 ** (8 * (exp - 3)))
    return (0xffff * (2 ** 208)) / target

def _get_prices(con):
    return {r[0]: r[1] for r in con.execute("SELECT day, price FROM btc_prices").fetchall()}

def yesterday():
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")


# ── Update outputs → nvt_daily + active_addr_daily ───────────────────────────

def update_outputs(con, since):
    sql = f"""
        SELECT
            DATE(block_timestamp)   AS day,
            SUM(value) / 1e8       AS btc_volume,
            COUNT(DISTINCT addr)   AS addr_count
        FROM `bigquery-public-data.crypto_bitcoin.outputs`,
        UNNEST(addresses) AS addr
        WHERE DATE(block_timestamp) >= '{since}'
          AND value > 0
        GROUP BY day ORDER BY day
    """
    rows = run_query(sql, "outputs (NVT + ActiveAddr)")
    con.executemany("INSERT OR REPLACE INTO nvt_daily (day, btc_volume) VALUES (?,?)",
                    [(str(r.day), float(r.btc_volume)) for r in rows])
    con.executemany("INSERT OR REPLACE INTO active_addr_daily (day, count) VALUES (?,?)",
                    [(str(r.day), int(r.addr_count)) for r in rows])
    con.commit()


# ── Update transactions → puell_daily + tx_stats_daily + whale_tx_daily ──────

def update_transactions(con, since):
    sql = f"""
        SELECT
            DATE(block_timestamp) AS day,
            COUNT(CASE WHEN NOT is_coinbase THEN 1 END)                                              AS tx_count,
            SUM(CASE WHEN NOT is_coinbase THEN output_value ELSE 0 END) / 1e8                        AS volume_btc,
            SUM(CASE WHEN NOT is_coinbase THEN fee ELSE 0 END) / 1e8                                 AS fees_btc,
            SUM(CASE WHEN is_coinbase THEN output_value ELSE 0 END) / 1e8                            AS coinbase_revenue,
            COUNT(CASE WHEN NOT is_coinbase AND output_value >= 10000000000 THEN 1 END)               AS whale_count,
            SUM(CASE WHEN NOT is_coinbase AND output_value >= 10000000000 THEN output_value ELSE 0 END) / 1e8 AS whale_volume
        FROM `bigquery-public-data.crypto_bitcoin.transactions`
        WHERE DATE(block_timestamp) >= '{since}'
        GROUP BY day ORDER BY day
    """
    rows = run_query(sql, "transactions (Puell + TxStats + Whale)")
    con.executemany("INSERT OR REPLACE INTO puell_daily (day, revenue) VALUES (?,?)",
                    [(str(r.day), float(r.coinbase_revenue)) for r in rows])
    con.executemany("INSERT OR REPLACE INTO tx_stats_daily (day, tx_count, volume, fees) VALUES (?,?,?,?)",
                    [(str(r.day), int(r.tx_count), float(r.volume_btc), float(r.fees_btc)) for r in rows])
    con.executemany("INSERT OR REPLACE INTO whale_tx_daily (day, count, btc_volume) VALUES (?,?,?)",
                    [(str(r.day), int(r.whale_count), float(r.whale_volume)) for r in rows])
    con.commit()


# ── Update blocks → hashrate_daily ───────────────────────────────────────────

def update_hashrate(con, since):
    sql = f"""
        SELECT
            DATE(timestamp) AS day,
            ANY_VALUE(bits) AS bits,
            COUNT(*)        AS block_count
        FROM `bigquery-public-data.crypto_bitcoin.blocks`
        WHERE DATE(timestamp) >= '{since}'
        GROUP BY day ORDER BY day
    """
    rows = run_query(sql, "blocks (Hashrate)")
    out = []
    for r in rows:
        try:
            diff = _bits_to_difficulty(r.bits)
        except Exception:
            continue
        eh = round(diff * (2 ** 32) / 600 / 1e18, 4)
        out.append((str(r.day), diff, eh, int(r.block_count)))
    con.executemany(
        "INSERT OR REPLACE INTO hashrate_daily (day, difficulty, hashrate_eh, block_count) VALUES (?,?,?,?)", out
    )
    con.commit()


# ── Update flows → sopr_daily + cdd_daily ────────────────────────────────────

def update_flows(con, since, prices):
    sql = f"""
        SELECT
            DATE(i.block_timestamp) AS spend_day,
            DATE(o.block_timestamp) AS creation_day,
            SUM(o.value) / 1e8      AS btc_amount
        FROM `bigquery-public-data.crypto_bitcoin.inputs` i
        JOIN `bigquery-public-data.crypto_bitcoin.outputs` o
            ON i.spent_transaction_hash = o.transaction_hash
            AND i.spent_output_index = o.index
        WHERE o.value > 0
          AND DATE(i.block_timestamp) >= '{since}'
        GROUP BY spend_day, creation_day
        ORDER BY spend_day
    """
    rows = run_query(sql, "flows (SOPR + CDD)")
    if not rows:
        return

    realized   = defaultdict(float)
    cost_basis = defaultdict(float)
    cdd_agg    = defaultdict(float)

    for r in rows:
        spend_day    = str(r.spend_day)
        creation_day = str(r.creation_day)
        btc          = float(r.btc_amount)

        p_spend    = prices.get(spend_day)
        p_creation = prices.get(creation_day)
        if p_spend and p_creation:
            realized[spend_day]   += btc * p_spend
            cost_basis[spend_day] += btc * p_creation

        try:
            age = (Date.fromisoformat(spend_day) - Date.fromisoformat(creation_day)).days
        except ValueError:
            continue
        if age >= 0:
            cdd_agg[spend_day] += btc * age

    sopr_rows = [
        (day, round(realized[day] / cost_basis[day], 6))
        for day in sorted(realized) if cost_basis[day] > 0
    ]
    cdd_rows = [(day, round(val, 2)) for day, val in sorted(cdd_agg.items())]
    con.executemany("INSERT OR REPLACE INTO sopr_daily (day, sopr) VALUES (?,?)", sopr_rows)
    con.executemany("INSERT OR REPLACE INTO cdd_daily (day, cdd) VALUES (?,?)", cdd_rows)
    con.commit()


# ── UTXO snapshot (settimanale) ───────────────────────────────────────────────

def _needs_utxo_refresh(con):
    row = con.execute(
        "SELECT updated_at FROM cache WHERE key='utxo_snapshot_updated'"
    ).fetchone()
    if not row:
        return True
    updated = datetime.fromisoformat(row[0])
    age_days = (datetime.now(timezone.utc) - updated).total_seconds() / 86400
    return age_days >= UTXO_REFRESH_DAYS

def update_utxo_snapshot(con):
    if not _needs_utxo_refresh(con):
        log("UTXO snapshot: aggiornato di recente, skip")
        return
    sql = """
        SELECT
            DATE(o.block_timestamp) AS creation_day,
            SUM(o.value) / 1e8      AS btc_value
        FROM `bigquery-public-data.crypto_bitcoin.outputs` o
        LEFT JOIN `bigquery-public-data.crypto_bitcoin.inputs` i
            ON o.transaction_hash = i.spent_transaction_hash
            AND o.index = i.spent_output_index
        WHERE i.transaction_hash IS NULL
          AND o.value > 0
        GROUP BY creation_day
        ORDER BY creation_day
    """
    rows = run_query(sql, "UTXO snapshot (MVRV + HODL)")
    out = [(str(r.creation_day), float(r.btc_value)) for r in rows]
    con.executemany("INSERT OR REPLACE INTO utxo_snapshot (creation_day, btc_value) VALUES (?,?)", out)
    con.execute(
        "INSERT OR REPLACE INTO cache (key, value, updated_at) VALUES ('utxo_snapshot_updated','true',?)",
        (datetime.now(timezone.utc).isoformat(),)
    )
    # Invalida cache metriche che dipendono da UTXO
    for key in ("mvrv", "hodl", "lth_sth", "rhodl", "mvrv_zscore", "nupl", "stf"):
        con.execute("DELETE FROM cache WHERE key=?", (key,))
    con.commit()
    log(f"  utxo_snapshot: {len(out)} righe aggiornate")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    since = yesterday()
    log(f"DB: {DB_PATH}")
    log(f"Aggiornamento dati dal {since}")

    con = sqlite3.connect(DB_PATH)

    prices = _get_prices(con)
    if not prices:
        log("WARN: btc_prices vuota — SOPR/CDD non calcolabili. Esegui prima migrate_history.py")

    update_outputs(con, since)
    update_transactions(con, since)
    update_hashrate(con, since)

    if prices:
        update_flows(con, since, prices)
    else:
        log("SOPR/CDD: skip (btc_prices mancante)")

    update_utxo_snapshot(con)

    # Invalida tutte le cache metriche per forzare ricalcolo al prossimo accesso
    con.execute("DELETE FROM cache WHERE key NOT LIKE 'utxo_snapshot%'")
    con.commit()

    con.close()
    log("Aggiornamento completato.")

if __name__ == "__main__":
    main()

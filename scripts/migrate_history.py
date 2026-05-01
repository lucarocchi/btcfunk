#!/usr/bin/env python3
"""
One-time BigQuery → SQLite full history migration.

Usage:
    python3 scripts/migrate_history.py           # full migration
    python3 scripts/migrate_history.py --dry-run  # preview only, no writes

Requires: gcloud auth application-default login
"""
import sys, os, sqlite3, argparse
from collections import defaultdict
from datetime import date as Date, datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, "../btcfunk.sqlite")
SINCE      = "2009-01-03"  # Bitcoin genesis

_bq = None
def bq():
    global _bq
    if _bq is None:
        from google.cloud import bigquery
        _bq = bigquery.Client()
    return _bq

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def run_query(sql, label):
    log(f"{label}: eseguo query BQ...")
    rows = list(bq().query(sql).result())
    log(f"{label}: {len(rows)} righe ricevute")
    return rows


# ── Helpers ──────────────────────────────────────────────────────────────────

def _bits_to_difficulty(bits_hex):
    exp      = int(bits_hex[:2], 16)
    mantissa = int(bits_hex[2:8], 16)
    target   = mantissa * (2 ** (8 * (exp - 3)))
    return (0xffff * (2 ** 208)) / target

def _get_prices(con):
    """Carica btc_prices da ohlc se non già presente, poi ritorna dict {day: price}."""
    count = con.execute("SELECT COUNT(*) FROM btc_prices").fetchone()[0]
    if count == 0:
        log("btc_prices vuota, popolo da ohlc...")
        rows = con.execute(
            "SELECT DATE(ts, 'unixepoch') AS day, close FROM ohlc WHERE tf = 1440 ORDER BY ts"
        ).fetchall()
        if rows:
            con.executemany("INSERT OR REPLACE INTO btc_prices (day, price) VALUES (?,?)", rows)
            con.commit()
            log(f"btc_prices: inserite {len(rows)} righe da ohlc")
    return {r[0]: r[1] for r in con.execute("SELECT day, price FROM btc_prices").fetchall()}


# ── Init tabelle ──────────────────────────────────────────────────────────────

def init_tables(con):
    con.executescript("""
        CREATE TABLE IF NOT EXISTS btc_prices (
            day TEXT PRIMARY KEY, price REAL
        );
        CREATE TABLE IF NOT EXISTS nvt_daily (
            day TEXT PRIMARY KEY, btc_volume REAL
        );
        CREATE TABLE IF NOT EXISTS active_addr_daily (
            day TEXT PRIMARY KEY, count INTEGER
        );
        CREATE TABLE IF NOT EXISTS puell_daily (
            day TEXT PRIMARY KEY, revenue REAL
        );
        CREATE TABLE IF NOT EXISTS tx_stats_daily (
            day TEXT PRIMARY KEY, tx_count INTEGER, volume REAL, fees REAL
        );
        CREATE TABLE IF NOT EXISTS whale_tx_daily (
            day TEXT PRIMARY KEY, count INTEGER, btc_volume REAL
        );
        CREATE TABLE IF NOT EXISTS hashrate_daily (
            day TEXT PRIMARY KEY, difficulty REAL, hashrate_eh REAL, block_count INTEGER
        );
        CREATE TABLE IF NOT EXISTS sopr_daily (
            day TEXT PRIMARY KEY, sopr REAL
        );
        CREATE TABLE IF NOT EXISTS cdd_daily (
            day TEXT PRIMARY KEY, cdd REAL
        );
        CREATE TABLE IF NOT EXISTS utxo_snapshot (
            creation_day TEXT PRIMARY KEY, btc_value REAL
        );
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY, value TEXT, updated_at TEXT
        );
    """)
    con.commit()


# ── Query 1: outputs → nvt_daily + active_addr_daily ─────────────────────────

def migrate_outputs(con, since, dry_run):
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
    if dry_run:
        log(f"  [dry-run] nvt_daily: {len(rows)} righe, active_addr_daily: {len(rows)} righe")
        return

    nvt_rows  = [(str(r.day), float(r.btc_volume)) for r in rows]
    addr_rows = [(str(r.day), int(r.addr_count))   for r in rows]
    con.executemany("INSERT OR REPLACE INTO nvt_daily (day, btc_volume) VALUES (?,?)", nvt_rows)
    con.executemany("INSERT OR REPLACE INTO active_addr_daily (day, count) VALUES (?,?)", addr_rows)
    con.commit()
    log(f"  nvt_daily: {len(nvt_rows)} righe inserite")
    log(f"  active_addr_daily: {len(addr_rows)} righe inserite")


# ── Query 2: transactions → puell_daily + tx_stats_daily + whale_tx_daily ────

def migrate_transactions(con, since, dry_run):
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
    if dry_run:
        log(f"  [dry-run] 3 tabelle × {len(rows)} righe")
        return

    puell_rows = [(str(r.day), float(r.coinbase_revenue)) for r in rows]
    tx_rows    = [(str(r.day), int(r.tx_count), float(r.volume_btc), float(r.fees_btc)) for r in rows]
    whale_rows = [(str(r.day), int(r.whale_count), float(r.whale_volume)) for r in rows]

    con.executemany("INSERT OR REPLACE INTO puell_daily (day, revenue) VALUES (?,?)", puell_rows)
    con.executemany("INSERT OR REPLACE INTO tx_stats_daily (day, tx_count, volume, fees) VALUES (?,?,?,?)", tx_rows)
    con.executemany("INSERT OR REPLACE INTO whale_tx_daily (day, count, btc_volume) VALUES (?,?,?)", whale_rows)
    con.commit()
    log(f"  puell_daily / tx_stats_daily / whale_tx_daily: {len(rows)} righe inserite")


# ── Query 3: blocks → hashrate_daily ─────────────────────────────────────────

def migrate_hashrate(con, since, dry_run):
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
    if dry_run:
        log(f"  [dry-run] hashrate_daily: {len(rows)} righe")
        return

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
    log(f"  hashrate_daily: {len(out)} righe inserite")


# ── Query 4: inputs JOIN outputs → sopr_daily + cdd_daily (per anno) ─────────

def migrate_flows_year(con, year, prices, dry_run):
    since = f"{year}-01-01"
    until = f"{year + 1}-01-01"
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
          AND DATE(i.block_timestamp) < '{until}'
        GROUP BY spend_day, creation_day
        ORDER BY spend_day
    """
    rows = run_query(sql, f"flows {year} (SOPR + CDD)")
    if not rows:
        return

    realized   = defaultdict(float)
    cost_basis = defaultdict(float)
    cdd_agg    = defaultdict(float)

    for r in rows:
        spend_day    = str(r.spend_day)
        creation_day = str(r.creation_day)
        btc          = float(r.btc_amount)

        # SOPR
        p_spend    = prices.get(spend_day)
        p_creation = prices.get(creation_day)
        if p_spend and p_creation:
            realized[spend_day]   += btc * p_spend
            cost_basis[spend_day] += btc * p_creation

        # CDD
        try:
            age = (Date.fromisoformat(spend_day) - Date.fromisoformat(creation_day)).days
        except ValueError:
            continue
        if age >= 0:
            cdd_agg[spend_day] += btc * age

    if dry_run:
        log(f"  [dry-run] {year}: sopr_daily {len(realized)} righe, cdd_daily {len(cdd_agg)} righe")
        return

    sopr_rows = [
        (day, round(realized[day] / cost_basis[day], 6))
        for day in sorted(realized) if cost_basis[day] > 0
    ]
    cdd_rows = [(day, round(val, 2)) for day, val in sorted(cdd_agg.items())]

    con.executemany("INSERT OR REPLACE INTO sopr_daily (day, sopr) VALUES (?,?)", sopr_rows)
    con.executemany("INSERT OR REPLACE INTO cdd_daily (day, cdd) VALUES (?,?)", cdd_rows)
    con.commit()
    log(f"  {year}: sopr_daily {len(sopr_rows)} righe, cdd_daily {len(cdd_rows)} righe inserite")


def migrate_flows(con, since, dry_run):
    prices     = _get_prices(con)
    start_year = int(since[:4])
    end_year   = datetime.now(timezone.utc).year
    for year in range(start_year, end_year + 1):
        migrate_flows_year(con, year, prices, dry_run)


# ── Query 5: UTXO snapshot → utxo_snapshot ───────────────────────────────────

def migrate_utxo_snapshot(con, dry_run):
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
    if dry_run:
        log(f"  [dry-run] utxo_snapshot: {len(rows)} righe")
        return

    out = [(str(r.creation_day), float(r.btc_value)) for r in rows]
    con.executemany("INSERT OR REPLACE INTO utxo_snapshot (creation_day, btc_value) VALUES (?,?)", out)
    con.execute(
        "INSERT OR REPLACE INTO cache (key, value, updated_at) VALUES ('utxo_snapshot_updated', 'true', ?)",
        (datetime.now(timezone.utc).isoformat(),)
    )
    con.commit()
    log(f"  utxo_snapshot: {len(out)} righe inserite")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Non scrive su SQLite")
    parser.add_argument("--since", default=SINCE, help="Data inizio (YYYY-MM-DD)")
    parser.add_argument("--skip-flows", action="store_true", help="Salta SOPR/CDD (query lenta)")
    parser.add_argument("--skip-utxo", action="store_true", help="Salta UTXO snapshot (query lenta)")
    args = parser.parse_args()

    log(f"DB: {DB_PATH}")
    log(f"Since: {args.since} | dry-run: {args.dry_run}")

    con = sqlite3.connect(DB_PATH)
    init_tables(con)

    migrate_outputs(con, args.since, args.dry_run)
    migrate_transactions(con, args.since, args.dry_run)
    migrate_hashrate(con, args.since, args.dry_run)

    if not args.skip_flows:
        migrate_flows(con, args.since, args.dry_run)
    else:
        log("SOPR/CDD: skippato (--skip-flows)")

    if not args.skip_utxo:
        migrate_utxo_snapshot(con, args.dry_run)
    else:
        log("UTXO snapshot: skippato (--skip-utxo)")

    con.close()
    log("Migrazione completata.")

if __name__ == "__main__":
    main()
